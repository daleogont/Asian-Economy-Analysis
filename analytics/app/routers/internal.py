import logging

import yfinance as yf
from fastapi import APIRouter

from app.cache import FORECAST_CACHE_PREFIX, redis_client

logging.getLogger("yfinance").setLevel(logging.WARNING)

router = APIRouter()


@router.get("/fundamentals/{ticker}")
def fundamentals(ticker: str):
    """
    Internal-only endpoint (no auth) — fetches live fundamentals via yfinance.
    Exists so yfinance only needs to be installed in this container, not on
    whatever host runs scripts/collectFundamentals.js.
    """
    try:
        info = yf.Ticker(ticker).info or {}
    except Exception as e:
        return {
            "pe_ratio":       None,
            "eps":            None,
            "dividend_yield": None,
            "beta":           None,
            "market_cap":     None,
            "error":          str(e),
        }

    return {
        "pe_ratio":       info.get("trailingPE"),
        "eps":            info.get("trailingEps"),
        "dividend_yield": info.get("dividendYield"),
        "beta":           info.get("beta"),
        "market_cap":     info.get("marketCap"),
    }


@router.delete("/cache/invalidate")
def invalidate_cache():
    """
    Internal-only endpoint (no auth) — flushes every `forecast:*` key from
    Redis. Called by server/utils/deltaFetch.js at the end of the nightly
    delta fetch, so cached random_forest/xgboost forecasts don't outlive
    the price data they were computed from.
    """
    pattern = f"{FORECAST_CACHE_PREFIX}:*"
    deleted = 0
    cursor = 0
    while True:
        cursor, keys = redis_client.scan(cursor=cursor, match=pattern, count=500)
        if keys:
            deleted += redis_client.delete(*keys)
        if cursor == 0:
            break
    return {"deleted": deleted}
