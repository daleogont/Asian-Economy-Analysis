from typing import List, Optional

from celery.result import AsyncResult
from fastapi import APIRouter, Query
from pydantic import BaseModel

from app.celery_app import celery_app
from app.db import fetch_df
from app.tasks import run_market_analysis, send_email_notification

router = APIRouter()


class EmailRequest(BaseModel):
    users: List[str] = ["admin@example.com", "analyst@example.com", "trader@example.com"]
    top_movers: Optional[List[dict]] = None


@router.post("/email")
def trigger_email(req: EmailRequest):
    task = send_email_notification.apply_async(args=[req.users, req.top_movers or []])
    return {"task_id": task.id, "status": "queued", "queue": "email_queue"}


@router.post("/analysis")
def trigger_analysis():
    task = run_market_analysis.apply_async()
    return {"task_id": task.id, "status": "queued", "queue": "longrunning_queue"}


@router.get("/status/{task_id}")
def get_status(task_id: str):
    res = AsyncResult(task_id, app=celery_app)
    return {
        "task_id": task_id,
        "status":  res.status,
        "result":  res.result if res.ready() else None,
    }


@router.get("/history")
def get_history(limit: int = Query(50, ge=1, le=500)):
    try:
        df = fetch_df(
            "SELECT task_id, operation, input_data, result, status, completed_at "
            "FROM task_results ORDER BY completed_at DESC NULLS LAST LIMIT :limit",
            {"limit": limit},
        )
        if df.empty:
            return []
        df["completed_at"] = df["completed_at"].astype(str)
        return df.to_dict(orient="records")
    except Exception:
        return []
