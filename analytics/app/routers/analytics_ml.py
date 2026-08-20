import time
import warnings
from collections import Counter
from itertools import combinations

import numpy as np
import pandas as pd
from fastapi import APIRouter, HTTPException, Query
from sklearn.cluster import KMeans
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler

from app.db import fetch_df

warnings.filterwarnings("ignore")

router = APIRouter()

PERIOD_DAYS = {"3m": 90, "6m": 180, "1y": 365, "2y": 730, "5y": 1825}


def _period_to_days(period: str) -> int:
    return PERIOD_DAYS.get(period, 365)


def _wide_prices(df: pd.DataFrame) -> pd.DataFrame:
    """Pivot (ticker, date, close) rows into a date x ticker close-price matrix."""
    df = df.copy()
    df["date"] = pd.to_datetime(df["date"])
    return df.pivot_table(index="date", columns="ticker", values="close", aggfunc="last")


@router.get("/correlation")
def correlation(
    country: str = Query(...),
    period:  str = Query("1y"),
):
    """
    Pairwise Pearson correlation of daily returns across every company in a
    country. Correlation is computed on returns (not raw price levels) to
    avoid spurious trend-driven correlation between unrelated stocks.
    """
    days = _period_to_days(period)

    df = fetch_df(
        """
        SELECT dp.ticker, dp.date, dp.close
        FROM daily_prices dp
        JOIN companies c ON dp.ticker = c.ticker
        WHERE c.country = :country
          AND dp.date >= CURRENT_DATE - (:days || ' days')::interval
          AND dp.close IS NOT NULL
        ORDER BY dp.date ASC
        """,
        {"country": country, "days": days},
    )

    if df.empty:
        raise HTTPException(status_code=404, detail=f"No price data for country '{country}'")

    start = time.perf_counter()

    wide = _wide_prices(df)
    tickers = sorted(wide.columns)
    if len(tickers) < 2:
        raise HTTPException(
            status_code=422,
            detail=f"Need at least 2 tickers with data in '{country}', found {len(tickers)}",
        )

    returns = wide.pct_change().dropna(how="all")
    corr_matrix = returns.corr(method="pearson")

    pairs = []
    for a, b in combinations(tickers, 2):
        val = corr_matrix.loc[a, b]
        if pd.isna(val):
            continue
        pairs.append({"ticker_a": a, "ticker_b": b, "correlation": round(float(val), 4)})

    top_correlated   = sorted(pairs, key=lambda p: p["correlation"], reverse=True)[:10]
    least_correlated = sorted(pairs, key=lambda p: p["correlation"])[:10]

    computation_time_ms = round((time.perf_counter() - start) * 1000, 3)

    return {
        "country":            country,
        "period":             period,
        "tickers":            tickers,
        "pairCount":          len(pairs),
        "pairs":              pairs,
        "topCorrelated":      top_correlated,
        "leastCorrelated":    least_correlated,
        "computation_time_ms": computation_time_ms,
    }


@router.get("/anomalies")
def anomalies(
    country: str = Query(...),
    period:  str = Query("1y"),
):
    """
    Flags anomalous companies within a country by two independent methods:
      - IsolationForest over each company's weekly-return time series
      - a simple Z-score on each company's latest weekly return vs its own
        history (|z| > 2)
    """
    days = _period_to_days(period)

    df = fetch_df(
        """
        SELECT dp.ticker, dp.date, dp.close
        FROM daily_prices dp
        JOIN companies c ON dp.ticker = c.ticker
        WHERE c.country = :country
          AND dp.date >= CURRENT_DATE - (:days || ' days')::interval
          AND dp.close IS NOT NULL
        ORDER BY dp.date ASC
        """,
        {"country": country, "days": days},
    )

    if df.empty:
        raise HTTPException(status_code=404, detail=f"No price data for country '{country}'")

    start = time.perf_counter()

    wide = _wide_prices(df)
    weekly_returns = wide.resample("W-FRI").last().pct_change().dropna(how="all")

    tickers = [t for t in weekly_returns.columns if weekly_returns[t].notna().sum() >= 3]
    if len(tickers) < 2:
        raise HTTPException(
            status_code=422,
            detail=f"Need at least 2 tickers with enough weekly history in '{country}', found {len(tickers)}",
        )

    # rows = tickers, cols = weeks — IsolationForest sees each company's
    # weekly-return pattern as a feature vector to compare against peers.
    matrix = weekly_returns[tickers].T.fillna(0.0)
    X = matrix.to_numpy()

    clf = IsolationForest(contamination=0.05, random_state=42)
    labels = clf.fit_predict(X)        # -1 == anomaly
    scores = -clf.decision_function(X)  # higher == more anomalous

    results = []
    for i, ticker in enumerate(tickers):
        series = weekly_returns[ticker].dropna()
        latest_return = float(series.iloc[-1])
        mean = float(series.mean())
        std  = float(series.std())
        zscore = (latest_return - mean) / std if std > 0 else 0.0

        is_if_anomaly = bool(labels[i] == -1)
        is_z_anomaly  = bool(abs(zscore) > 2)

        if is_if_anomaly and is_z_anomaly:
            method = "both"
        elif is_if_anomaly:
            method = "isolation_forest"
        elif is_z_anomaly:
            method = "zscore"
        else:
            method = None

        results.append({
            "ticker":               ticker,
            "latest_weekly_return": round(latest_return, 4),
            "anomaly_score":        round(float(scores[i]), 4),
            "is_anomaly":           is_if_anomaly or is_z_anomaly,
            "zscore":               round(float(zscore), 4),
            "detection_method":     method,
        })

    results.sort(key=lambda r: r["anomaly_score"], reverse=True)
    anomaly_count = sum(1 for r in results if r["is_anomaly"])

    computation_time_ms = round((time.perf_counter() - start) * 1000, 3)

    return {
        "country":             country,
        "period":              period,
        "companyCount":        len(results),
        "anomalyCount":        anomaly_count,
        "companies":           results,
        "computation_time_ms": computation_time_ms,
    }


