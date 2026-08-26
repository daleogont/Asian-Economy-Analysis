"""
Multi-ticker benchmark for a research paper comparing ARIMA, ETS, SARIMA,
and Prophet. Calls the model classes directly (not via HTTP) for clean
timing without network/serialization noise.

Run inside the python-api container:
    docker compose exec python-api python scripts/benchmark_paper.py
"""
import logging
import os
import random
import sys
import warnings

# This script lives in scripts/, but imports the `app` package from the
# parent directory (/app when run inside the container) — add it to
# sys.path since `python scripts/benchmark_paper.py` only puts the
# script's own directory there by default.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
import pandas as pd

from app.db import fetch_df
from app.models.arima import ArimaModel
from app.models.ets import EtsModel
from app.models.prophet import ProphetModel
from app.models.sarima import SarimaModel

warnings.filterwarnings("ignore")
logging.getLogger("cmdstanpy").setLevel(logging.WARNING)
logging.getLogger("prophet").setLevel(logging.WARNING)

MODELS = {
    "arima":   ArimaModel,
    "ets":     EtsModel,
    "sarima":  SarimaModel,
    "prophet": ProphetModel,
}

DAYS           = 30
PERIOD_DAYS    = 365
HOLDOUT_FRAC   = 0.2
MIN_ROWS       = 240
TARGET_TICKERS = 30
BASE_PER_COUNTRY = 2
REFERENCE_TICKER = "9988.HK"
SEED           = 42

HERE     = os.path.dirname(os.path.abspath(__file__))
OUT_CSV  = os.path.join(HERE, "benchmark_results.csv")


def select_tickers() -> pd.DataFrame:
    """Tickers with >= MIN_ROWS rows in the last PERIOD_DAYS, stratified
    ~2-3 per country, ~TARGET_TICKERS total, always including the
    reference ticker."""
    coverage = fetch_df(
        f"""
        SELECT dp.ticker, c.country, COUNT(*) AS row_count
        FROM daily_prices dp
        JOIN companies c ON c.ticker = dp.ticker
        WHERE dp.date >= CURRENT_DATE - INTERVAL '{PERIOD_DAYS} days'
          AND dp.close IS NOT NULL
        GROUP BY dp.ticker, c.country
        HAVING COUNT(*) >= {MIN_ROWS}
        ORDER BY c.country, dp.ticker
        """
    )

    rng = random.Random(SEED)
    by_country = {
        country: list(group["ticker"])
        for country, group in coverage.groupby("country")
    }

    selected = []
    ref_country = None
    if REFERENCE_TICKER in coverage["ticker"].values:
        ref_country = coverage.loc[coverage["ticker"] == REFERENCE_TICKER, "country"].iloc[0]
        selected.append(REFERENCE_TICKER)
        by_country[ref_country].remove(REFERENCE_TICKER)

    countries = sorted(by_country.keys())
    for country in countries:
        already = 1 if country == ref_country else 0
        need = max(BASE_PER_COUNTRY - already, 0)
        pool = by_country[country]
        take = min(need, len(pool))
        picks = rng.sample(pool, take) if take > 0 else []
        selected.extend(picks)
        for p in picks:
            pool.remove(p)

    # Top up round-robin across countries with spare tickers until we hit
    # the target (or run out of eligible tickers everywhere).
    while len(selected) < TARGET_TICKERS:
        progressed = False
        for country in countries:
            if len(selected) >= TARGET_TICKERS:
                break
            pool = by_country[country]
            if pool:
                pick = rng.choice(pool)
                pool.remove(pick)
                selected.append(pick)
                progressed = True
        if not progressed:
            break

    ticker_to_country = dict(zip(coverage["ticker"], coverage["country"]))
    return pd.DataFrame(
        {"ticker": selected, "country": [ticker_to_country[t] for t in selected]}
    )


def fetch_series(ticker: str) -> pd.Series:
    df = fetch_df(
        f"""
        SELECT date, close
        FROM daily_prices
        WHERE ticker = :ticker
          AND date >= CURRENT_DATE - INTERVAL '{PERIOD_DAYS} days'
          AND close IS NOT NULL
        ORDER BY date ASC
        """,
        {"ticker": ticker},
    )
    df["date"]  = pd.to_datetime(df["date"])
    df["close"] = df["close"].astype(float)
    df = df.set_index("date").asfreq("B").ffill()
    return df["close"]


