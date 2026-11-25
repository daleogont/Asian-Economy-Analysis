import os
from unittest.mock import patch

import numpy as np
import pandas as pd
import pytest

from app.models.arima import ArimaModel
from app.validation import CHEAP_MODELS, HEAVY_MODELS, origins_for, resolve_models

FIXTURES_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fixtures")


# ---------------------------------------------------------------------------
# origins_for — pure window-stepping logic
# ---------------------------------------------------------------------------
def test_origins_for_basic_stepping():
    # n=100, min_train=50, step=10, horizon=10 -> origins at 50,60,70,80,90
    # (90+10=100 still fits; 100+10=110 would not)
    assert origins_for(100, 50, 10, 10) == [50, 60, 70, 80, 90]


def test_origins_for_not_enough_data():
    assert origins_for(40, 50, 10, 10) == []


# ---------------------------------------------------------------------------
# resolve_models — request validation
# ---------------------------------------------------------------------------
def test_resolve_models_defaults_to_cheap_set():
    assert resolve_models(None, allow_heavy=False) == CHEAP_MODELS


def test_resolve_models_always_includes_naive_baseline():
    resolved = resolve_models(["arima"], allow_heavy=False)
    assert "naive" in resolved


def test_resolve_models_rejects_unknown_model():
    with pytest.raises(ValueError):
        resolve_models(["not_a_real_model"], allow_heavy=False)


def test_resolve_models_rejects_heavy_without_flag():
    with pytest.raises(ValueError):
        resolve_models(["lstm"], allow_heavy=False)


def test_resolve_models_allows_heavy_with_flag():
    resolved = resolve_models(["lstm"], allow_heavy=True)
    assert "lstm" in resolved
    assert set(HEAVY_MODELS) & set(resolved) == {"lstm"}


# ---------------------------------------------------------------------------
# Reproduces the paper's numbers — 9988.HK, arima, origin 2023-09-12.
# Source: research/results/rolling_folds.csv, row
#   9988.HK,China,2023-09-12,504,arima,A,3.9706,3.1746,...
# The fixture CSV is a frozen snapshot (research/data/snapshot_2026-10-16.csv,
# trimmed to this one ticker) so this test needs no DB and is independent of
# how much daily_prices has grown since the paper's benchmark ran.
# ---------------------------------------------------------------------------
EXPECTED_RMSE = 3.9706
EXPECTED_MAE = 3.1746


def test_reproduces_paper_rolling_origin_fold():
    df = pd.read_csv(os.path.join(FIXTURES_DIR, "9988_HK_snapshot.csv"))
    df["date"] = pd.to_datetime(df["date"])
    series = df.set_index("date")["close"].astype(float).asfreq("B").ffill()

    origin_date = pd.Timestamp("2023-09-12")
    train = series.loc[:origin_date]
    horizon = 30
    actual = series.iloc[len(train): len(train) + horizon].to_numpy()

    model = ArimaModel()
    model.fit(train)
    forecast = model.predict(horizon)
    pred = np.asarray(forecast["mean"][:len(actual)], dtype=float)

    rmse = float(np.sqrt(np.mean((pred - actual) ** 2)))
    mae = float(np.mean(np.abs(pred - actual)))

    assert rmse == pytest.approx(EXPECTED_RMSE, abs=0.01)
    assert mae == pytest.approx(EXPECTED_MAE, abs=0.01)


# ---------------------------------------------------------------------------
# API-level: POST /analytics/validation/rolling/{ticker} must always enqueue
# to Celery, never run inline, and must validate before enqueuing.
# ---------------------------------------------------------------------------
def test_rolling_endpoint_enqueues_celery_task(client):
    with patch("app.routers.validation.run_rolling_validation") as mock_task:
        mock_task.apply_async.return_value.id = "fake-task-id"
        resp = client.post("/analytics/validation/rolling/9988.HK")

    assert resp.status_code == 200
    body = resp.json()
    assert body["task_id"] == "fake-task-id"
    assert body["status"] == "queued"
    assert "naive" in body["models"]
    mock_task.apply_async.assert_called_once()


def test_rolling_endpoint_rejects_heavy_model_without_flag(client):
    with patch("app.routers.validation.run_rolling_validation") as mock_task:
        resp = client.post("/analytics/validation/rolling/9988.HK?models=lstm")

    assert resp.status_code == 400
    mock_task.apply_async.assert_not_called()


def test_rolling_endpoint_rejects_unknown_model(client):
    with patch("app.routers.validation.run_rolling_validation") as mock_task:
        resp = client.post("/analytics/validation/rolling/9988.HK?models=not_a_real_model")

    assert resp.status_code == 400
    mock_task.apply_async.assert_not_called()


def test_rolling_validation_task_body_runs_end_to_end():
    """Calls the Celery task function directly (not through apply_async/a
    worker) with a small synthetic price series and a mocked fetch_df, so
    the task's own data-handling code (date parsing, series construction)
    actually executes under test -- the API-level tests above mock the
    task itself, which would miss a bug inside its body."""
    from app.tasks import run_rolling_validation

    dates = pd.bdate_range("2024-01-01", periods=200)
    prices = pd.DataFrame({
        "date": dates.strftime("%Y-%m-%d"),
        "close": 100 + np.cumsum(np.random.RandomState(0).normal(0, 1, len(dates))),
    })

    with patch("app.tasks.fetch_df", return_value=prices), \
         patch("app.tasks._save_result"), patch("app.tasks._publish"):
        result = run_rolling_validation.run(
            ticker="TEST.XX", models=["naive"], min_train=60,
            origin_step=30, horizon=10, window="expanding", period="1y",
        )

    assert "error" not in result
    assert result["ticker"] == "TEST.XX"
    assert result["summary"]["naive"]["n_folds"] > 0


def test_forecast_endpoint_contract_unchanged_by_naive_addition(client):
    """Guards against the one risk explicitly called out for this change:
    the existing single-ticker forecast endpoint's behavior/shape must not
    move. This doesn't re-run the full 41-test Jest suite (frontend), but
    confirms the backend contract itself is untouched: an empty result set
    still fails MIN_ROWS with the same pre-existing 422, not some new shape."""
    with patch("app.routers.models.fetch_df") as mock_fetch:
        mock_fetch.return_value = pd.DataFrame()  # 0 rows < MIN_ROWS -> 422
        resp = client.get("/analytics/models/forecast/9988.HK?model=arima")
    assert resp.status_code == 422
    assert "detail" in resp.json()