@router.get("/clusters")
def clusters(
    n_clusters: int = Query(5, ge=2, le=10),
    period:     str = Query("1y"),
):
    """
    K-means clustering of all companies on mean weekly return and weekly-return
    volatility — both currency-neutral, return-based features. Standardized
    (zero mean, unit variance) before KMeans so the two contribute equally
    regardless of their raw magnitude.
    """
    days = _period_to_days(period)

    df = fetch_df(
        """
        SELECT dp.ticker, dp.date, dp.close, c.country, c.sector
        FROM daily_prices dp
        JOIN companies c ON dp.ticker = c.ticker
        WHERE dp.date >= CURRENT_DATE - (:days || ' days')::interval
          AND dp.close IS NOT NULL
        ORDER BY dp.date ASC
        """,
        {"days": days},
    )

    if df.empty:
        raise HTTPException(status_code=404, detail="No price data found")

    start = time.perf_counter()

    meta = df.drop_duplicates("ticker").set_index("ticker")[["country", "sector"]]
    wide = _wide_prices(df)
    weekly_returns = wide.resample("W-FRI").last().pct_change()

    mean_weekly_return = weekly_returns.mean(axis=0)
    volatility         = weekly_returns.std(axis=0)

    tickers = [
        t for t in wide.columns
        if pd.notna(mean_weekly_return.get(t)) and pd.notna(volatility.get(t))
    ]
    if len(tickers) < n_clusters:
        raise HTTPException(
            status_code=422,
            detail=f"Need at least {n_clusters} companies with sufficient data, found {len(tickers)}",
        )

    features = pd.DataFrame({
        "mean_weekly_return": mean_weekly_return[tickers],
        "volatility":         volatility[tickers],
    })

    X_scaled = StandardScaler().fit_transform(features.to_numpy())

    km = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
    labels = km.fit_predict(X_scaled)

    companies = []
    for i, ticker in enumerate(tickers):
        companies.append({
            "ticker":             ticker,
            "country":            meta.loc[ticker, "country"],
            "sector":             meta.loc[ticker, "sector"],
            "cluster_id":         int(labels[i]),
            "mean_weekly_return": round(float(features.loc[ticker, "mean_weekly_return"]), 4),
            "volatility":         round(float(features.loc[ticker, "volatility"]), 4),
        })

    cluster_summary = []
    for cid in range(n_clusters):
        members = [c for c in companies if c["cluster_id"] == cid]
        if not members:
            cluster_summary.append({
                "cluster_id": cid, "size": 0, "mean_return": None,
                "mean_volatility": None, "dominant_country": None, "dominant_sector": None,
            })
            continue
        cluster_summary.append({
            "cluster_id":       cid,
            "size":             len(members),
            "mean_return":      round(float(np.mean([m["mean_weekly_return"] for m in members])), 4),
            "mean_volatility":  round(float(np.mean([m["volatility"] for m in members])), 4),
            "dominant_country": Counter(m["country"] for m in members).most_common(1)[0][0],
            "dominant_sector":  Counter(m["sector"]  for m in members).most_common(1)[0][0],
        })

    computation_time_ms = round((time.perf_counter() - start) * 1000, 3)

    return {
        "n_clusters":           n_clusters,
        "period":               period,
        "companyCount":         len(companies),
        "companies":            companies,
        "cluster_summary":      cluster_summary,
        "computation_time_ms":  computation_time_ms,
    }
