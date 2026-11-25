from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from app.batch_benchmark import DEFAULT_MODELS, friedman_wilcoxon_holm, run_one, summarize


def _series(n=200, seed=0):
    import numpy as np
    idx = pd.bdate_range("2024-01-01", periods=n)
    rng = np.random.RandomState(seed)
    return pd.Series(100 + rng.normal(0, 1, n).cumsum(), index=idx)


def test_default_models_excludes_lstm():
    assert "lstm" not in DEFAULT_MODELS
    assert "naive" in DEFAULT_MODELS
    assert "arima" in DEFAULT_MODELS


def test_run_one_naive_succeeds_and_reports_ce_metrics():
    row = run_one("TEST.XX", "naive", _series(), horizon=10)
    assert row["error"] is None
    assert row["rmse"] is not None
    assert row["rmse_pct"] is not None
    assert row["inference_latency_ms"] is not None


def test_run_one_unknown_model_reports_error_not_exception():
    row = run_one("TEST.XX", "not_a_model", _series(), horizon=10)
    assert row["error"] is not None
    assert row["rmse"] is None


def _rows(ticker_model_rmse):
    """ticker_model_rmse: {ticker: {model: rmse_or_None}}"""
    rows = []
    for ticker, by_model in ticker_model_rmse.items():
        for model, rmse in by_model.items():
            rows.append({
                "ticker": ticker, "model": model, "error": None if rmse is not None else "failed",
                "rmse": rmse, "mae": rmse, "rmse_pct": rmse, "inference_latency_ms": 1.0,
                "train_time_s": 0.1, "memory_mb": 0.1,
            })
    return rows


def test_summarize_rank_table_and_best_model_count():
    rows = _rows({
        "T1": {"m1": 1.0, "m2": 2.0},
        "T2": {"m1": 3.0, "m2": 1.0},
    })
    agg = summarize(rows, ["m1", "m2"], ["T1", "T2"])
    assert agg["rank_table"]["T1"] == {"m1": 1, "m2": 2}
    assert agg["rank_table"]["T2"] == {"m1": 2, "m2": 1}
    assert agg["model_summary"]["m1"]["best_model_count"] == 1
    assert agg["model_summary"]["m2"]["best_model_count"] == 1
    assert agg["zero_error_tickers"] == []


def test_summarize_flags_zero_error_tickers():
    rows = _rows({
        "T1": {"m1": 0.0, "m2": 0.0},  # degenerate -- every model ~0
        "T2": {"m1": 3.0, "m2": 1.0},
    })
    agg = summarize(rows, ["m1", "m2"], ["T1", "T2"])
    assert agg["zero_error_tickers"] == ["T1"]


def test_friedman_wilcoxon_holm_needs_three_tickers_and_models():
    rows = _rows({"T1": {"m1": 1.0, "m2": 2.0}})
    result = friedman_wilcoxon_holm(rows, ["m1", "m2"], ["T1"])
    assert "note" in result


def test_friedman_wilcoxon_holm_runs_on_a_complete_matrix():
    rows = _rows({
        "T1": {"m1": 1.0, "m2": 2.0, "m3": 1.5},
        "T2": {"m1": 3.0, "m2": 1.0, "m3": 2.0},
        "T3": {"m1": 2.0, "m2": 2.5, "m3": 1.0},
    })
    result = friedman_wilcoxon_holm(rows, ["m1", "m2", "m3"], ["T1", "T2", "T3"])
    assert result["complete_tickers"] == ["T1", "T2", "T3"]
    assert "friedman" in result
    assert len(result["pairwise_wilcoxon_holm"]) == 3  # 3 models -> 3 pairs
    for p in result["pairwise_wilcoxon_holm"]:
        assert 0 <= p["p_value_holm"] <= 1


# ---------------------------------------------------------------------------
# API-level
# ---------------------------------------------------------------------------
def test_start_batch_benchmark_requires_tickers_or_country_or_sector(client):
    resp = client.post("/analytics/batch-benchmark", json={"models": ["naive"]})
    assert resp.status_code == 400


def test_start_batch_benchmark_rejects_unknown_model(client):
    resp = client.post("/analytics/batch-benchmark", json={"tickers": ["9988.HK"], "models": ["not_a_model"]})
    assert resp.status_code == 400


def test_start_batch_benchmark_enqueues_with_explicit_tickers(client):
    with patch("app.routers.batch_benchmark.run_batch_benchmark") as mock_task:
        mock_task.apply_async.return_value.id = "fake-task-id"
        resp = client.post("/analytics/batch-benchmark", json={"tickers": ["9988.HK", "0001.hk"], "models": ["naive"]})
    assert resp.status_code == 200
    body = resp.json()
    assert body["task_id"] == "fake-task-id"
    assert body["tickers"] == ["9988.HK", "0001.HK"]  # upper-cased
    mock_task.apply_async.assert_called_once()


def test_start_batch_benchmark_resolves_tickers_by_country(client):
    companies_df = pd.DataFrame({"ticker": ["AAA.T", "BBB.T"]})
    with patch("app.routers.batch_benchmark.fetch_df", return_value=companies_df), \
         patch("app.routers.batch_benchmark.run_batch_benchmark") as mock_task:
        mock_task.apply_async.return_value.id = "fake-task-id"
        resp = client.post("/analytics/batch-benchmark", json={"country": "Japan", "models": ["naive"]})
    assert resp.status_code == 200
    assert resp.json()["tickers"] == ["AAA.T", "BBB.T"]


def test_batch_benchmark_status_reports_progress():
    from fastapi.testclient import TestClient
    from app.main import app
    client = TestClient(app)

    fake_result = MagicMock(status="PROGRESS", state="PROGRESS", info={"done": 3, "total": 10})
    with patch("app.routers.batch_benchmark.AsyncResult", return_value=fake_result):
        resp = client.get("/analytics/batch-benchmark/some-id/status")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "PROGRESS"
    assert body["progress"] == {"done": 3, "total": 10}


def test_batch_benchmark_results_not_ready_returns_null_result(client):
    fake_result = MagicMock()
    fake_result.ready.return_value = False
    fake_result.status = "PROGRESS"
    with patch("app.routers.batch_benchmark.AsyncResult", return_value=fake_result):
        resp = client.get("/analytics/batch-benchmark/some-id/results")
    assert resp.status_code == 200
    assert resp.json()["result"] is None


def test_batch_benchmark_results_returns_payload_on_success(client):
    fake_result = MagicMock()
    fake_result.ready.return_value = True
    fake_result.failed.return_value = False
    fake_result.status = "SUCCESS"
    fake_result.result = {"rows": []}
    with patch("app.routers.batch_benchmark.AsyncResult", return_value=fake_result):
        resp = client.get("/analytics/batch-benchmark/some-id/results")
    assert resp.status_code == 200
    assert resp.json()["result"] == {"rows": []}
