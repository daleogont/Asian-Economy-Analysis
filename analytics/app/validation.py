"""
Rolling-origin cross-validation — shared core used by both the async
`/analytics/validation/rolling/{ticker}` endpoint (via the Celery task in
tasks.py) and the pytest suite. Mirrors research/rolling_benchmark.py's
methodology (expanding window, HORIZON=30, STEP=30, MIN_TRAIN=504) so the
production numbers this produces are comparable with the paper's, but
drives the *production* MODEL_REGISTRY classes instead of research-only
copies.
"""
import numpy as np
import pandas as pd

from app.routers.models import MODEL_REGISTRY

HORIZON_DEFAULT = 30
MIN_TRAIN_DEFAULT = 504  # ~2 years of business days, same as research/rolling_benchmark.py
STEP_DEFAULT = 30

# Cheap enough to run inline inside one Celery task across many origins.
# RF/XGBoost/LSTM are excluded unless the caller explicitly opts in
# (`allow_heavy=True`) because their per-fit cost multiplied by dozens of
# origins is substantial.
CHEAP_MODELS = ["arima", "ets", "sarima", "prophet", "ridge", "naive"]
HEAVY_MODELS = ["random_forest", "xgboost", "lstm"]
ALLOWED_MODELS = set(CHEAP_MODELS) | set(HEAVY_MODELS)

BASELINE_MODEL = "naive"


def origins_for(n: int, min_train: int, step: int, horizon: int) -> list[int]:
    """Business-day index positions marking the end of each training window."""
    out, idx = [], min_train
    while idx + horizon <= n:
        out.append(idx)
        idx += step
    return out


def resolve_models(models: list[str] | None, allow_heavy: bool) -> list[str]:
    """Validates the requested model list and guarantees the baseline is
    present. Raises ValueError on an unknown model, or a heavy model
    requested without allow_heavy=True."""
    requested = list(models) if models else list(CHEAP_MODELS)

    unknown = [m for m in requested if m not in ALLOWED_MODELS]
    if unknown:
        raise ValueError(f"Unknown model(s) for rolling-origin validation: {unknown}")

    if not allow_heavy:
        heavy_requested = [m for m in requested if m in HEAVY_MODELS]
        if heavy_requested:
            raise ValueError(
                f"Model(s) {heavy_requested} are only allowed with allow_heavy=true "
                f"(each origin re-fits from scratch, so cost multiplies fast)"
            )

    if BASELINE_MODEL not in requested:
        requested.append(BASELINE_MODEL)
    return requested


def _train_slice(series: pd.Series, origin_idx: int, min_train: int, window: str) -> pd.Series:
    if window == "sliding":
        return series.iloc[max(0, origin_idx - min_train):origin_idx]
    return series.iloc[:origin_idx]  # expanding (default)


def _fold_metrics(pred: np.ndarray, actual: np.ndarray, train: pd.Series) -> dict:
    err = pred - actual
    rmse = float(np.sqrt(np.mean(err ** 2)))
    mae = float(np.mean(np.abs(err)))
    mean_close = float(np.concatenate([train.to_numpy(), actual]).mean())
    rmse_pct = (rmse / mean_close * 100) if mean_close else None
    train_diffs = np.diff(train.to_numpy())
    naive_mae = float(np.mean(np.abs(train_diffs))) if len(train_diffs) else None
    mase = (mae / naive_mae) if naive_mae else None
    return {"rmse": rmse, "mae": mae, "rmse_pct": rmse_pct, "mase": mase}


def run_rolling_origin(
    series: pd.Series,
    models: list[str],
    min_train: int = MIN_TRAIN_DEFAULT,
    origin_step: int = STEP_DEFAULT,
    horizon: int = HORIZON_DEFAULT,
    window: str = "expanding",
    max_origins: int | None = None,
) -> dict:
    """Walk the forecast origin forward across `series`, fitting each of
    `models` fresh at every origin and scoring it against the realized
    next `horizon` values. Returns per-fold rows plus a per-model summary
    (mean/std of rmse_pct and mase, and each fold's error relative to the
    included naive baseline)."""
    n = len(series)
    origins = origins_for(n, min_train, origin_step, horizon)
    if max_origins:
        origins = origins[:max_origins]
    if not origins:
        raise ValueError(
            f"Not enough history for rolling-origin validation: have {n} rows, "
            f"need at least {min_train + horizon}"
        )

    folds = []
    for origin_idx in origins:
        train = _train_slice(series, origin_idx, min_train, window)
        actual_series = series.iloc[origin_idx: origin_idx + horizon]
        actual = actual_series.to_numpy()
        origin_date = str(series.index[origin_idx - 1].date())

        fold_results = {}
        for model_key in models:
            instance = MODEL_REGISTRY[model_key]()
            try:
                instance.fit(train)
                forecast = instance.predict(horizon)
                pred = np.asarray(forecast["mean"][:len(actual)], dtype=float)
                metrics = _fold_metrics(pred, actual, train) if len(pred) == len(actual) else None
                error = None if metrics else "prediction length mismatch"
            except Exception as exc:
                metrics, error = None, str(exc)[:300]

            fold_results[model_key] = {
                "origin_date": origin_date,
                "n_train": len(train),
                "error": error,
                **(metrics or {"rmse": None, "mae": None, "rmse_pct": None, "mase": None}),
            }

        baseline_rmse = fold_results.get(BASELINE_MODEL, {}).get("rmse")
        for model_key, row in fold_results.items():
            row["rmse_vs_naive"] = (
                row["rmse"] / baseline_rmse
                if row["rmse"] is not None and baseline_rmse not in (None, 0)
                else None
            )
            folds.append({"model": model_key, **row})

    summary = {}
    for model_key in models:
        model_folds = [f for f in folds if f["model"] == model_key and f["rmse"] is not None]
        if not model_folds:
            summary[model_key] = {"n_folds": 0}
            continue
        rmse_pct_vals = [f["rmse_pct"] for f in model_folds if f["rmse_pct"] is not None]
        mase_vals = [f["mase"] for f in model_folds if f["mase"] is not None]
        rel_vals = [f["rmse_vs_naive"] for f in model_folds if f["rmse_vs_naive"] is not None]
        summary[model_key] = {
            "n_folds":            len(model_folds),
            "mean_rmse_pct":      round(float(np.mean(rmse_pct_vals)), 4) if rmse_pct_vals else None,
            "std_rmse_pct":       round(float(np.std(rmse_pct_vals)), 4) if rmse_pct_vals else None,
            "mean_mase":          round(float(np.mean(mase_vals)), 4) if mase_vals else None,
            "std_mase":           round(float(np.std(mase_vals)), 4) if mase_vals else None,
            "mean_rmse_vs_naive": round(float(np.mean(rel_vals)), 4) if rel_vals else None,
        }

    return {
        "window": window,
        "min_train": min_train,
        "origin_step": origin_step,
        "horizon": horizon,
        "n_origins": len(origins),
        "folds": folds,
        "summary": summary,
    }
