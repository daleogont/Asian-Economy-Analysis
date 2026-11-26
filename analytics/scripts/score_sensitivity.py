"""
Score sensitivity sweep: how much does the Score formula's top-3 ranking
move if the default budgets (latency 200ms, train time 2s, memory 10MB)
are wrong by up to 2x in either direction?

Mirrors the Score formula used client-side in
client/src/utils/score.js — kept in sync by hand, since one is JS and one
is Python and there's no shared module between them.

Run inside the python-api container:
    docker compose exec python-api python scripts/score_sensitivity.py [ticker]
"""
import itertools
import logging
import os
import sys
import warnings

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd

from app.db import fetch_df
from app.routers.models import MODEL_REGISTRY

warnings.filterwarnings("ignore")
logging.getLogger("cmdstanpy").setLevel(logging.WARNING)
logging.getLogger("prophet").setLevel(logging.WARNING)
logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger("score_sensitivity")

DEFAULT_TICKER = "9988.HK"
DEFAULT_BUDGETS = {"latency_ms": 200.0, "train_time_s": 2.0, "memory_mb": 10.0}
MULTIPLIERS = [0.5, 1.0, 2.0]


def _budget_ratio(cost, budget):
    if cost is None or cost <= 0:
        return 1.0
    if budget <= 0:
        return 0.0
    return min(1.0, budget / cost)


def score(rmse, rmse_min, costs, budgets):
    if rmse is None or rmse_min is None or rmse <= 0 or rmse_min <= 0:
        return None
    accuracy_ratio = rmse_min / rmse
    penalty = (
        _budget_ratio(costs["latency_ms"], budgets["latency_ms"])
        * _budget_ratio(costs["train_time_s"], budgets["train_time_s"])
        * _budget_ratio(costs["memory_mb"], budgets["memory_mb"])
    )
    return 100 * accuracy_ratio * penalty


def fetch_series(ticker: str, period_days: int = 365) -> pd.Series:
    df = fetch_df(
        """
        SELECT date, close FROM daily_prices
        WHERE ticker = :ticker AND date >= CURRENT_DATE - (:days || ' days')::interval
          AND close IS NOT NULL
        ORDER BY date ASC
        """,
        {"ticker": ticker, "days": period_days},
    )
    df["date"] = pd.to_datetime(df["date"])
    df["close"] = df["close"].astype(float)
    return df.set_index("date")["close"].asfreq("B").ffill()


def run_all_models(ticker: str) -> dict:
    series = fetch_series(ticker)
    costs = {}
    for name, cls in MODEL_REGISTRY.items():
        try:
            result = cls().run(series, steps=30)
            m = result["metrics"]
            if m.get("rmse") is None:
                continue
            costs[name] = {
                "rmse": m["rmse"], "latency_ms": m["inference_latency_ms"],
                "train_time_s": m["train_time_s"], "memory_mb": m["memory_mb"],
            }
        except Exception as exc:
            logger.warning(f"{name} failed: {exc}")
    return costs


def main():
    ticker = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_TICKER
    logger.info(f"Running all models on {ticker} (this fits every registered model once)...")
    costs = run_all_models(ticker)
    rmse_min = min(c["rmse"] for c in costs.values())

    def top3(budgets):
        scored = {m: score(c["rmse"], rmse_min, c, budgets) for m, c in costs.items()}
        ranked = sorted(scored.items(), key=lambda kv: kv[1] if kv[1] is not None else -1, reverse=True)
        return tuple(m for m, _ in ranked[:3]), scored

    baseline_top3, baseline_scores = top3(DEFAULT_BUDGETS)
    logger.info(f"Baseline (1x,1x,1x) top 3: {baseline_top3}")
    logger.info(f"Baseline scores: { {m: round(s, 2) for m, s in baseline_scores.items() if s is not None} }")

    changed = []
    for lat_mult, train_mult, mem_mult in itertools.product(MULTIPLIERS, MULTIPLIERS, MULTIPLIERS):
        budgets = {
            "latency_ms":   DEFAULT_BUDGETS["latency_ms"] * lat_mult,
            "train_time_s": DEFAULT_BUDGETS["train_time_s"] * train_mult,
            "memory_mb":    DEFAULT_BUDGETS["memory_mb"] * mem_mult,
        }
        combo_top3, _ = top3(budgets)
        is_changed = combo_top3 != baseline_top3
        if is_changed:
            changed.append((lat_mult, train_mult, mem_mult, combo_top3))

    total = len(MULTIPLIERS) ** 3
    logger.info(f"\n{total} budget combinations checked ({MULTIPLIERS} x each of latency/train_time/memory).")
    logger.info(f"Top-3 changed in {len(changed)}/{total} combinations:")
    for lat_mult, train_mult, mem_mult, combo_top3 in changed:
        logger.info(f"  latency x{lat_mult}, train_time x{train_mult}, memory x{mem_mult} -> {combo_top3}")

    return {"baseline_top3": baseline_top3, "changed_combinations": changed, "total_combinations": total}


if __name__ == "__main__":
    main()
