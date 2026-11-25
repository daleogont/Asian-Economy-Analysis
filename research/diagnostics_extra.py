"""
STEP 2 (extra) -- additional diagnostics requested on top of diagnostics.py's
original five (stationarity, ljung-box, prophet decomposition, prophet
ablations, pooled diebold-mariano).

Everything here reads only from research/results/rolling_folds.csv and
forecast_paths.csv -- no DB connection, no model refitting -- so it can run
standalone, independent of Postgres/Docker being up.

Outputs (research/results/):
  diagnostics_mape_by_horizon.csv       -- MAPE at h=1,5,10,20,30 per model
  diagnostics_anchoring.csv             -- anchoring analysis, Prophet variants + arima/ets/sarima for comparison
  diagnostics_ticker_clustered.csv      -- per (model, ticker) mean rmse_pct vs random_walk
  diagnostics_ticker_clustered_summary.csv -- paired t-test + Wilcoxon on the 30 ticker means, per model
  diagnostics_dm_per_ticker.csv         -- per (model, ticker) Diebold-Mariano approx at h=30
  diagnostics_dm_per_ticker_summary.csv -- aggregated across the 30 per-ticker DM tests
  diagnostics_win_counts.csv            -- win counts within prod-4 and prod-4+RW, by fold and by ticker
  diagnostics_selected_config_distribution.csv -- selected_config distribution, optimized tiers
"""
import logging
import os
import sys

import numpy as np
import pandas as pd
from scipy import stats

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s", stream=sys.stdout)
logger = logging.getLogger("diagnostics_extra")

RESULTS_DIR = os.path.join(HERE, "results")
FOLDS_CSV = os.path.join(RESULTS_DIR, "rolling_folds.csv")
PATHS_CSV = os.path.join(RESULTS_DIR, "forecast_paths.csv")

HORIZONS = [1, 5, 10, 20, 30]
PROD_MODELS = ["arima", "ets", "sarima", "prophet"]
OPTIMIZED_MODELS = ["arima_optimized", "ets_optimized", "prophet_optimized"]
ANCHOR_MODELS = ["prophet", "prophet_no_yearly", "prophet_optimized", "sarima", "arima", "ets"]


# ---------------------------------------------------------------------------
# 3. MAPE by horizon h = 1, 5, 10, 20, 30, per model
# ---------------------------------------------------------------------------
def run_mape_by_horizon(paths: pd.DataFrame) -> pd.DataFrame:
    sub = paths[paths["h"].isin(HORIZONS)].copy()
    sub = sub[sub["actual"] != 0]
    sub["abs_pct_err"] = (sub["forecast"] - sub["actual"]).abs() / sub["actual"].abs() * 100
    summary = sub.groupby(["model", "h"]).agg(
        mape_pct=("abs_pct_err", "mean"),
        n=("abs_pct_err", "count"),
    ).reset_index()
    out = os.path.join(RESULTS_DIR, "diagnostics_mape_by_horizon.csv")
    summary.to_csv(out, index=False)
    logger.info(f"Wrote {out}\n{summary.to_string(index=False)}")
    return summary


