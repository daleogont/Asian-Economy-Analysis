import logging
import os

import numpy as np
import pandas as pd
import requests
from sqlalchemy import text

logger = logging.getLogger(__name__)

LAGS = (1, 2, 3, 5, 10, 20)

NODE_API_URL = os.environ.get("NODE_API_URL", "http://node-api:4000")

# The Node /api/macros endpoint hits the World Bank API live with no
# caching of its own, and only supports ~10 of our 14 countries. Cache per
# country for the life of this process so repeated fits within one forecast
# request (holdout split + final fit) — and across requests for the same
# country — don't redo that network round trip.
_macro_cache: dict = {}


def _fetch_macro(country: str) -> dict:
    if country in _macro_cache:
        return _macro_cache[country]
    try:
        resp = requests.get(f"{NODE_API_URL}/api/macros", params={"country": country}, timeout=10)
        resp.raise_for_status()
        data = resp.json()
    except Exception as exc:
        logger.warning("macro fetch failed for %s: %s", country, exc)
        data = {}
    _macro_cache[country] = data
    return data


def _fetch_fundamentals(ticker: str, db_conn) -> dict:
    with db_conn.connect() as conn:
        row = conn.execute(
            text(
                "SELECT pe_ratio, eps, dividend_yield, beta, market_cap "
                "FROM fundamentals WHERE ticker = :ticker"
            ),
            {"ticker": ticker},
        ).mappings().first()
    return dict(row) if row else {}


def _median(db_conn, column: str, fallback: float) -> float:
    with db_conn.connect() as conn:
        value = conn.execute(
            text(
                f"SELECT percentile_cont(0.5) WITHIN GROUP (ORDER BY {column}) "
                f"FROM fundamentals WHERE {column} IS NOT NULL"
            )
        ).scalar()
    return float(value) if value is not None else fallback


def build_features(prices: pd.Series, ticker: str, country: str, db_conn) -> pd.DataFrame:
    """
    Enriched feature matrix for one ticker: lagged close prices + time index
    (same as the price-only Stage 2 features) plus static fundamentals and
    macro features (Stage 3). Fundamentals/macro don't vary day-to-day, so
    they're broadcast as constant columns across every row.

    Returns a DataFrame aligned to `prices`' index, including the target
    column 'y'. The warmup rows (where lag features aren't available yet)
    still have NaNs — the caller drops those.

    NULL-filling:
      - beta          -> 1.0 (market-neutral default)
      - pe_ratio       -> median of all non-null pe_ratio in `fundamentals`
      - market_cap     -> median of all non-null market_cap, then log-transformed
      - dividend_yield -> 0.0
      - gdp            -> log-transformed; 0.0 if unavailable (unsupported
                           country, or the live World Bank call failed)
      - unemployment   -> 0.0 if unavailable
    """
    df = pd.DataFrame({"y": prices.to_numpy()}, index=prices.index)
    for lag in LAGS:
        df[f"lag_{lag}"] = prices.shift(lag).to_numpy()
    df["time_idx"] = np.arange(len(prices))

    fundamentals = _fetch_fundamentals(ticker, db_conn)

    beta = fundamentals.get("beta")
    df["beta"] = float(beta) if beta is not None else 1.0

    pe_ratio = fundamentals.get("pe_ratio")
    df["pe_ratio"] = float(pe_ratio) if pe_ratio is not None else _median(db_conn, "pe_ratio", 15.0)

    market_cap = fundamentals.get("market_cap")
    market_cap = float(market_cap) if market_cap is not None else _median(db_conn, "market_cap", 1e9)
    df["log_market_cap"] = np.log(max(market_cap, 1.0))

    dividend_yield = fundamentals.get("dividend_yield")
    df["dividend_yield"] = float(dividend_yield) if dividend_yield is not None else 0.0

    macro = _fetch_macro(country)
    gdp = macro.get("gdp")
    df["log_gdp"] = np.log(gdp) if gdp and gdp > 0 else 0.0

    unemployment = macro.get("unemployment")
    df["unemployment"] = float(unemployment) if unemployment is not None else 0.0

    return df
