import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts"))
from score_sensitivity import DEFAULT_BUDGETS, score  # noqa: E402


def test_score_matches_the_spec_example_set():
    """Same example the spec gave (9988.HK, default budgets): ETS=100,
    ARIMA~98.6, Ridge~97.1, LSTM~1.4 — using the exact metrics recorded in
    PROJECT_STATE.md's 8-model benchmark table at the time this was written."""
    rmse_min = 13.1653  # ets

    ets = score(13.1653, rmse_min, {"latency_ms": 156.9, "train_time_s": 0.339, "memory_mb": 0.48}, DEFAULT_BUDGETS)
    arima = score(13.3555, rmse_min, {"latency_ms": 92.6, "train_time_s": 0.419, "memory_mb": 0.86}, DEFAULT_BUDGETS)
    ridge = score(13.5570, rmse_min, {"latency_ms": 150.9, "train_time_s": 0.034, "memory_mb": 0.08}, DEFAULT_BUDGETS)
    lstm = score(18.0727, rmse_min, {"latency_ms": 110.7, "train_time_s": 21.573, "memory_mb": 47.50}, DEFAULT_BUDGETS)

    assert ets == pytest.approx(100, abs=0.01)
    assert arima == pytest.approx(98.58, abs=0.1)
    assert ridge == pytest.approx(97.11, abs=0.1)
    assert lstm == pytest.approx(1.42, abs=0.1)


def test_score_is_none_for_non_positive_rmse():
    assert score(0, 10, {"latency_ms": 1, "train_time_s": 1, "memory_mb": 1}, DEFAULT_BUDGETS) is None
    assert score(None, 10, {}, DEFAULT_BUDGETS) is None


def test_zero_budget_with_positive_cost_drives_score_to_zero():
    budgets = {**DEFAULT_BUDGETS, "latency_ms": 0}
    result = score(10, 10, {"latency_ms": 50, "train_time_s": 1, "memory_mb": 1}, budgets)
    assert result == 0