# ---------------------------------------------------------------------------
# 4. Anchoring analysis
#
# For each candidate model, anchor its path to the random-walk level:
#   anchored_h = rw_forecast + (forecast_h - forecast_1)
# where rw_forecast is the (flat) random_walk forecast for that
# (ticker, origin_date) -- i.e. the last training close. This removes the
# model's own level offset (its h=1 forecast vs. the last close) while
# keeping its forecasted shape/slope intact. The "h=1 offset" it removes is
# exactly |forecast_1 - rw_forecast| / rw_forecast * 100 -- reported
# separately as the mean absolute size of the correction being applied.
# ---------------------------------------------------------------------------
def run_anchoring(paths: pd.DataFrame) -> pd.DataFrame:
    rw = paths[paths["model"] == "random_walk"][["ticker", "origin_date", "h", "forecast"]].rename(
        columns={"forecast": "rw_forecast"}
    )

    rows = []
    for model in ANCHOR_MODELS:
        m = paths[paths["model"] == model][["ticker", "origin_date", "h", "forecast", "actual"]]
        if m.empty:
            continue
        h1 = m[m["h"] == 1][["ticker", "origin_date", "forecast"]].rename(columns={"forecast": "forecast_1"})
        merged = m.merge(h1, on=["ticker", "origin_date"], how="inner")
        merged = merged.merge(rw, on=["ticker", "origin_date", "h"], how="inner")
        merged = merged[merged["actual"] != 0]

        merged["anchored"] = merged["rw_forecast"] + (merged["forecast"] - merged["forecast_1"])

        def pooled_rms_pct(err, denom):
            return float(np.sqrt(np.mean(err ** 2)) / np.mean(np.abs(denom)) * 100)

        err_orig = merged["forecast"] - merged["actual"]
        err_anchored = merged["anchored"] - merged["actual"]
        err_rw = merged["rw_forecast"] - merged["actual"]

        h1_rows = merged[merged["h"] == 1]
        mean_abs_h1_offset_pct = float(
            ((h1_rows["forecast_1"] - h1_rows["rw_forecast"]).abs() / h1_rows["rw_forecast"].abs()).mean() * 100
        )

        rows.append({
            "model": model,
            "n_rows": len(merged),
            "n_folds": merged[["ticker", "origin_date"]].drop_duplicates().shape[0],
            "rms_pct_error_original": pooled_rms_pct(err_orig, merged["actual"]),
            "rms_pct_error_anchored": pooled_rms_pct(err_anchored, merged["actual"]),
            "rms_pct_error_random_walk": pooled_rms_pct(err_rw, merged["actual"]),
            "mean_abs_h1_offset_pct": mean_abs_h1_offset_pct,
        })
        logger.info(f"anchoring: {model} done (n_folds={rows[-1]['n_folds']})")

    df = pd.DataFrame(rows)
    out = os.path.join(RESULTS_DIR, "diagnostics_anchoring.csv")
    df.to_csv(out, index=False)
    logger.info(
        "Anchoring: anchored_h = rw_forecast + (forecast_h - forecast_1); "
        "mean_abs_h1_offset_pct is the mean size of that level correction "
        "(|forecast_1 - rw_forecast| / rw_forecast * 100), i.e. how far each "
        "model's own first-step forecast sits from the random-walk anchor.\n"
        f"{df.to_string(index=False)}"
    )
    return df


# ---------------------------------------------------------------------------
# 6a. Ticker-clustered paired tests vs random_walk (on rmse_pct)
# ---------------------------------------------------------------------------
def run_ticker_clustered(folds: pd.DataFrame):
    ok = folds.dropna(subset=["rmse_pct"])
    rw_by_ticker = ok[ok["model"] == "random_walk"].groupby("ticker")["rmse_pct"].mean()

    detail_rows, summary_rows = [], []
    for model in [m for m in ok["model"].unique() if m != "random_walk"]:
        by_ticker = ok[ok["model"] == model].groupby("ticker").agg(
            mean_rmse_pct_model=("rmse_pct", "mean"),
            n_origins=("rmse_pct", "count"),
        )
        by_ticker = by_ticker.join(rw_by_ticker.rename("mean_rmse_pct_rw"), how="inner")
        by_ticker["diff"] = by_ticker["mean_rmse_pct_model"] - by_ticker["mean_rmse_pct_rw"]
        by_ticker = by_ticker.reset_index()
        by_ticker.insert(0, "model", model)
        detail_rows.append(by_ticker)

        d = by_ticker["diff"].to_numpy()
        n = len(d)
        if n < 2:
            continue
        t_stat, t_p = stats.ttest_1samp(d, 0.0)
        try:
            w_stat, w_p = stats.wilcoxon(d)
        except ValueError:
            w_stat, w_p = None, None
        summary_rows.append({
            "model": model, "n_tickers": n,
            "mean_diff_rmse_pct": float(np.mean(d)),
            "n_tickers_model_better": int(np.sum(d < 0)),
            "paired_ttest_stat": float(t_stat), "paired_ttest_pvalue": float(t_p),
            "wilcoxon_stat": float(w_stat) if w_stat is not None else None,
            "wilcoxon_pvalue": float(w_p) if w_p is not None else None,
        })

    detail = pd.concat(detail_rows, ignore_index=True)
    detail.to_csv(os.path.join(RESULTS_DIR, "diagnostics_ticker_clustered.csv"), index=False)

    summary = pd.DataFrame(summary_rows).sort_values("mean_diff_rmse_pct")
    out = os.path.join(RESULTS_DIR, "diagnostics_ticker_clustered_summary.csv")
    summary.to_csv(out, index=False)
    logger.info(
        "Ticker-clustered paired tests vs random_walk (per-ticker mean "
        f"rmse_pct, 30 tickers each):\n{summary.to_string(index=False)}"
    )
    return detail, summary


