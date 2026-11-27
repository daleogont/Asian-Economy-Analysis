"""
Shared DB access + ticker selection for the research/ benchmark pipeline.

Runs OUTSIDE Docker, against a dedicated venv (research/.venv) with
read-only access to the same Postgres instance the production stack uses
(exposed on localhost:5432 per docker-compose.yml). No production code is
imported or modified; model classes are imported directly from
analytics/app/models/ (added to sys.path below) purely to reuse their
exact fit/predict logic, not via the FastAPI app.
"""
import hashlib
import os
import random
import sys

import pandas as pd
import sqlalchemy as sa

HERE = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(HERE)

# Resolve the directory that contains the `app` package (analytics/app on
# the host; /app/app when this same code runs inside the python-api
# container via the research-only docker-compose.override.yml mount --
# WORKDIR /app there, with app/ baked in at build time, not a sibling
# "analytics" dir).
ANALYTICS_DIR = "/app" if os.path.exists("/app/app") else os.path.join(PROJECT_ROOT, "analytics")

# So `from app.models.arima import ArimaModel` etc. resolve to the
# production model classes without needing the FastAPI app or Docker.
if ANALYTICS_DIR not in sys.path:
    sys.path.insert(0, ANALYTICS_DIR)

DATABASE_URL = os.environ.get(
    "RESEARCH_DATABASE_URL",
    os.environ.get("DATABASE_URL", "postgresql://admin:secret@localhost:5432/asianmarkets"),
)
_engine = sa.create_engine(DATABASE_URL, poolclass=sa.pool.NullPool)


def fetch_df(query: str, params: dict | None = None) -> pd.DataFrame:
    with _engine.connect() as conn:
        return pd.read_sql(sa.text(query), conn, params=params)


# ---------------------------------------------------------------------------
# Ticker selection — identical algorithm to analytics/scripts/benchmark_paper.py
# (coverage window / MIN_ROWS / stratification / seed), so the research
# benchmark's sample is the same 30 tickers as the original 1-year paper
# benchmark, as long as DB coverage hasn't changed. Only PERIOD_DAYS and
# MIN_ROWS are exposed as params since the rolling benchmark needs a
# multi-year coverage window instead of the original 365-day one.
# ---------------------------------------------------------------------------
REFERENCE_TICKER = "9988.HK"
SEED = 42
TARGET_TICKERS = 30
BASE_PER_COUNTRY = 2

# The exact 30 tickers used by the existing one-year paper benchmark
# (analytics/scripts/benchmark_paper.py), read back from its committed
# output (research/legacy/benchmark_results.csv) rather than re-run live: re-running
# select_tickers() against the *current* DB returns ZERO tickers at the
# 365-day/240-row threshold, because daily_prices is ~2 months stale
# relative to wall-clock "today" and the 365-day window no longer has
# 240 trading days of coverage. Using the fixed list keeps the rolling
# benchmark's sample identical to (and thus comparable with) the
# existing one-year results, and sidesteps that staleness entirely.
# No South Korea or UAE tickers appear in this set (12 countries, 2-3
# tickers each) -- confirmed against `companies` on 2026-10-16.
PAPER_TICKERS = [
    "0001.HK", "0358.HK", "0388.HK", "0857.HK", "1101.TW", "1211.SR",
    "2082.SR", "2802.T", "3045.TW", "3988.HK", "5225.KL", "6012.KL",
    "7052.KL", "8801.T", "9433.T", "9988.HK", "APOLLOHOSP.NS", "BBRI.JK",
    "CC3.SI", "CRC.BK", "DCR.KA", "DLF.NS", "FPT.VN", "GOTO.JK",
    "HINDUNILVR.NS", "SCC.BK", "SE", "UBL.KA", "VHM.VN", "WIKA.JK",
]


def select_tickers(period_days: int, min_rows: int) -> pd.DataFrame:
    coverage = fetch_df(
        f"""
        SELECT dp.ticker, c.country, COUNT(*) AS row_count
        FROM daily_prices dp
        JOIN companies c ON c.ticker = dp.ticker
        WHERE dp.date >= CURRENT_DATE - INTERVAL '{period_days} days'
          AND dp.close IS NOT NULL
        GROUP BY dp.ticker, c.country
        HAVING COUNT(*) >= {min_rows}
        ORDER BY c.country, dp.ticker
        """
    )

    rng = random.Random(SEED)
    by_country = {
        country: list(group["ticker"])
        for country, group in coverage.groupby("country")
    }

    selected = []
    ref_country = None
    if REFERENCE_TICKER in coverage["ticker"].values:
        ref_country = coverage.loc[coverage["ticker"] == REFERENCE_TICKER, "country"].iloc[0]
        selected.append(REFERENCE_TICKER)
        by_country[ref_country].remove(REFERENCE_TICKER)

    countries = sorted(by_country.keys())
    for country in countries:
        already = 1 if country == ref_country else 0
        need = max(BASE_PER_COUNTRY - already, 0)
        pool = by_country[country]
        take = min(need, len(pool))
        picks = rng.sample(pool, take) if take > 0 else []
        selected.extend(picks)
        for p in picks:
            pool.remove(p)

    while len(selected) < TARGET_TICKERS:
        progressed = False
        for country in countries:
            if len(selected) >= TARGET_TICKERS:
                break
            pool = by_country[country]
            if pool:
                pick = rng.choice(pool)
                pool.remove(pick)
                selected.append(pick)
                progressed = True
        if not progressed:
            break

    ticker_to_country = dict(zip(coverage["ticker"], coverage["country"]))
    return pd.DataFrame(
        {"ticker": selected, "country": [ticker_to_country[t] for t in selected]}
    )


def fetch_series(ticker: str, period_days: int) -> pd.Series:
    """Business-day-frequency, forward-filled close price series — same
    convention as benchmark_paper.py's fetch_series, extended to an
    arbitrary multi-year window."""
    df = fetch_df(
        f"""
        SELECT date, close
        FROM daily_prices
        WHERE ticker = :ticker
          AND date >= CURRENT_DATE - INTERVAL '{period_days} days'
          AND close IS NOT NULL
        ORDER BY date ASC
        """,
        {"ticker": ticker},
    )
    df["date"] = pd.to_datetime(df["date"])
    df["close"] = df["close"].astype(float)
    df = df.set_index("date").asfreq("B").ffill()
    return df["close"]


def sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()
