import os

import redis

REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/0")

redis_client = redis.from_url(REDIS_URL, decode_responses=True)

FORECAST_CACHE_PREFIX = "forecast"


def forecast_cache_key(ticker: str, model: str, days: int, period: str, enriched: bool) -> str:
    return f"{FORECAST_CACHE_PREFIX}:{ticker}:{model}:{days}:{period}:{str(enriched).lower()}"