# ---------------------------------------------------------------------------
# 6b. Diebold-Mariano per ticker at h=30 (non-overlapping folds within a
# ticker), aggregated across the 30 per-ticker tests.
#
# Approximation used: within a ticker, step == horizon == 30 makes the
# origins non-overlapping, so (unlike the usual DM setting) there is no
# within-ticker serial correlation from overlapping forecast windows for
# the HAC correction to remove -- a plain one-sample t-test on each
# ticker's own h=30 squared-error differential is used per ticker. The 30
# resulting per-ticker test statistics are then aggregated by simple counts
# and averaging (not a single pooled/meta-analytic test), since cross-ticker
# contemporaneous correlation (shared market days/macro shocks) is not
# modeled here either -- the same limitation already noted for the pooled
# DM table in diagnostics.py, carried over to this per-ticker version.
# ---------------------------------------------------------------------------
def run_dm_per_ticker(paths: pd.DataFrame):
    h30 = paths[paths["h"] == 30].copy()
    h30["sq_err"] = (h30["forecast"] - h30["actual"]) ** 2
    rw = h30[h30["model"] == "random_walk"][["ticker", "origin_date", "sq_err"]].rename(
        columns={"sq_err": "sq_err_rw"}
    )

    detail_rows, summary_rows = [], []
    for model in [m for m in h30["model"].unique() if m != "random_walk"]:
        other = h30[h30["model"] == model][["ticker", "origin_date", "sq_err"]].rename(
            columns={"sq_err": "sq_err_model"}
        )
        merged = other.merge(rw, on=["ticker", "origin_date"], how="inner")
        merged["d"] = merged["sq_err_model"] - merged["sq_err_rw"]

        per_ticker = []
        for ticker, g in merged.groupby("ticker"):
            d = g["d"].dropna().to_numpy()
            n = len(d)
            if n < 2:
                continue
            tstat, pvalue = stats.ttest_1samp(d, 0.0)
            per_ticker.append({
                "model": model, "ticker": ticker, "n_folds": n,
                "mean_d": float(np.mean(d)),
                "dm_tstat_approx": float(tstat), "dm_pvalue_approx": float(pvalue),
                "model_better_than_rw": bool(np.mean(d) < 0),
            })
        pt_df = pd.DataFrame(per_ticker)
        detail_rows.append(pt_df)

        sig_better = int(((pt_df["dm_pvalue_approx"] < 0.05) & pt_df["model_better_than_rw"]).sum())
        sig_worse = int(((pt_df["dm_pvalue_approx"] < 0.05) & ~pt_df["model_better_than_rw"]).sum())
        summary_rows.append({
            "model": model,
            "n_tickers": len(pt_df),
            "n_tickers_model_better_direction": int(pt_df["model_better_than_rw"].sum()),
            "n_tickers_significant_better_p05": sig_better,
            "n_tickers_significant_worse_p05": sig_worse,
            "mean_tstat_across_tickers": float(pt_df["dm_tstat_approx"].mean()),
        })

    detail = pd.concat(detail_rows, ignore_index=True)
    detail.to_csv(os.path.join(RESULTS_DIR, "diagnostics_dm_per_ticker.csv"), index=False)

    summary = pd.DataFrame(summary_rows).sort_values("mean_tstat_across_tickers")
    out = os.path.join(RESULTS_DIR, "diagnostics_dm_per_ticker_summary.csv")
    summary.to_csv(out, index=False)
    logger.info(f"Per-ticker Diebold-Mariano (approx) vs random_walk, h=30, aggregated:\n{summary.to_string(index=False)}")
    return detail, summary


