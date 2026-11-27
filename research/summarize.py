"""
Builds research/results/summary_by_model_tier.csv: mean/median/std of
rmse_pct and MASE per model, cost means (train_time_s, inference_latency_ms,
memory_mb), win counts (how often each model has the lowest rmse_pct among
all 10 for a given ticker x origin), with the old one-year single-split
paper numbers (research/legacy/benchmark_results.csv) joined in for
side-by-side comparison on the 4 production-tier models.

Run AFTER rolling_benchmark.py has completed (or at any checkpoint, to
inspect partial results -- it just summarizes whatever is in
rolling_folds.csv so far).
"""
import os
import sys

import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

RESULTS_DIR = os.path.join(HERE, "results")
FOLDS_CSV = os.path.join(RESULTS_DIR, "rolling_folds.csv")
OLD_BENCHMARK_CSV = os.path.join(HERE, "legacy", "benchmark_results.csv")
OUT_CSV = os.path.join(RESULTS_DIR, "summary_by_model_tier.csv")

TIER = {
    "arima": "A", "ets": "A", "sarima": "A", "prophet": "A",
    "random_walk": "B", "random_walk_drift": "B",
    "arima_optimized": "C", "ets_optimized": "C", "prophet_optimized": "C",
    "prophet_no_yearly": "D",
}


def main():
    df = pd.read_csv(FOLDS_CSV)
    ok = df.dropna(subset=["rmse"]).copy()

    agg = ok.groupby("model").agg(
        tier=("tier", "first"),
        n_folds=("rmse", "count"),
        n_failed=("error", lambda s: df.loc[s.index, "error"].notna().sum() if len(s) else 0),
        rmse_pct_mean=("rmse_pct", "mean"),
        rmse_pct_median=("rmse_pct", "median"),
        rmse_pct_std=("rmse_pct", "std"),
        mase_mean=("mase", "mean"),
        mase_median=("mase", "median"),
        mase_std=("mase", "std"),
        train_time_s_mean=("train_time_s", "mean"),
        inference_latency_ms_mean=("inference_latency_ms", "mean"),
        memory_mb_mean=("memory_mb", "mean"),
    ).reset_index()

    # Count true failures (error not null) per model from the unfiltered df.
    fail_counts = df[df["error"].notna()].groupby("model").size()
    agg["n_failed"] = agg["model"].map(fail_counts).fillna(0).astype(int)

    # Win counts: lowest rmse_pct among all models available for that
    # (ticker, origin_date) fold.
    pivot = ok.pivot_table(index=["ticker", "origin_date"], columns="model", values="rmse_pct")
    winners = pivot.idxmin(axis=1).value_counts()
    agg["win_count"] = agg["model"].map(winners).fillna(0).astype(int)
    agg["win_rate"] = agg["win_count"] / len(pivot)

    # Side-by-side: old one-year single-split numbers for the 4 production models.
    if os.path.exists(OLD_BENCHMARK_CSV):
        old = pd.read_csv(OLD_BENCHMARK_CSV)
        old_ok = old.dropna(subset=["rmse"])
        old_agg = old_ok.groupby("model").agg(
            old_1y_rmse_pct_mean=("rmse_pct", "mean"),
            old_1y_rmse_pct_median=("rmse_pct", "median"),
            old_1y_mae_mean=("mae", "mean"),
        ).reset_index()
        agg = agg.merge(old_agg, on="model", how="left")

    agg = agg.sort_values(["tier", "rmse_pct_mean"])
    agg.to_csv(OUT_CSV, index=False)
    print(f"Wrote {OUT_CSV}")
    print(agg.to_string(index=False))


if __name__ == "__main__":
    main()
