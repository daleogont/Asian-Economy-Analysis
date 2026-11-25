"""
STEP 2 (clean timing pass) -- run INSIDE the python-api container (Linux,
CPU-only, the environment the paper's cost numbers should actually
describe), on a quiet host, to produce timing/memory numbers uncontaminated
by the host-side CPU contention the main rolling_benchmark.py run was
under.

Protocol (as specified): all 30 tickers x 3 fixed origins x all 10 model
variants, run strictly sequentially, 3 repetitions each, discard the first
fit per model per process as warm-up, report the median per (ticker,
model) across the repetitions x origins. Checks os.getloadavg() before and
after every ticker and pauses (polling, logged) if it exceeds 1.5 rather
than silently continuing or aborting outright.

"3 fixed origins" = the same three RELATIVE positions (first available,
middle, last available) in each ticker's own origin list -- origin COUNTS
differ slightly by ticker (21-25, depending on history length), so fixed
absolute indices would not be comparable across tickers the same way.

Run via:
  docker compose exec -T python-api python /research/timing_pass.py
(research/ is mounted read-only at /research, research/results read-write,
via docker-compose.override.yml.)
"""
import csv
import logging
import os
import sys
import time
import tracemalloc

import numpy as np
import psutil

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from common import PAPER_TICKERS, fetch_df, fetch_series  # noqa: E402
from rolling_benchmark import (  # noqa: E402
    FULL_PERIOD_DAYS, HORIZON, MIN_TRAIN_DAYS, MODELS, STEP, TIER, origins_for,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s", stream=sys.stdout)
logger = logging.getLogger("timing_pass")

RESULTS_DIR = os.path.join(HERE, "results")
OUT_CSV = os.path.join(RESULTS_DIR, "timing_clean.csv")
SUMMARY_CSV = os.path.join(RESULTS_DIR, "timing_clean_summary.csv")

N_REPS = 3
LOADAVG_LIMIT = 1.5
LOADAVG_POLL_S = 15
LOADAVG_MAX_WAIT_S = 1200  # give up and exit loudly after 20 min of waiting

RAW_COLS = ["ticker", "origin_date", "origin_position", "model", "tier", "rep",
            "train_time_s", "inference_latency_ms", "memory_mb", "error"]

_process = psutil.Process(os.getpid())
_warmed_up = set()


def wait_for_quiet_host():
    waited = 0
    while True:
        la = os.getloadavg()[0]
        if la <= LOADAVG_LIMIT:
            return la
        if waited >= LOADAVG_MAX_WAIT_S:
            raise RuntimeError(f"loadavg still {la:.2f} > {LOADAVG_LIMIT} after {waited}s -- aborting timing pass")
        logger.warning(f"loadavg={la:.2f} > {LOADAVG_LIMIT}, pausing {LOADAVG_POLL_S}s (waited {waited}s so far)")
        time.sleep(LOADAVG_POLL_S)
        waited += LOADAVG_POLL_S


def pick_fixed_origins(origins):
    if len(origins) == 1:
        return [("first", origins[0])]
    if len(origins) == 2:
        return [("first", origins[0]), ("last", origins[-1])]
    mid = origins[len(origins) // 2]
    return [("first", origins[0]), ("middle", mid), ("last", origins[-1])]


def time_one_fit(model_key, train, horizon_steps=HORIZON):
    instance = MODELS[model_key]()
    tracemalloc.start()
    rss_before = _process.memory_info().rss
    t0 = time.perf_counter()
    error = None
    try:
        instance.fit(train)
        train_time_s = time.perf_counter() - t0
        t1 = time.perf_counter()
        instance.predict(horizon_steps)
        inference_latency_ms = (time.perf_counter() - t1) * 1000
    except Exception as exc:
        train_time_s = time.perf_counter() - t0
        inference_latency_ms = None
        error = str(exc)[:300]
    _, traced_peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    rss_delta = max(_process.memory_info().rss - rss_before, 0)
    memory_mb = max(traced_peak, rss_delta) / (1024 * 1024)
    return train_time_s, inference_latency_ms, memory_mb, error


def append_rows(rows):
    exists = os.path.exists(OUT_CSV)
    with open(OUT_CSV, "a", newline="") as f:
        w = csv.DictWriter(f, fieldnames=RAW_COLS)
        if not exists:
            w.writeheader()
        for r in rows:
            w.writerow(r)


def main():
    os.makedirs(RESULTS_DIR, exist_ok=True)
    logger.info(f"execution_context=container pid={os.getpid()} cpu_count={psutil.cpu_count()}")

    tickers_df = fetch_df("SELECT ticker, country FROM companies WHERE ticker = ANY(:t)", {"t": PAPER_TICKERS})
    ticker_country = dict(zip(tickers_df.ticker, tickers_df.country))

    run_start = time.perf_counter()
    for ti, ticker in enumerate(PAPER_TICKERS, 1):
        la_before = wait_for_quiet_host()
        series = fetch_series(ticker, period_days=FULL_PERIOD_DAYS)
        origins = origins_for(len(series), MIN_TRAIN_DAYS, STEP, HORIZON)
        fixed = pick_fixed_origins(origins)
        logger.info(f"[{ti}/{len(PAPER_TICKERS)}] {ticker} n={len(series)} loadavg_before={la_before:.2f} "
                    f"origins={[ (p, str(series.index[i-1].date())) for p, i in fixed ]}")

        for position, origin_idx in fixed:
            train = series.iloc[:origin_idx]
            origin_date = str(series.index[origin_idx - 1].date())
            for model_key in MODELS:
                for rep in range(1, N_REPS + 1):
                    is_warmup = model_key not in _warmed_up
                    train_time_s, inference_latency_ms, memory_mb, error = time_one_fit(model_key, train)
                    if is_warmup:
                        _warmed_up.add(model_key)
                        logger.info(f"  (warm-up fit for {model_key}, discarded)")
                        continue
                    append_rows([{
                        "ticker": ticker, "origin_date": origin_date, "origin_position": position,
                        "model": model_key, "tier": TIER[model_key], "rep": rep,
                        "train_time_s": round(train_time_s, 4),
                        "inference_latency_ms": round(inference_latency_ms, 3) if inference_latency_ms is not None else None,
                        "memory_mb": round(memory_mb, 3), "error": error,
                    }])

        la_after = os.getloadavg()[0]
        elapsed = time.perf_counter() - run_start
        logger.info(f"[{ti}/{len(PAPER_TICKERS)}] {ticker} done. loadavg_after={la_after:.2f} elapsed={elapsed:.1f}s")

    logger.info(f"RUN COMPLETE. total_elapsed={time.perf_counter()-run_start:.1f}s")
    build_summary()


def build_summary():
    import pandas as pd
    df = pd.read_csv(OUT_CSV)
    ok = df.dropna(subset=["train_time_s"])
    summary = ok.groupby(["ticker", "model"]).agg(
        tier=("tier", "first"),
        n=("train_time_s", "count"),
        train_time_s_median=("train_time_s", "median"),
        inference_latency_ms_median=("inference_latency_ms", "median"),
        memory_mb_median=("memory_mb", "median"),
    ).reset_index()
    summary.to_csv(SUMMARY_CSV, index=False)
    logger.info(f"Wrote {SUMMARY_CSV}")


if __name__ == "__main__":
    main()