def run_one(ticker: str, country: str, model_key: str, series: pd.Series) -> dict:
    instance = MODELS[model_key]()
    result = instance.run(series, steps=DAYS, holdout_frac=HOLDOUT_FRAC)
    metrics = result["metrics"]

    mean_close = float(series.mean())
    rmse = metrics["rmse"]
    rmse_pct = (rmse / mean_close * 100) if (rmse is not None and mean_close) else None

    return {
        "ticker":               ticker,
        "country":              country,
        "model":                model_key,
        "rmse":                 rmse,
        "mae":                  metrics["mae"],
        "rmse_pct":             rmse_pct,
        "inference_latency_ms": metrics["inference_latency_ms"],
        "train_time_s":         metrics["train_time_s"],
        "memory_mb":            metrics["memory_mb"],
        "error":                None,
    }


def failed_row(ticker: str, country: str, model_key: str, exc: Exception) -> dict:
    return {
        "ticker": ticker, "country": country, "model": model_key,
        "rmse": np.nan, "mae": np.nan, "rmse_pct": np.nan,
        "inference_latency_ms": np.nan, "train_time_s": np.nan, "memory_mb": np.nan,
        "error": str(exc)[:200],
    }


def print_summary(df: pd.DataFrame) -> None:
    print("\n" + "=" * 80)
    print("SUMMARY — mean ± std across tickers, per model")
    print("=" * 80)

    metric_cols = ["rmse", "rmse_pct", "mae", "inference_latency_ms", "train_time_s", "memory_mb"]
    header = f"{'model':<10}{'n_ok':>6}{'n_fail':>7}" + "".join(f"{c:>20}" for c in metric_cols)
    print(header)

    for model_key in MODELS:
        sub = df[df["model"] == model_key]
        ok  = sub.dropna(subset=["rmse"])
        n_fail = len(sub) - len(ok)

        row = f"{model_key:<10}{len(ok):>6}{n_fail:>7}"
        for col in metric_cols:
            if len(ok) > 0:
                row += f"{ok[col].mean():>10.3f}±{ok[col].std():<8.3f}"
            else:
                row += f"{'—':>20}"
        print(row)

    failures = df[df["error"].notna()]
    if len(failures) > 0:
        print("\nFailed ticker×model combinations:")
        for _, r in failures.iterrows():
            print(f"  {r['ticker']:<12} {r['model']:<10} — {r['error']}")
    else:
        print("\nNo failures.")


def main():
    tickers_df = select_tickers()
    print(f"\n📊 Selected {len(tickers_df)} tickers across {tickers_df['country'].nunique()} countries:")
    for country, group in tickers_df.groupby("country"):
        print(f"  {country}: {', '.join(group['ticker'])}")

    total = len(tickers_df)
    results = []

    for i, row in enumerate(tickers_df.itertuples(index=False), 1):
        ticker, country = row.ticker, row.country
        try:
            series = fetch_series(ticker)
        except Exception as exc:
            print(f"ticker {i}/{total}: {ticker} — failed to fetch price series: {exc}")
            for model_key in MODELS:
                results.append(failed_row(ticker, country, model_key, exc))
            continue

        for model_key in MODELS:
            try:
                result = run_one(ticker, country, model_key, series)
                rmse = result["rmse"]
                rmse_str = f"{rmse:.1f}" if rmse is not None else "NaN"
                print(f"ticker {i}/{total}: {ticker} — {model_key} done (rmse={rmse_str})")
            except Exception as exc:
                result = failed_row(ticker, country, model_key, exc)
                print(f"ticker {i}/{total}: {ticker} — {model_key} FAILED ({exc})")
            results.append(result)

    df_results = pd.DataFrame(results)
    df_results.to_csv(OUT_CSV, index=False)
    print(f"\n💾 Saved {len(df_results)} rows to {OUT_CSV}")

    print_summary(df_results)


if __name__ == "__main__":
    main()
