"""
STEP 2 — rolling-origin cross-validation benchmark.

Expanding window: first origin after ~2 years (504 business days) of
training data, then step forward 30 trading days, forecasting a 30-day
horizon at each origin and comparing against the realized next 30 closes.
Tiers:
  A  production-fixed (exact prod classes/configs): arima, ets, sarima, prophet
  B  baselines (research-only): random_walk, random_walk_drift
  C  optimized: arima_optimized, ets_optimized, prophet_optimized
  D  ablation: prophet_no_yearly

Resumable: completed (ticker, origin_date, model) rows are skipped on
restart by re-reading research/results/rolling_folds.csv.

Usage:
  research/.venv/bin/python research/rolling_benchmark.py                  # full run
  research/.venv/bin/python research/rolling_benchmark.py --tickers 2 --max-origins 3   # pilot
"""
import argparse
import csv
import logging
import os
import sys
import time
import tracemalloc
import warnings

import numpy as np
import pandas as pd
import psutil

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from common import PAPER_TICKERS, fetch_df, fetch_series  # noqa: E402
from models_extra import (  # noqa: E402
    OptimizedArimaModel, OptimizedEtsModel, OptimizedProphetModel,
    ProphetNoYearly, RandomWalkDriftModel, RandomWalkModel,
)

ANALYTICS_DIR = os.path.join(os.path.dirname(HERE), "analytics")
sys.path.insert(0, ANALYTICS_DIR)
from app.models.arima import ArimaModel  # noqa: E402
from app.models.ets import EtsModel  # noqa: E402
from app.models.prophet import ProphetModel  # noqa: E402
from app.models.sarima import SarimaModel  # noqa: E402

warnings.filterwarnings("ignore")
logging.getLogger("cmdstanpy").setLevel(logging.WARNING)
logging.getLogger("prophet").setLevel(logging.WARNING)
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s", stream=sys.stdout)
logger = logging.getLogger("rolling_benchmark")

MODELS = {
    "arima": ArimaModel,
    "ets": EtsModel,
    "sarima": SarimaModel,
    "prophet": ProphetModel,
    "random_walk": RandomWalkModel,
    "random_walk_drift": RandomWalkDriftModel,
    "arima_optimized": OptimizedArimaModel,
    "ets_optimized": OptimizedEtsModel,
    "prophet_optimized": OptimizedProphetModel,
    "prophet_no_yearly": ProphetNoYearly,
}
TIER = {
    "arima": "A", "ets": "A", "sarima": "A", "prophet": "A",
    "random_walk": "B", "random_walk_drift": "B",
    "arima_optimized": "C", "ets_optimized": "C", "prophet_optimized": "C",
    "prophet_no_yearly": "D",
}

HORIZON = 30
MIN_TRAIN_DAYS = 504  # ~2 years of business days
STEP = 30
SEED = 42
FULL_PERIOD_DAYS = 5 * 365 + 10

RESULTS_DIR = os.path.join(HERE, "results")
FOLDS_CSV = os.path.join(RESULTS_DIR, "rolling_folds.csv")
PATHS_CSV = os.path.join(RESULTS_DIR, "forecast_paths.csv")

FOLDS_COLS = [
    "ticker", "country", "origin_date", "origin_idx", "model", "tier",
    "rmse", "mae", "rmse_pct", "mase",
    "train_time_s", "inference_latency_ms", "memory_mb",
    "n_train", "selected_config", "error",
]
PATHS_COLS = ["ticker", "origin_date", "model", "h", "date", "forecast", "actual"]

_process = psutil.Process(os.getpid())
_warmed_up = set()


def origins_for(n, min_train, step, horizon):
    out, idx = [], min_train
    while idx + horizon <= n:
        out.append(idx)
        idx += step
    return out


def compute_metrics(forecast, actual, train_series):
    pred = np.asarray(forecast["mean"][: len(actual)], dtype=float)
    act = np.asarray(actual, dtype=float)
    if len(pred) != len(act) or len(pred) == 0:
        return None
    err = pred - act
    rmse = float(np.sqrt(np.mean(err ** 2)))
    mae = float(np.mean(np.abs(err)))
    # mean_close mirrors the existing benchmark's normalization base (mean
    # over the full series fed in, i.e. train+holdout combined) -- here
    # that is train ∪ realized horizon.
    mean_close = float(np.concatenate([train_series.to_numpy(), act]).mean())
    rmse_pct = (rmse / mean_close * 100) if mean_close else None
    train_diffs = np.diff(train_series.to_numpy())
    naive_mae = float(np.mean(np.abs(train_diffs))) if len(train_diffs) else None
    mase = (mae / naive_mae) if naive_mae else None
    return rmse, mae, rmse_pct, mase, pred


def load_completed(path):
    completed = set()
    if os.path.exists(path):
        with open(path) as f:
            for row in csv.DictReader(f):
                completed.add((row["ticker"], row["origin_date"], row["model"]))
    return completed


