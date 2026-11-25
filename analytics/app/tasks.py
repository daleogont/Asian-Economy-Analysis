import json
import logging
import os
from datetime import datetime, timezone

import pandas as pd
import redis
from sqlalchemy import text

from app.batch_benchmark import friedman_wilcoxon_holm, run_one, summarize
from app.celery_app import celery_app
from app.db import engine, fetch_df
from app.validation import run_rolling_origin

logger = logging.getLogger(__name__)

REDIS_URL      = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
PUBSUB_CHANNEL = "task_events"


def _get_redis():
    return redis.from_url(REDIS_URL, decode_responses=True)


def _publish(task_id: str, operation: str, status: str, result: dict) -> None:
    try:
        r = _get_redis()
        r.publish(PUBSUB_CHANNEL, json.dumps({
            "task_id":      task_id,
            "operation":    operation,
            "status":       status,
            "result":       result,
            "completed_at": datetime.now(timezone.utc).isoformat(),
        }))
        r.close()
    except Exception as exc:
        logger.error("Redis publish failed: %s", exc)


def _save_result(
    task_id: str, operation: str, input_data: dict, result: dict, status: str
) -> None:
    try:
        with engine.connect() as conn:
            conn.execute(text("""
                INSERT INTO task_results
                    (task_id, operation, input_data, result, status, completed_at)
                VALUES
                    (:task_id, :operation, :input_data::jsonb, :result::jsonb, :status, :completed_at)
                ON CONFLICT (task_id) DO UPDATE SET
                    result       = EXCLUDED.result,
                    status       = EXCLUDED.status,
                    completed_at = EXCLUDED.completed_at
            """), {
                "task_id":      task_id,
                "operation":    operation,
                "input_data":   json.dumps(input_data),
                "result":       json.dumps(result),
                "status":       status,
                "completed_at": datetime.now(timezone.utc),
            })
            conn.commit()
    except Exception as exc:
        logger.error("DB save failed: %s", exc)


@celery_app.task(bind=True, name="app.tasks.send_email_notification")
def send_email_notification(self, users: list, top_movers: list | None = None):
    task_id = self.request.id
    logger.info("[EMAIL] task_id=%s  users=%d", task_id, len(users))

    if not top_movers:
        try:
            df = fetch_df("""
                WITH latest AS (
                    SELECT DISTINCT ON (ticker) ticker, close
                    FROM daily_prices ORDER BY ticker, date DESC
                ),
                week_ago AS (
                    SELECT DISTINCT ON (ticker) ticker, close AS week_close
                    FROM daily_prices
                    WHERE date <= CURRENT_DATE - INTERVAL '5 days'
                    ORDER BY ticker, date DESC
                )
                SELECT c.name, c.ticker, c.country,
                    ROUND(((l.close - wa.week_close) / wa.week_close * 100)::numeric, 2)
                        AS weekly_return
                FROM companies c
                JOIN latest   l  USING (ticker)
                LEFT JOIN week_ago wa USING (ticker)
                WHERE wa.week_close > 0
                ORDER BY weekly_return DESC
                LIMIT 5
            """)
            top_movers = df.to_dict(orient="records") if not df.empty else []
        except Exception as exc:
            logger.warning("[EMAIL] Could not fetch top movers: %s", exc)
            top_movers = []

    sent = []
    for user in users:
        logger.info("[EMAIL] Simulating send → %s  (top_movers=%d)", user, len(top_movers))
        sent.append({"user": user, "status": "sent"})

    result = {
        "users_notified":      len(users),
        "top_movers_included": len(top_movers),
        "top_movers":          top_movers,
        "emails":              sent,
    }
    input_data = {"users": users, "top_movers_count": len(top_movers)}
    _save_result(task_id, "send_email_notification", input_data, result, "success")
    _publish(task_id, "send_email_notification", "success", result)
    return result


@celery_app.task(bind=True, name="app.tasks.run_market_analysis")
def run_market_analysis(self):
    task_id = self.request.id
    logger.info("[ANALYSIS] task_id=%s  starting", task_id)

    df = fetch_df("""
        WITH latest AS (
            SELECT DISTINCT ON (ticker) ticker, close
            FROM daily_prices ORDER BY ticker, date DESC
        ),
        week_ago AS (
            SELECT DISTINCT ON (ticker) ticker, close AS week_close
            FROM daily_prices
            WHERE date <= CURRENT_DATE - INTERVAL '5 days'
            ORDER BY ticker, date DESC
        )
        SELECT
            c.ticker, c.country, c.sector,
            l.close,
            CASE WHEN wa.week_close > 0
                THEN ROUND(((l.close - wa.week_close) / wa.week_close * 100)::numeric, 4)
                ELSE NULL
            END AS weekly_return
        FROM companies c
        JOIN latest   l  USING (ticker)
        LEFT JOIN week_ago wa USING (ticker)
    """)

    country_stats: dict = {}
    for country, grp in df.groupby("country"):
        prices  = grp["close"].dropna().astype(float)
        returns = grp["weekly_return"].dropna().astype(float)
        country_stats[str(country)] = {
            "company_count":       int(len(grp)),
            "avg_price":           round(float(prices.mean()),  4) if len(prices)  > 0 else None,
            "avg_weekly_return":   round(float(returns.mean()), 4) if len(returns) > 0 else None,
            "best_weekly_return":  round(float(returns.max()),  4) if len(returns) > 0 else None,
            "worst_weekly_return": round(float(returns.min()),  4) if len(returns) > 0 else None,
        }

    logger.info("[ANALYSIS] done — %d countries", len(country_stats))
    result = {"countries_analyzed": len(country_stats), "country_stats": country_stats}
    _save_result(task_id, "run_market_analysis", {}, result, "success")
    _publish(task_id, "run_market_analysis", "success", result)
    return result


