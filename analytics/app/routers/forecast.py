from fastapi import APIRouter, HTTPException, Query
import pandas as pd
import numpy as np
import warnings
from statsmodels.tsa.arima.model import ARIMA
from app.db import fetch_df

warnings.filterwarnings("ignore")

router = APIRouter()

MIN_ROWS = 60

@router.get("/forecast/{ticker}")
def forecast(
    ticker: str,
    days:   int = Query(30, ge=7, le=90),
    period: str = Query("1y"),
):
    """
    ARIMA(1,1,1) forecast for a ticker.
    Returns historical closes + predicted closes with 95% confidence interval.
    """
    days_map = {"6m": 180, "1y": 365, "2y": 730}
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

    model  = ARIMA(series, order=(1, 1, 1))
    result = model.fit()

    forecast_res  = result.get_forecast(steps=days)
    forecast_mean = forecast_res.predicted_mean
    conf_int      = forecast_res.conf_int(alpha=0.05)

    history = [
        {"date": d.strftime("%Y-%m-%d"), "actual": round(float(v), 4)}
        for d, v in series.items()
    ]

    predictions = []
    for date, pred in forecast_mean.items():
        lower = conf_int.loc[date, "lower close"]
        upper = conf_int.loc[date, "upper close"]
        predictions.append({
            "date":      date.strftime("%Y-%m-%d"),
            "predicted": round(float(pred),  4),
            "lower":     round(float(lower), 4),
            "upper":     round(float(upper), 4),
        })

    return {
        "ticker":  ticker.upper(),
        "model":   "ARIMA(1,1,1)",
        "days":    days,
        "period":  period,
        "history":  history,
        "forecast": predictions,
    }
