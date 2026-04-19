import json
import logging
import os
from datetime import datetime, timezone

import redis
from sqlalchemy import text

from app.celery_app import celery_app
from app.db import engine, fetch_df

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
