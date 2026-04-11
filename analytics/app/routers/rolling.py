from fastapi import APIRouter, HTTPException, Query
import pandas as pd
from app.db import fetch_df

router = APIRouter()

@router.get("/rolling/{ticker}")
def rolling(
    ticker: str,
    window: int  = Query(30, ge=2, le=200),
    period: str  = Query("1y"),
):
    """
    Returns daily close prices + rolling mean for a ticker.
    period: 3m | 6m | 1y | 2y
    window: rolling average window in trading days
    """
    days_map = {"3m": 90, "6m": 180, "1y": 365, "2y": 730}
    days = days_map.get(period, 365)

    df = fetch_df(
        """
        SELECT date, close
        FROM daily_prices
        WHERE ticker = :ticker
          AND date >= CURRENT_DATE - (:days || ' days')::interval
        ORDER BY date ASC
        """,
        {"ticker": ticker.upper(), "days": days},
    )

    if df.empty:
        raise HTTPException(status_code=404, detail=f"No data for {ticker}")

    df["date"]   = pd.to_datetime(df["date"]).dt.strftime("%Y-%m-%d")
    df["close"]  = df["close"].astype(float)
    df[f"ma{window}"] = df["close"].rolling(window=window, min_periods=1).mean().round(4)

    return {
        "ticker": ticker.upper(),
        "window": window,
        "period": period,
        "data":   df.to_dict(orient="records"),
    }
