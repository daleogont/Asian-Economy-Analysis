import warnings

import pandas as pd
from fastapi import APIRouter, HTTPException, Query

from app.db import engine, fetch_df
from app.models.arima import ArimaModel
from app.models.ets import EtsModel
from app.models.prophet import ProphetModel
from app.models.random_forest import RandomForestModel
from app.models.ridge import RidgeModel
from app.models.sarima import SarimaModel
from app.models.xgboost_model import XgboostModel

warnings.filterwarnings("ignore")

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
}

# Only the lagged-feature (sklearn-style) models take fundamentals/macro
# features — ARIMA/ETS/SARIMA/Prophet fit on the raw series and have no
# feature vector to enrich, so `enriched=true` is silently a no-op for them.
ENRICHABLE_MODELS = {"ridge", "random_forest", "xgboost"}


@router.get("/models/forecast/{ticker}")
def forecast_with_model(
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
    """
    if model not in MODEL_REGISTRY:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown model '{model}'. Available: {sorted(MODEL_REGISTRY)}",
        )

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

    if len(df) < MIN_ROWS:
        raise HTTPException(
            status_code=422,
            detail=f"Not enough data for {ticker} — need {MIN_ROWS} rows, got {len(df)}",
        )

    df["date"]  = pd.to_datetime(df["date"])
    df["close"] = df["close"].astype(float)
    df = df.set_index("date").asfreq("B").ffill()  # business day freq, fill gaps

    series = df["close"]

    use_enriched = enriched and model in ENRICHABLE_MODELS
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

    return {
        "ticker":   ticker.upper(),
        "model":    result["model_name"],
        "days":     days,
        "period":   period,
        "enriched": use_enriched,
        "history":  history,
        "forecast": predictions,
        "metrics":  result["metrics"],
    }
