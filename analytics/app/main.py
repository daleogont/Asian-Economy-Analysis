import asyncio
import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path

import pandas as pd
import redis.asyncio as aioredis
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text

from app.db import engine, fetch_df
from app.models.lstm import LstmModel
from app.routers import analytics_ml, forecast, internal, models, rolling, summary, validation
from app.routers import tasks as tasks_router

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

REDIS_URL      = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
PUBSUB_CHANNEL = "task_events"


class _ConnectionManager:
    def __init__(self):
        self._connections: list[WebSocket] = []

    async def connect(self, ws: WebSocket) -> None:
        await ws.accept()
        self._connections.append(ws)

    def disconnect(self, ws: WebSocket) -> None:
        if ws in self._connections:
            self._connections.remove(ws)

    async def broadcast(self, message: str) -> None:
        dead = []
        for ws in list(self._connections):
            try:
                await ws.send_text(message)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.disconnect(ws)


manager = _ConnectionManager()


async def _redis_listener() -> None:
    while True:
        try:
            r = aioredis.from_url(REDIS_URL)
            pubsub = r.pubsub()
            await pubsub.subscribe(PUBSUB_CHANNEL)
            logger.info("Redis pub/sub listener active on channel '%s'", PUBSUB_CHANNEL)
            async for msg in pubsub.listen():
                if msg["type"] == "message":
                    data = msg["data"]
                    if isinstance(data, bytes):
                        data = data.decode()
                    await manager.broadcast(data)
        except asyncio.CancelledError:
            return
        except Exception as exc:
            logger.error("Redis listener error: %s — retrying in 5 s", exc)
            await asyncio.sleep(5)


def _ensure_task_results_table() -> None:
    with engine.connect() as conn:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS task_results (
                task_id      VARCHAR     PRIMARY KEY,
                operation    VARCHAR     NOT NULL,
                input_data   JSONB,
                result       JSONB,
                status       VARCHAR     NOT NULL,
                completed_at TIMESTAMPTZ,
                created_at   TIMESTAMPTZ DEFAULT NOW()
            )
        """))
        conn.commit()


def _fit_lstm_warmup() -> None:
    """Blocking work for warmup_lstm() — run off the event loop via asyncio.to_thread."""
    df = fetch_df(
        """
        SELECT date, close
        FROM daily_prices
        WHERE ticker = :ticker
          AND date >= CURRENT_DATE - INTERVAL '365 days'
          AND close IS NOT NULL
        ORDER BY date ASC
        """,
        {"ticker": "9988.HK"},
    )
    df["date"]  = pd.to_datetime(df["date"])
    df["close"] = df["close"].astype(float)
    df = df.set_index("date").asfreq("B").ffill()

    LstmModel().fit(df["close"])


async def warmup_lstm() -> None:
    """
    Fire-and-forget: pays PyTorch's one-time CPU-backend warm-up cost
    (observed 60-150s, landing unpredictably in either training or
    inference) at container startup instead of on a user's first real
    LSTM request. `fit()` is blocking/CPU-bound, so it runs in a thread
    via asyncio.to_thread — otherwise it would freeze the event loop
    (including /health) for the whole warm-up window. Never allowed to
    affect startup or crash the app if it fails.
    """
    await asyncio.sleep(10)  # let the container finish settling first
    try:
        await asyncio.to_thread(_fit_lstm_warmup)
        logger.info("LSTM warm-up complete")
    except Exception as exc:
        logger.warning("LSTM warm-up failed: %s", exc)


@asynccontextmanager
async def lifespan(app: FastAPI):
    _ensure_task_results_table()
    listener = asyncio.create_task(_redis_listener())
    warmup   = asyncio.create_task(warmup_lstm())
    yield
    listener.cancel()
    warmup.cancel()
    for task in (listener, warmup):
        try:
            await task
        except asyncio.CancelledError:
            pass


app = FastAPI(title="Asian Capital Markets Analytics API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Cache"],
)

app.mount("/static", StaticFiles(directory="app/static"), name="static")

app.include_router(summary.router,       prefix="/analytics", tags=["Analytics"])
app.include_router(rolling.router,       prefix="/analytics", tags=["Analytics"])
app.include_router(forecast.router,      prefix="/analytics", tags=["Analytics"])
app.include_router(models.router,        prefix="/analytics", tags=["Analytics"])
app.include_router(analytics_ml.router,  prefix="/analytics", tags=["Analytics"])
app.include_router(validation.router,    prefix="/analytics", tags=["Analytics"])
app.include_router(internal.router,      prefix="/internal",  tags=["Internal"])
app.include_router(tasks_router.router,  prefix="/tasks",     tags=["Tasks"])


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/admin", include_in_schema=False)
def admin():
    return FileResponse("app/static/admin.html")


@app.websocket("/ws/tasks")
async def ws_tasks(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)
