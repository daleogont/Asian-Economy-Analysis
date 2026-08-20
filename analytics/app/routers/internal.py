import logging

import yfinance as yf
from fastapi import APIRouter

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
