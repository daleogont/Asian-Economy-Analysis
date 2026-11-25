"""
STEP 3 — why does Prophet underperform on single-equity series?

Hypothesis: prices are near a random walk; Prophet fits one smooth curve
and under-weights the last observation, so its error decomposes into a
level offset (its fitted curve sits above/below the last actual close)
plus a slope-extrapolation term that ARIMA/ETS/random-walk don't carry;
and with ~1y of data the yearly Fourier terms are fit from a single cycle.

Outputs (research/results/):
  diagnostics_stationarity.csv      -- ADF+KPSS on price levels & log price, per ticker
  diagnostics_ljungbox.csv          -- Ljung-Box(10,20) on Prophet vs random-walk in-sample residuals, per ticker, at the last origin
  diagnostics_prophet_decomp.csv    -- per-origin level/slope decomposition of Prophet's forecast error, per ticker
  diagnostics_prophet_ablation.csv  -- yearly seasonality on/off, derived from rolling_folds.csv (tiers A vs D)
  diagnostics_window_length.csv     -- training window length 1y/3y/5y ablation at fixed origins
  diagnostics_diebold_mariano.csv   -- DM test of each model vs random_walk, h=30, pooled across tickers

Depends on research/results/rolling_folds.csv and forecast_paths.csv
having already been produced by rolling_benchmark.py (for the ablation
and DM-test parts). Run AFTER the rolling benchmark finishes -- not
concurrently -- so CPU contention doesn't bias either run's timings.
"""
import itertools
import logging
import os
import sys
import warnings

import numpy as np
import pandas as pd
from prophet import Prophet
from scipy import stats
from statsmodels.stats.diagnostic import acorr_ljungbox
from statsmodels.tsa.stattools import adfuller, kpss

warnings.filterwarnings("ignore")
logging.getLogger("cmdstanpy").setLevel(logging.WARNING)
logging.getLogger("prophet").setLevel(logging.WARNING)
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s", stream=sys.stdout)
logger = logging.getLogger("diagnostics")

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from common import PAPER_TICKERS, fetch_df, fetch_series  # noqa: E402
from rolling_benchmark import HORIZON, MIN_TRAIN_DAYS, STEP, origins_for  # noqa: E402

RESULTS_DIR = os.path.join(HERE, "results")
FOLDS_CSV = os.path.join(RESULTS_DIR, "rolling_folds.csv")
PATHS_CSV = os.path.join(RESULTS_DIR, "forecast_paths.csv")
FULL_PERIOD_DAYS = 5 * 365 + 10


def _production_prophet(df):
    m = Prophet(daily_seasonality=False, weekly_seasonality=True, yearly_seasonality=True)
    m.fit(df)
    return m


# ---------------------------------------------------------------------------
# 1. ADF / KPSS on price levels and log prices
# ---------------------------------------------------------------------------
def run_stationarity():
    rows = []
    for ticker in PAPER_TICKERS:
        series = fetch_series(ticker, period_days=FULL_PERIOD_DAYS)
        log_series = np.log(series)
        for label, s in (("level", series), ("log", log_series)):
            try:
                adf_stat, adf_p = adfuller(s.dropna(), autolag="AIC")[:2]
            except Exception:
                adf_stat, adf_p = None, None
            try:
                kpss_stat, kpss_p = kpss(s.dropna(), regression="c", nlags="auto")[:2]
            except Exception:
                kpss_stat, kpss_p = None, None
            rows.append({
                "ticker": ticker, "transform": label,
                "adf_stat": adf_stat, "adf_pvalue": adf_p,
                "adf_nonstationary_at_5pct": (adf_p is not None and adf_p > 0.05),
                "kpss_stat": kpss_stat, "kpss_pvalue": kpss_p,
                "kpss_nonstationary_at_5pct": (kpss_p is not None and kpss_p < 0.05),
            })
        logger.info(f"stationarity: {ticker} done")

    df = pd.DataFrame(rows)
    out = os.path.join(RESULTS_DIR, "diagnostics_stationarity.csv")
    df.to_csv(out, index=False)

    summary = df.groupby("transform")[["adf_nonstationary_at_5pct", "kpss_nonstationary_at_5pct"]].mean()
    logger.info(f"Share of tickers flagged non-stationary by transform:\n{summary}")
    return df


