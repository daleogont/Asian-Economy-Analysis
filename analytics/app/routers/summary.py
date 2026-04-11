from fastapi import APIRouter, HTTPException, Query
from typing import Optional
import numpy as np
from app.db import fetch_df

router = APIRouter()

@router.get("/summary")
def summary(
    country: Optional[str] = Query(None),
    sector:  Optional[str] = Query(None),
):
    """
    Descriptive statistics for a group of companies.
    Filter by country and/or sector.
    Returns mean, median, std, min, max for close price and weekly return.
    """
    where = []
    params = {}
    if country:
        where.append("c.country = :country")
        params["country"] = country
    if sector:
        where.append("c.sector = :sector")
        params["sector"] = sector

    where_clause = ("WHERE " + " AND ".join(where)) if where else ""

    df = fetch_df(f"""
        WITH latest AS (
            SELECT DISTINCT ON (ticker) ticker, close
            FROM daily_prices
            ORDER BY ticker, date DESC
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
        JOIN latest  l  USING (ticker)
        LEFT JOIN week_ago wa USING (ticker)
        {where_clause}
    """, params)

    if df.empty:
        raise HTTPException(status_code=404, detail="No data found for given filters")

    prices  = df["close"].dropna().astype(float)
    returns = df["weekly_return"].dropna().astype(float)

    def stats(series):
        return {
            "mean":   round(float(np.mean(series)),   4),
            "median": round(float(np.median(series)), 4),
            "std":    round(float(np.std(series)),    4),
            "min":    round(float(np.min(series)),    4),
            "max":    round(float(np.max(series)),    4),
            "count":  int(len(series)),
        }

    return {
        "filters":       {"country": country, "sector": sector},
        "companyCount":  len(df),
        "price":         stats(prices)  if len(prices)  > 0 else None,
        "weeklyReturn":  stats(returns) if len(returns) > 0 else None,
    }