# ---------------------------------------------------------------------------
# 7. Win counts within production-4 and production-4+random_walk, by fold
#    and by ticker. (The win_count column in summary_by_model_tier.csv
#    counts across all 10 variants, which is misleading because the three
#    Prophet variants split wins -- this adds the narrower comparisons.)
# ---------------------------------------------------------------------------
def run_win_counts(folds: pd.DataFrame):
    ok = folds.dropna(subset=["rmse_pct"])
    comparisons = {
        "prod4": PROD_MODELS,
        "prod4_plus_rw": PROD_MODELS + ["random_walk"],
    }

    rows = []
    for label, models in comparisons.items():
        sub = ok[ok["model"].isin(models)]

        # By fold: lowest rmse_pct among `models` for each (ticker, origin_date).
        pivot = sub.pivot_table(index=["ticker", "origin_date"], columns="model", values="rmse_pct")
        pivot = pivot.dropna(how="any")  # only folds where all `models` have a value
        winners_fold = pivot.idxmin(axis=1).value_counts()
        n_folds = len(pivot)
        for model in models:
            rows.append({
                "comparison_set": label, "aggregation": "by_fold", "model": model,
                "win_count": int(winners_fold.get(model, 0)), "n_total": n_folds,
                "win_rate": (winners_fold.get(model, 0) / n_folds) if n_folds else None,
            })

        # By ticker: lowest mean rmse_pct among `models`, per ticker.
        by_ticker_mean = sub.groupby(["ticker", "model"])["rmse_pct"].mean().unstack("model")
        by_ticker_mean = by_ticker_mean.dropna(how="any")
        winners_ticker = by_ticker_mean.idxmin(axis=1).value_counts()
        n_tickers = len(by_ticker_mean)
        for model in models:
            rows.append({
                "comparison_set": label, "aggregation": "by_ticker", "model": model,
                "win_count": int(winners_ticker.get(model, 0)), "n_total": n_tickers,
                "win_rate": (winners_ticker.get(model, 0) / n_tickers) if n_tickers else None,
            })

    df = pd.DataFrame(rows)
    out = os.path.join(RESULTS_DIR, "diagnostics_win_counts.csv")
    df.to_csv(out, index=False)
    logger.info(f"Win counts (prod-4 and prod-4+RW, by fold and by ticker):\n{df.to_string(index=False)}")
    return df


# ---------------------------------------------------------------------------
# 8. Distribution of selected_config for the optimized tiers
# ---------------------------------------------------------------------------
def run_selected_config_distribution(folds: pd.DataFrame):
    sub = folds[folds["model"].isin(OPTIMIZED_MODELS)].dropna(subset=["selected_config"])
    dist = sub.groupby(["model", "selected_config"]).size().rename("count").reset_index()
    dist["pct"] = dist["count"] / dist.groupby("model")["count"].transform("sum") * 100
    dist = dist.sort_values(["model", "count"], ascending=[True, False])
    out = os.path.join(RESULTS_DIR, "diagnostics_selected_config_distribution.csv")
    dist.to_csv(out, index=False)
    logger.info(f"selected_config distribution (optimized tiers):\n{dist.to_string(index=False)}")
    return dist


def main():
    os.makedirs(RESULTS_DIR, exist_ok=True)
    folds = pd.read_csv(FOLDS_CSV)
    paths = pd.read_csv(PATHS_CSV)

    logger.info("=== 3. MAPE by horizon ===")
    run_mape_by_horizon(paths)
    logger.info("=== 4. anchoring analysis ===")
    run_anchoring(paths)
    logger.info("=== 6a. ticker-clustered paired tests vs random_walk ===")
    run_ticker_clustered(folds)
    logger.info("=== 6b. diebold-mariano per ticker, h=30 ===")
    run_dm_per_ticker(paths)
    logger.info("=== 7. win counts (prod4 / prod4+rw, by fold / by ticker) ===")
    run_win_counts(folds)
    logger.info("=== 8. selected_config distribution ===")
    run_selected_config_distribution(folds)
    logger.info("DONE")


if __name__ == "__main__":
    main()