# ---------------------------------------------------------------------------
# 2. Ljung-Box on Prophet vs random-walk in-sample residuals at last origin
# ---------------------------------------------------------------------------
def run_ljungbox():
    rows = []
    for ticker in PAPER_TICKERS:
        series = fetch_series(ticker, period_days=FULL_PERIOD_DAYS)
        origins = origins_for(len(series), MIN_TRAIN_DAYS, STEP, HORIZON)
        if not origins:
            continue
        train = series.iloc[: origins[-1]]

        df = pd.DataFrame({"ds": train.index, "y": train.to_numpy()})
        try:
            m = _production_prophet(df)
            fitted = m.predict(df)["yhat"].to_numpy()
            prophet_resid = train.to_numpy() - fitted
        except Exception as exc:
            logger.warning(f"{ticker}: prophet fit failed for ljung-box ({exc})")
            continue

        rw_resid = train.diff().dropna().to_numpy()  # one-step random-walk residuals

        for label, resid in (("prophet", prophet_resid), ("random_walk", rw_resid)):
            try:
                lb = acorr_ljungbox(resid, lags=[10, 20], return_df=True)
                rows.append({
                    "ticker": ticker, "series": label,
                    "lb_stat_10": lb.loc[10, "lb_stat"], "lb_pvalue_10": lb.loc[10, "lb_pvalue"],
                    "lb_stat_20": lb.loc[20, "lb_stat"], "lb_pvalue_20": lb.loc[20, "lb_pvalue"],
                })
            except Exception as exc:
                logger.warning(f"{ticker}/{label}: ljung-box failed ({exc})")
        logger.info(f"ljung-box: {ticker} done")

    df = pd.DataFrame(rows)
    out = os.path.join(RESULTS_DIR, "diagnostics_ljungbox.csv")
    df.to_csv(out, index=False)
    return df


# ---------------------------------------------------------------------------
# 3. Prophet level-offset / slope-error decomposition, every origin
# ---------------------------------------------------------------------------
def run_prophet_decomposition():
    rows = []
    for ti, ticker in enumerate(PAPER_TICKERS, 1):
        series = fetch_series(ticker, period_days=FULL_PERIOD_DAYS)
        origins = origins_for(len(series), MIN_TRAIN_DAYS, STEP, HORIZON)

        for origin_idx in origins:
            train = series.iloc[:origin_idx]
            actual_horizon = series.iloc[origin_idx: origin_idx + HORIZON]
            if len(actual_horizon) < HORIZON:
                continue
            origin_date = str(series.index[origin_idx - 1].date())

            df = pd.DataFrame({"ds": train.index, "y": train.to_numpy()})
            try:
                m = _production_prophet(df)
                fitted_T = float(m.predict(df)["yhat"].iloc[-1])
                future = pd.date_range(train.index[-1], periods=HORIZON + 1, freq=train.index.freq or "B")[1:]
                fc = m.predict(pd.DataFrame({"ds": future}))["yhat"].to_numpy()
            except Exception as exc:
                logger.warning(f"{ticker}/{origin_date}: prophet fit failed ({exc})")
                continue

            close_T = float(train.iloc[-1])
            actual = actual_horizon.to_numpy()

            u_T = close_T - fitted_T  # level offset
            realized_slope = (actual[-1] - close_T) / HORIZON
            forecast_slope = (fc[-1] - fitted_T) / HORIZON
            slope_error = realized_slope - forecast_slope

            err = fc - actual
            sse_actual = float(np.sum(err ** 2))

            h = np.arange(1, HORIZON + 1)
            level_contrib = float(HORIZON * u_T ** 2)
            cross_contrib = float(2 * u_T * slope_error * h.sum())
            slope_contrib = float(slope_error ** 2 * np.sum(h ** 2))
            sse_approx = level_contrib + cross_contrib + slope_contrib

            denom = sse_approx if sse_approx != 0 else np.nan
            rows.append({
                "ticker": ticker, "origin_date": origin_date,
                "close_T": close_T, "fitted_T": fitted_T, "level_offset_u": u_T,
                "realized_slope": realized_slope, "forecast_slope": forecast_slope,
                "slope_error": slope_error,
                "sse_actual": sse_actual, "sse_linear_approx": sse_approx,
                "level_share": level_contrib / denom if denom else None,
                "slope_share": slope_contrib / denom if denom else None,
                "cross_share": cross_contrib / denom if denom else None,
            })
        logger.info(f"prophet decomposition: [{ti}/{len(PAPER_TICKERS)}] {ticker} done ({len(origins)} origins)")

    df = pd.DataFrame(rows)
    out = os.path.join(RESULTS_DIR, "diagnostics_prophet_decomp.csv")
    df.to_csv(out, index=False)
    logger.info(
        "Decomposition used: linearizing Prophet's forecast as fitted_T + "
        "forecast_slope*h and the realized path as close_T + realized_slope*h, "
        "so squared error at h decomposes as u_T^2 + 2*u_T*slope_error*h + "
        "slope_error^2*h^2 (level + cross + slope terms), summed over h=1..30. "
        "This ignores Prophet's seasonal wiggle around its trend line -- "
        "sse_linear_approx vs sse_actual in the CSV shows how good that "
        "approximation is per fold."
    )
    return df


