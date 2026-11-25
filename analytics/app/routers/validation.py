from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query

from app.tasks import run_rolling_validation
from app.validation import HORIZON_DEFAULT, MIN_TRAIN_DEFAULT, STEP_DEFAULT, resolve_models

router = APIRouter()


@router.post("/validation/rolling/{ticker}")
def start_rolling_validation(
    ticker: str,
    models: Optional[List[str]] = Query(
        None, description="Defaults to the cheap set (arima/ets/sarima/prophet/ridge/naive)."
    ),
    min_train: int = Query(MIN_TRAIN_DEFAULT, ge=60, description="Business days in the first training window."),
    origin_step: int = Query(STEP_DEFAULT, ge=1, le=365),
    horizon: int = Query(HORIZON_DEFAULT, ge=7, le=90),
    window: str = Query("expanding", pattern="^(expanding|sliding)$"),
    period: str = Query("5y", description="History window to fetch: 6m|1y|2y|5y"),
    allow_heavy: bool = Query(False, description="Required to include random_forest/xgboost/lstm."),
):
    """
    Rolling-origin cross-validation for one ticker. Always asynchronous —
    fitting several models at dozens of origins is too expensive for the
    request/response cycle, unlike the single-holdout
    `/analytics/models/forecast/{ticker}` endpoint, whose behavior this
    does not touch. Poll `GET /tasks/status/{task_id}` for progress/result.
    """
    try:
        resolved_models = resolve_models(models, allow_heavy)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    task = run_rolling_validation.apply_async(args=[
        ticker.upper(), resolved_models, min_train, origin_step, horizon, window, period,
    ])
    return {
        "task_id": task.id,
        "status": "queued",
        "queue": "longrunning_queue",
        "ticker": ticker.upper(),
        "models": resolved_models,
    }