def append_rows(path, cols, rows):
    exists = os.path.exists(path)
    with open(path, "a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=cols)
        if not exists:
            writer.writeheader()
        for r in rows:
            writer.writerow(r)


def run_fold(model_key, ticker, country, series, origin_idx):
    train = series.iloc[:origin_idx]
    horizon_actual = series.iloc[origin_idx: origin_idx + HORIZON]
    origin_date = str(series.index[origin_idx - 1].date())

    instance = MODELS[model_key]()

    tracemalloc.start()
    rss_before = _process.memory_info().rss
    t0 = time.perf_counter()
    forecast, error = None, None
    try:
        instance.fit(train)
        train_time_s = time.perf_counter() - t0
        infer_t0 = time.perf_counter()
        forecast = instance.predict(HORIZON)
        inference_latency_ms = (time.perf_counter() - infer_t0) * 1000
    except Exception as exc:
        train_time_s = time.perf_counter() - t0
        inference_latency_ms = None
        error = str(exc)[:300]
    _, traced_peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    rss_delta = max(_process.memory_info().rss - rss_before, 0)
    memory_mb = max(traced_peak, rss_delta) / (1024 * 1024)

    selected_config = str(getattr(instance, "selected_config", None) or getattr(instance, "selected_order", None) or "")

    fold_row = {
        "ticker": ticker, "country": country, "origin_date": origin_date,
        "origin_idx": origin_idx, "model": model_key, "tier": TIER[model_key],
        "rmse": None, "mae": None, "rmse_pct": None, "mase": None,
        "train_time_s": round(train_time_s, 4),
        "inference_latency_ms": round(inference_latency_ms, 3) if inference_latency_ms is not None else None,
        "memory_mb": round(memory_mb, 3),
        "n_train": len(train), "selected_config": selected_config, "error": error,
    }
    path_rows = []

    if forecast is not None and error is None:
        metrics = compute_metrics(forecast, horizon_actual.to_numpy(), train)
        if metrics is not None:
            rmse, mae, rmse_pct, mase, pred = metrics
            fold_row.update(
                rmse=round(rmse, 4), mae=round(mae, 4),
                rmse_pct=round(rmse_pct, 4) if rmse_pct is not None else None,
                mase=round(mase, 4) if mase is not None else None,
            )
            for h, (d, fc_val, act_val) in enumerate(
                zip(horizon_actual.index, pred, horizon_actual.to_numpy()), start=1
            ):
                path_rows.append({
                    "ticker": ticker, "origin_date": origin_date, "model": model_key,
                    "h": h, "date": str(d.date()), "forecast": float(fc_val), "actual": float(act_val),
                })

    return fold_row, path_rows


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--tickers", type=int, default=None, help="limit to first N tickers (pilot)")
    parser.add_argument("--max-origins", type=int, default=None, help="limit origins per ticker (pilot)")
    args = parser.parse_args()

    np.random.seed(SEED)
    os.makedirs(RESULTS_DIR, exist_ok=True)
    completed = load_completed(FOLDS_CSV)

    tickers_df = fetch_df("SELECT ticker, country FROM companies WHERE ticker = ANY(:t)", {"t": PAPER_TICKERS})
    ticker_country = dict(zip(tickers_df.ticker, tickers_df.country))
    tickers = PAPER_TICKERS[: args.tickers] if args.tickers else PAPER_TICKERS

    run_start = time.perf_counter()
    n_folds_done = 0

    for ti, ticker in enumerate(tickers, 1):
        country = ticker_country.get(ticker, "unknown")
        la_before = os.getloadavg()
        series = fetch_series(ticker, period_days=FULL_PERIOD_DAYS)
        n = len(series)
        origins = origins_for(n, MIN_TRAIN_DAYS, STEP, HORIZON)
        if args.max_origins:
            origins = origins[: args.max_origins]
        logger.info(
            f"[{ti}/{len(tickers)}] {ticker} ({country}) n={n} origins={len(origins)} "
            f"loadavg_before={la_before}"
        )

        for oi, origin_idx in enumerate(origins, 1):
            origin_date = str(series.index[origin_idx - 1].date())
            for model_key in MODELS:
                key = (ticker, origin_date, model_key)
                if key in completed:
                    continue

                is_warmup = model_key not in _warmed_up
                fold_row, path_rows = run_fold(model_key, ticker, country, series, origin_idx)

                if is_warmup:
                    _warmed_up.add(model_key)
                    logger.info(f"  (warm-up fit for {model_key}, discarded)")
                    continue

                append_rows(FOLDS_CSV, FOLDS_COLS, [fold_row])
                if path_rows:
                    append_rows(PATHS_CSV, PATHS_COLS, path_rows)
                completed.add(key)
                n_folds_done += 1

            elapsed = time.perf_counter() - run_start
            logger.info(
                f"  origin {oi}/{len(origins)} ({origin_date}) done | "
                f"folds_done={n_folds_done} elapsed={elapsed:.1f}s"
            )

        la_after = os.getloadavg()
        logger.info(f"[{ti}/{len(tickers)}] {ticker} done. loadavg_after={la_after}")

    total_elapsed = time.perf_counter() - run_start
    logger.info(f"RUN COMPLETE. folds_done={n_folds_done} total_elapsed={total_elapsed:.1f}s")


if __name__ == "__main__":
    main()