# ---------------------------------------------------------------------------
# 4a. Prophet seasonality ablation -- derived from rolling_folds.csv (tiers A/D)
# ---------------------------------------------------------------------------
def run_prophet_seasonality_ablation():
    if not os.path.exists(FOLDS_CSV):
        logger.warning(f"{FOLDS_CSV} not found -- run rolling_benchmark.py first. Skipping.")
        return None
    df = pd.read_csv(FOLDS_CSV)
    sub = df[df["model"].isin(["prophet", "prophet_no_yearly"])].dropna(subset=["rmse"])
    summary = sub.groupby("model")[["rmse", "rmse_pct", "mae", "mase"]].agg(["mean", "median", "std"])
    out = os.path.join(RESULTS_DIR, "diagnostics_prophet_ablation.csv")
    summary.to_csv(out)
    logger.info(f"Prophet yearly-seasonality ablation (from rolling_folds.csv):\n{summary}")
    return summary


# ---------------------------------------------------------------------------
# 4b. Training window length ablation: 1y / 3y / 5y at fixed origins
# ---------------------------------------------------------------------------
WINDOW_YEARS = {"1y": 252, "3y": 756, "5y": 1260}


def run_window_length_ablation():
    # NOTE: this originally required a literal 1260-business-day ("5y")
    # history before the chosen origin (usable = origins with idx >= 1260)
    # and skipped any ticker that didn't have one. In practice NO ticker in
    # this 30-ticker sample reaches 1260 business days before its last
    # origin (max across all 30 is 1224, ~4.85y) -- consistent with the
    # README's own "4.3-5.0 years of history" characterization -- so
    # `usable` was empty for every ticker, producing an all-empty rows list
    # and crashing on `df.dropna(subset=["rmse"])` (no such column on an
    # empty-built DataFrame). Fixed by using each ticker's own LAST origin
    # (maximum available training history) as the fixed origin, and letting
    # the "5y" tier mean "as much history as is actually available, capped
    # at 1260 days" rather than a literal 1260-day window -- the actual
    # n_train used is recorded per row, so nothing here is fabricated: the
    # "5y" rows will show n_train ~1219-1224 (~4.85y), not 1260.
    rows = []
    for ticker in PAPER_TICKERS:
        series = fetch_series(ticker, period_days=FULL_PERIOD_DAYS)
        origins = origins_for(len(series), MIN_TRAIN_DAYS, STEP, HORIZON)
        if not origins:
            continue
        origin_idx = origins[-1]  # last origin = max available training history for this ticker
        origin_date = str(series.index[origin_idx - 1].date())
        actual_horizon = series.iloc[origin_idx: origin_idx + HORIZON].to_numpy()
        if len(actual_horizon) < HORIZON:
            continue

        for label, n_days in WINDOW_YEARS.items():
            train = series.iloc[max(0, origin_idx - n_days): origin_idx]
            df = pd.DataFrame({"ds": train.index, "y": train.to_numpy()})
            try:
                m = _production_prophet(df)
                future = pd.date_range(train.index[-1], periods=HORIZON + 1, freq=train.index.freq or "B")[1:]
                fc = m.predict(pd.DataFrame({"ds": future}))["yhat"].to_numpy()
                rmse = float(np.sqrt(np.mean((fc - actual_horizon) ** 2)))
                mae = float(np.mean(np.abs(fc - actual_horizon)))
            except Exception as exc:
                logger.warning(f"{ticker}/{label}: window-length fit failed ({exc})")
                rmse, mae = None, None
            rows.append({
                "ticker": ticker, "origin_date": origin_date, "window": label,
                "n_train": len(train), "rmse": rmse, "mae": mae,
            })
        logger.info(f"window-length ablation: {ticker} done")

    df = pd.DataFrame(rows)
    out = os.path.join(RESULTS_DIR, "diagnostics_window_length.csv")
    df.to_csv(out, index=False)
    summary = df.dropna(subset=["rmse"]).groupby("window")[["rmse", "mae"]].agg(["mean", "median"])
    logger.info(f"Window-length ablation summary:\n{summary}")
    return df


