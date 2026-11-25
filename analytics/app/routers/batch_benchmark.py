from typing import List, Optional

from celery.result import AsyncResult
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.batch_benchmark import DEFAULT_MODELS
from app.celery_app import celery_app
from app.db import fetch_df
from app.routers.models import MODEL_REGISTRY
from app.tasks import run_batch_benchmark

router = APIRouter()

_PERIOD_DAYS = {"6m": 180, "1y": 365, "2y": 730, "5y": 1825}


class BatchBenchmarkRequest(BaseModel):
    tickers: Optional[List[str]] = None
    country: Optional[str] = None
    sector: Optional[str] = None
    models: Optional[List[str]] = None
    horizon: int = 30
    period: str = "1y"
    stats: bool = False


def _resolve_tickers(req: BatchBenchmarkRequest) -> List[str]:
    if req.tickers:
        return [t.upper() for t in req.tickers]

    if not req.country and not req.sector:
        raise HTTPException(status_code=400, detail="Provide `tickers`, or `country`/`sector` to select them.")

    conditions, params = [], {}
    if req.country:
        conditions.append("country = :country")
        params["country"] = req.country
    if req.sector:
        conditions.append("sector = :sector")
        params["sector"] = req.sector

    df = fetch_df(f"SELECT ticker FROM companies WHERE {' AND '.join(conditions)}", params)
    if df.empty:
        raise HTTPException(status_code=404, detail="No companies matched the given country/sector.")
    return df["ticker"].tolist()


@router.post("/batch-benchmark")
def start_batch_benchmark(req: BatchBenchmarkRequest):
    """
    Benchmarks a ticker set x model set with the same single-holdout
    protocol as /analytics/models/forecast, one Celery task for the whole
    batch (never inline — this is routinely dozens-to-hundreds of
    fit+predict calls). LSTM is excluded from the default model set; pass
    it explicitly in `models` to include it.
    """
    tickers = _resolve_tickers(req)
    models = [m.lower() for m in req.models] if req.models else list(DEFAULT_MODELS)

    unknown = [m for m in models if m not in MODEL_REGISTRY]
    if unknown:
        raise HTTPException(status_code=400, detail=f"Unknown model(s): {unknown}. Available: {sorted(MODEL_REGISTRY)}")

    period_days = _PERIOD_DAYS.get(req.period, 365)
    task = run_batch_benchmark.apply_async(args=[
        tickers, models, req.horizon, req.period, period_days, req.stats,
    ])
    return {
        "task_id": task.id,
        "status": "queued",
        "queue": "longrunning_queue",
        "tickers": tickers,
        "models": models,
    }


@router.get("/batch-benchmark/{task_id}/status")
def batch_benchmark_status(task_id: str):
    """Progress-aware status: {done, total} while running, via Celery's
    own PROGRESS state — distinct from the generic /tasks/status, which
    only reports PENDING/STARTED/SUCCESS/FAILURE with no progress detail."""
    res = AsyncResult(task_id, app=celery_app)
    progress = res.info if res.state == "PROGRESS" and isinstance(res.info, dict) else None
    return {"task_id": task_id, "status": res.status, "progress": progress}


@router.get("/batch-benchmark/{task_id}/results")
def batch_benchmark_results(task_id: str):
    res = AsyncResult(task_id, app=celery_app)
    if not res.ready():
        return {"task_id": task_id, "status": res.status, "result": None}
    if res.failed():
        raise HTTPException(status_code=500, detail=f"Batch benchmark task failed: {res.result}")
    return {"task_id": task_id, "status": res.status, "result": res.result}