_PERIOD_DAYS = {"6m": 180, "1y": 365, "2y": 730, "5y": 1825}


@celery_app.task(bind=True, name="app.tasks.run_rolling_validation")
def run_rolling_validation(
    self,
    ticker: str,
    models: list,
    min_train: int,
    origin_step: int,
    horizon: int,
    window: str,
    period: str,
):
    """
    Rolling-origin cross-validation for one ticker — always run via Celery
    (never inline on the request path) since it re-fits every model at
    every origin. Mirrors research/rolling_benchmark.py's methodology.
    """
    task_id = self.request.id
    input_data = {
        "ticker": ticker, "models": models, "min_train": min_train,
        "origin_step": origin_step, "horizon": horizon, "window": window, "period": period,
    }
    logger.info("[ROLLING] task_id=%s  %s", task_id, input_data)

    days = _PERIOD_DAYS.get(period, 1825)
    df = fetch_df(
        """
        SELECT date, close
        FROM daily_prices
        WHERE ticker = :ticker
          AND date >= CURRENT_DATE - (:days || ' days')::interval
          AND close IS NOT NULL
        ORDER BY date ASC
        """,
        {"ticker": ticker.upper(), "days": days},
    )
    if df.empty:
        result = {"error": f"No price data for ticker '{ticker}'"}
        _save_result(task_id, "run_rolling_validation", input_data, result, "failure")
        _publish(task_id, "run_rolling_validation", "failure", result)
        return result

    df["date"] = pd.to_datetime(df["date"])
    df["close"] = df["close"].astype(float)
    series = df.set_index("date")["close"].asfreq("B").ffill()

    try:
        result = run_rolling_origin(
            series, models,
            min_train=min_train, origin_step=origin_step, horizon=horizon, window=window,
        )
        result["ticker"] = ticker.upper()
        status = "success"
    except Exception as exc:
        result = {"error": str(exc)}
        status = "failure"

    logger.info("[ROLLING] task_id=%s  status=%s", task_id, status)
    _save_result(task_id, "run_rolling_validation", input_data, result, status)
    _publish(task_id, "run_rolling_validation", status, result)
    return result


@celery_app.task(bind=True, name="app.tasks.run_batch_benchmark", soft_time_limit=1500, time_limit=1800)
def run_batch_benchmark(self, tickers: list, models: list, horizon: int, period: str, period_days: int, stats: bool):
    """
    Runs every (ticker, model) pair through the single-holdout benchmark
    protocol already used elsewhere (BaseForecastModel.run()). Reports
    progress via Celery's own state so the frontend can show a bar instead
    of a spinner. Bounded by a per-task time limit (soft 25min/hard 30min)
    since a large ticker x model grid can otherwise run indefinitely.
    """
    task_id = self.request.id
    input_data = {"tickers": tickers, "models": models, "horizon": horizon, "period": period, "stats": stats}
    logger.info("[BATCH] task_id=%s  n_tickers=%d  n_models=%d", task_id, len(tickers), len(models))

    rows = []
    total = len(tickers) * len(models)
    done = 0

    for ticker in tickers:
        df = fetch_df(
            """
            SELECT date, close
            FROM daily_prices
            WHERE ticker = :ticker
              AND date >= CURRENT_DATE - (:days || ' days')::interval
              AND close IS NOT NULL
            ORDER BY date ASC
            """,
            {"ticker": ticker, "days": period_days},
        )
        if df.empty:
            for model_key in models:
                rows.append({
                    "ticker": ticker, "model": model_key, "error": "No price data",
                    "rmse": None, "mae": None, "rmse_pct": None,
                    "inference_latency_ms": None, "train_time_s": None, "memory_mb": None,
                })
                done += 1
            continue

        df["date"] = pd.to_datetime(df["date"])
        df["close"] = df["close"].astype(float)
        series = df.set_index("date")["close"].asfreq("B").ffill()

        for model_key in models:
            rows.append(run_one(ticker, model_key, series, horizon))
            done += 1
            self.update_state(state="PROGRESS", meta={"done": done, "total": total})

    agg = summarize(rows, models, tickers)
    result = {
        "tickers": tickers, "models": models, "horizon": horizon, "period": period,
        "rows": rows, **agg,
    }
    if stats:
        result["stats"] = friedman_wilcoxon_holm(rows, models, tickers)

    logger.info("[BATCH] task_id=%s  done=%d/%d", task_id, done, total)
    _save_result(task_id, "run_batch_benchmark", input_data, result, "success")
    _publish(task_id, "run_batch_benchmark", "success", result)
    return result