# ---------------------------------------------------------------------------
# 5. Diebold-Mariano vs random_walk, h=30, pooled across tickers
# ---------------------------------------------------------------------------
def run_diebold_mariano():
    if not os.path.exists(PATHS_CSV):
        logger.warning(f"{PATHS_CSV} not found -- run rolling_benchmark.py first. Skipping.")
        return None
    paths = pd.read_csv(PATHS_CSV)
    h30 = paths[paths["h"] == HORIZON].copy()
    h30["sq_err"] = (h30["forecast"] - h30["actual"]) ** 2

    rw = h30[h30["model"] == "random_walk"][["ticker", "origin_date", "sq_err"]].rename(
        columns={"sq_err": "sq_err_rw"}
    )

    rows = []
    models = [m for m in h30["model"].unique() if m != "random_walk"]
    for model in models:
        other = h30[h30["model"] == model][["ticker", "origin_date", "sq_err"]].rename(
            columns={"sq_err": "sq_err_model"}
        )
        merged = other.merge(rw, on=["ticker", "origin_date"], how="inner")
        d = (merged["sq_err_model"] - merged["sq_err_rw"]).dropna().to_numpy()
        n = len(d)
        if n < 2:
            continue
        # Approximation used: pooled across tickers/origins, treating each
        # (ticker, origin) pair's non-overlapping 30-day-ahead squared-error
        # differential as one observation and running a simple one-sample
        # t-test (no HAC/Newey-West correction) on d_t. Non-overlap within a
        # ticker (step == horizon == 30) removes the usual within-ticker
        # serial-correlation problem DM corrects for; cross-ticker
        # contemporaneous correlation (shared market days) is NOT corrected
        # for here and is a known limitation of this pooled approximation.
        mean_d = float(np.mean(d))
        tstat, pvalue = stats.ttest_1samp(d, 0.0)
        rows.append({
            "model": model, "n_pairs": n, "mean_loss_diff": mean_d,
            "dm_tstat_approx": float(tstat), "dm_pvalue_approx": float(pvalue),
            "model_better_than_rw": mean_d < 0,
        })

    df = pd.DataFrame(rows).sort_values("mean_loss_diff")
    out = os.path.join(RESULTS_DIR, "diagnostics_diebold_mariano.csv")
    df.to_csv(out, index=False)
    logger.info(f"Diebold-Mariano (approx, pooled) vs random_walk at h=30:\n{df.to_string()}")
    return df


def main():
    os.makedirs(RESULTS_DIR, exist_ok=True)
    logger.info("=== 1. stationarity ===")
    run_stationarity()
    logger.info("=== 2. ljung-box ===")
    run_ljungbox()
    logger.info("=== 3. prophet decomposition ===")
    run_prophet_decomposition()
    logger.info("=== 4a. prophet seasonality ablation ===")
    run_prophet_seasonality_ablation()
    logger.info("=== 4b. window-length ablation ===")
    run_window_length_ablation()
    logger.info("=== 5. diebold-mariano ===")
    run_diebold_mariano()
    logger.info("DONE")


if __name__ == "__main__":
    main()
