"""
Batch benchmark — shared core used by the Celery task in tasks.py. Runs
every (ticker, model) pair through the same single-holdout protocol the
rest of the app already uses (BaseForecastModel.run(), 80/20 holdout,
one fit+predict per pair), just looped across many tickers/models instead
of one forecast request.
"""
import numpy as np

from app.routers.models import MODEL_REGISTRY

# LSTM is excluded from the default set — its per-fit cost (seconds, not
# milliseconds) multiplies fast across many tickers. Still runnable if
# explicitly requested in `models`.
DEFAULT_MODELS = [k for k in MODEL_REGISTRY if k != "lstm"]

# A ticker where every requested model lands at (near-)zero RMSE usually
# means degenerate/flat price data for that ticker, not a genuinely easy
# forecast -- worth flagging rather than letting it skew "best model"
# counts or distort chart scales.
ZERO_ERROR_THRESHOLD = 1e-6


def run_one(ticker: str, model_key: str, series, horizon: int) -> dict:
    """Runs one (ticker, model) pair and returns a flat result row."""
    row = {
        "ticker": ticker, "model": model_key, "error": None,
        "rmse": None, "mae": None, "rmse_pct": None,
        "inference_latency_ms": None, "train_time_s": None, "memory_mb": None,
    }
    try:
        instance = MODEL_REGISTRY[model_key]()
        result = instance.run(series, steps=horizon)
        metrics = result["metrics"]
    except Exception as exc:
        row["error"] = str(exc)[:300]
        return row

    row.update({
        "rmse": metrics.get("rmse"),
        "mae": metrics.get("mae"),
        "inference_latency_ms": metrics.get("inference_latency_ms"),
        "train_time_s": metrics.get("train_time_s"),
        "memory_mb": metrics.get("memory_mb"),
    })
    if metrics.get("rmse") is not None:
        mean_close = float(series.to_numpy().mean())
        row["rmse_pct"] = round(metrics["rmse"] / mean_close * 100, 4) if mean_close else None
    return row


def summarize(rows: list, models: list, tickers: list) -> dict:
    """Per-model aggregates, a model x ticker rank table, and the tickers
    where every model scored ~0 RMSE (flagged, never silently dropped)."""
    by_ticker = {t: {r["model"]: r for r in rows if r["ticker"] == t} for t in tickers}

    zero_error_tickers = []
    for t, model_rows in by_ticker.items():
        scored = [r for r in model_rows.values() if r["rmse"] is not None]
        if scored and all(r["rmse"] <= ZERO_ERROR_THRESHOLD for r in scored):
            zero_error_tickers.append(t)

    rank_table = {}  # ticker -> {model -> rank (1 = best RMSE), or None}
    for t, model_rows in by_ticker.items():
        scored = sorted(
            ((m, r["rmse"]) for m, r in model_rows.items() if r["rmse"] is not None),
            key=lambda pair: pair[1],
        )
        ranks = {m: i + 1 for i, (m, _) in enumerate(scored)}
        rank_table[t] = {m: ranks.get(m) for m in models}

    model_summary = {}
    for m in models:
        model_rows = [r for r in rows if r["model"] == m and r["rmse"] is not None]
        rmse_pct_vals = [r["rmse_pct"] for r in model_rows if r["rmse_pct"] is not None]
        best_count = sum(1 for t in tickers if rank_table.get(t, {}).get(m) == 1)
        model_summary[m] = {
            "n_tickers":      len(model_rows),
            "mean_rmse_pct":  round(float(np.mean(rmse_pct_vals)), 4) if rmse_pct_vals else None,
            "std_rmse_pct":   round(float(np.std(rmse_pct_vals)), 4) if rmse_pct_vals else None,
            "best_model_count": best_count,
        }

    return {
        "model_summary":       model_summary,
        "rank_table":          rank_table,
        "zero_error_tickers":  zero_error_tickers,
    }


def friedman_wilcoxon_holm(rows: list, models: list, tickers: list) -> dict:
    """Friedman test across models + pairwise Wilcoxon signed-rank with
    Holm correction, on the tickers where every model produced an RMSE
    (an incomplete matrix can't feed either test)."""
    from scipy.stats import friedmanchisquare, wilcoxon
    from statsmodels.stats.multitest import multipletests

    by_ticker = {t: {r["model"]: r["rmse"] for r in rows if r["ticker"] == t} for t in tickers}
    complete_tickers = [
        t for t in tickers
        if all(by_ticker[t].get(m) is not None for m in models)
    ]
    if len(complete_tickers) < 3 or len(models) < 3:
        return {
            "complete_tickers": complete_tickers,
            "note": "Need at least 3 tickers with every model scored, and at least 3 models, "
                    "to run Friedman/Wilcoxon.",
        }

    samples = {m: [by_ticker[t][m] for t in complete_tickers] for m in models}
    friedman_stat, friedman_p = friedmanchisquare(*[samples[m] for m in models])

    pairwise = []
    for i in range(len(models)):
        for j in range(i + 1, len(models)):
            a, b = models[i], models[j]
            try:
                stat, p = wilcoxon(samples[a], samples[b])
            except ValueError:
                stat, p = None, 1.0  # identical samples -> wilcoxon undefined, treat as non-significant
            pairwise.append({"model_a": a, "model_b": b, "statistic": stat, "p_value": p})

    _, holm_corrected, _, _ = multipletests([p["p_value"] for p in pairwise], method="holm")
    for p, corrected in zip(pairwise, holm_corrected):
        p["p_value_holm"] = round(float(corrected), 6)
        p["p_value"] = round(float(p["p_value"]), 6)
        if p["statistic"] is not None:
            p["statistic"] = round(float(p["statistic"]), 4)

    return {
        "complete_tickers": complete_tickers,
        "friedman": {"statistic": round(float(friedman_stat), 4), "p_value": round(float(friedman_p), 6)},
        "pairwise_wilcoxon_holm": pairwise,
    }
