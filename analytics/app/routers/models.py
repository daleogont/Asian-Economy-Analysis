import json
import logging
import warnings

import pandas as pd
from fastapi import APIRouter, HTTPException, Query, Response

from app.cache import forecast_cache_key, redis_client
from app.db import engine, fetch_df
from app.models.arima import ArimaModel
from app.models.ets import EtsModel
from app.models.lstm import LstmModel
from app.models.prophet import ProphetModel
from app.models.random_forest import RandomForestModel
from app.models.ridge import RidgeModel
from app.models.sarima import SarimaModel
from app.models.xgboost_model import XgboostModel

warnings.filterwarnings("ignore")

logger = logging.getLogger(__name__)

router = APIRouter()

MIN_ROWS = 60

MODEL_REGISTRY = {
    "arima":         ArimaModel,
    "ets":           EtsModel,
    "prophet":       ProphetModel,
    "sarima":        SarimaModel,
    "ridge":         RidgeModel,
    "random_forest": RandomForestModel,
    "xgboost":       XgboostModel,
    "lstm":          LstmModel,
}

# LSTM needs a longer minimum history than the other models: its 60-day
# lookback window alone eats most of MIN_ROWS, leaving too few sequences to
# train on.
MODEL_MIN_ROWS = {"lstm": 120}

# Only the lagged-feature (sklearn-style) models take fundamentals/macro
# features — ARIMA/ETS/SARIMA/Prophet fit on the raw series and have no
# feature vector to enrich, so `enriched=true` is silently a no-op for them.
# LSTM is also excluded: it consumes price history as a raw sequence, not a
# feature vector.
ENRICHABLE_MODELS = {"ridge", "random_forest", "xgboost"}

# Slow enough (RF/XGBoost's iterative multi-step predict loop; LSTM's
# training pass) to be worth caching — everything else responds in well
# under 200ms already, so caching would add complexity for no real benefit.
CACHEABLE_MODELS = {"random_forest", "xgboost", "lstm"}
CACHE_TTL_SECONDS = 86400  # 24h — invalidated early by the nightly delta fetch


@router.get("/models/forecast/{ticker}")
def forecast_with_model(
    response: Response,
    ticker: str,
    model:    str  = Query("arima"),
    days:     int  = Query(30, ge=7, le=90),
    period:   str  = Query("1y"),
    enriched: bool = Query(False),
):
    """
    Unified forecast endpoint — routes to the requested model and returns
    predictions plus CE performance metrics (latency, train time, memory,
    RMSE/MAE).

    `enriched=true` switches ridge/random_forest/xgboost from price-only
    lag features (Stage 2) to lag features + fundamentals + macro features
    (Stage 3). Ignored for arima/ets/sarima/prophet, which fit on the raw
    series and have no feature vector to enrich.

    random_forest/xgboost/lstm responses are cached in Redis for 24h (key:
    `forecast:{ticker}:{model}:{days}:{period}:{enriched}`), since they're
    meaningfully slower than every other model (RF/XGBoost's iterative
    multi-step predict loop; LSTM's training pass). `X-Cache: HIT`/`MISS`
    is set on cached responses; the nightly delta fetch flushes the whole
    `forecast:*` keyspace once new price data lands
    (`DELETE /internal/cache/invalidate`).
    """
    if model not in MODEL_REGISTRY:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown model '{model}'. Available: {sorted(MODEL_REGISTRY)}",
        )

    use_enriched = enriched and model in ENRICHABLE_MODELS
    cacheable = model in CACHEABLE_MODELS
    cache_key = forecast_cache_key(ticker.upper(), model, days, period, use_enriched) if cacheable else None

    if cacheable:
        try:
            cached = redis_client.get(cache_key)
        except Exception as exc:
            logger.warning("Redis GET failed for %s: %s", cache_key, exc)
            cached = None
        if cached is not None:
            response.headers["X-Cache"] = "HIT"
            return json.loads(cached)

    days_map = {"6m": 180, "1y": 365, "2y": 730, "5y": 1825}
    history_days = days_map.get(period, 365)

    df = fetch_df(
        """
        SELECT date, close
        FROM daily_prices
        WHERE ticker = :ticker
          AND date >= CURRENT_DATE - (:days || ' days')::interval
          AND close IS NOT NULL
        ORDER BY date ASC
        """,
        {"ticker": ticker.upper(), "days": history_days},
    )

    min_rows = MODEL_MIN_ROWS.get(model, MIN_ROWS)
    if len(df) < min_rows:
        raise HTTPException(
            status_code=422,
            detail=f"Not enough data for {ticker} — need {min_rows} rows, got {len(df)}",
        )

    df["date"]  = pd.to_datetime(df["date"])
    df["close"] = df["close"].astype(float)
    df = df.set_index("date").asfreq("B").ffill()  # business day freq, fill gaps

    series = df["close"]

    if use_enriched:
        country_df = fetch_df("SELECT country FROM companies WHERE ticker = :ticker", {"ticker": ticker.upper()})
        if country_df.empty:
            raise HTTPException(status_code=404, detail=f"Unknown ticker '{ticker}'")
        country = country_df.iloc[0]["country"]
        instance = MODEL_REGISTRY[model](
            use_enriched_features=True,
            ticker=ticker.upper(),
            country=country,
            db_conn=engine,
        )
    else:
        instance = MODEL_REGISTRY[model]()

    result = instance.run(series, steps=days)

    history = [
        {"date": d.strftime("%Y-%m-%d"), "actual": round(float(v), 4)}
        for d, v in series.items()
    ]

    forecast = result["forecast"]
    predictions = [
        {
            "date":      forecast["dates"][i],
            "predicted": round(float(forecast["mean"][i]), 4),
            "lower":     round(float(forecast["lower"][i]), 4),
            "upper":     round(float(forecast["upper"][i]), 4),
        }
        for i in range(len(forecast["dates"]))
    ]

    payload = {
        "ticker":   ticker.upper(),
        "model":    result["model_name"],
        "days":     days,
        "period":   period,
        "enriched": use_enriched,
        "history":  history,
        "forecast": predictions,
        "metrics":  result["metrics"],
    }

    if cacheable:
        try:
            redis_client.setex(cache_key, CACHE_TTL_SECONDS, json.dumps(payload))
        except Exception as exc:
            logger.warning("Redis SETEX failed for %s: %s", cache_key, exc)
        response.headers["X-Cache"] = "MISS"

    return payload
