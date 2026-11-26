import time
import warnings
from collections import Counter
from itertools import combinations

import numpy as np
import pandas as pd
from fastapi import APIRouter, HTTPException, Query
from scipy.cluster.hierarchy import dendrogram, linkage
from scipy.sparse.csgraph import minimum_spanning_tree
from scipy.spatial.distance import pdist, squareform
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


def correlation_distance_matrix(returns: pd.DataFrame):
    """rho -> d = sqrt(2*(1-rho)) on daily returns. Shared by the MST/
    hierarchical-clustering work (analytics/scripts/validate_distance_methods.py
    today; the /analytics/network and ordered-heatmap endpoints reuse this
    too) so every consumer agrees on the same distance definition."""
    tickers = sorted(returns.columns)
    corr = returns[tickers].corr(method="pearson").to_numpy()
    corr = np.clip(corr, -1.0, 1.0)
    dist = np.sqrt(2 * (1 - corr))
    np.fill_diagonal(dist, 0.0)
    return tickers, dist


def hierarchical_leaf_order(tickers: list, dist: np.ndarray) -> list:
    """Average-linkage hierarchical clustering over a correlation-distance
    matrix, returning tickers in dendrogram leaf order (correlated
    companies placed next to each other) instead of alphabetical order."""
    if len(tickers) < 3:
        return list(tickers)
    condensed = squareform(dist, checks=False)
    z = linkage(condensed, method="average")
    leaves = dendrogram(z, no_plot=True)["leaves"]
    return [tickers[i] for i in leaves]


@router.get("/correlation")
def correlation(
    country: str = Query(...),
    period:  str = Query("1y"),
    order:   str = Query("default", pattern="^(default|clustered)$"),
):
    """
    Pairwise Pearson correlation of daily returns across every company in a
    country. Correlation is computed on returns (not raw price levels) to
    avoid spurious trend-driven correlation between unrelated stocks.

    `order=clustered` additionally returns `orderedTickers`: the same
    tickers re-ordered by average-linkage hierarchical clustering over the
    correlation-distance matrix (d = sqrt(2*(1-rho))), so a heatmap drawn
    in that order groups correlated companies together instead of sorting
    alphabetically. `tickers` (default/alphabetical) is always present and
    unchanged either way.
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

    ordered_tickers = None
    if order == "clustered":
        _, dist = correlation_distance_matrix(returns[tickers])
        ordered_tickers = hierarchical_leaf_order(tickers, dist)

    computation_time_ms = round((time.perf_counter() - start) * 1000, 3)

    return {
        "country":            country,
        "period":             period,
        "order":              order,
        "tickers":            tickers,
        "orderedTickers":     ordered_tickers,
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
    include_knn: bool = Query(False),
    knn_k: int = Query(5, ge=1, le=20),
    knn_percentile: float = Query(95.0, ge=50.0, le=99.9),
):
    """
    Flags anomalous companies within a country by two independent methods:
      - IsolationForest over each company's weekly-return time series
      - a simple Z-score on each company's latest weekly return vs its own
        history (|z| > 2)

    `include_knn=true` adds a third, independent detector: for each company,
    the Euclidean distance (in the same standardized mean-weekly-return +
    volatility space `/analytics/clusters` uses) to its `knn_k`-th nearest
    neighbor within the country. Companies above the `knn_percentile`
    percentile of that distance are flagged `"knn_distance"`. Off by
    default — this detector has not been event-study validated the way the
    other two have, so it never changes the default response; opt in
    explicitly to see it.
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

    # kNN-distance detector — same (mean_weekly_return, volatility) feature
    # definition as /analytics/clusters, standardized before distances so
    # neither feature dominates. Only computed when requested.
    knn_distance_by_ticker = {}
    if include_knn:
        k = min(knn_k, len(tickers) - 1)
        mean_weekly_return = weekly_returns[tickers].mean(axis=0)
        volatility = weekly_returns[tickers].std(axis=0)
        knn_tickers = [
            t for t in tickers
            if pd.notna(mean_weekly_return.get(t)) and pd.notna(volatility.get(t))
        ]
        if k >= 1 and len(knn_tickers) > k:
            features = np.column_stack([
                mean_weekly_return[knn_tickers].to_numpy(),
                volatility[knn_tickers].to_numpy(),
            ])
            X_scaled = StandardScaler().fit_transform(features)
            dmat = squareform(pdist(X_scaled))
            kth_dist = np.sort(dmat, axis=1)[:, k]  # index 0 is self (distance 0)
            threshold = float(np.percentile(kth_dist, knn_percentile))
            for i, t in enumerate(knn_tickers):
                knn_distance_by_ticker[t] = {
                    "distance": float(kth_dist[i]),
                    "is_anomaly": bool(kth_dist[i] > threshold),
                }

    results = []
    for i, ticker in enumerate(tickers):
        series = weekly_returns[ticker].dropna()
        latest_return = float(series.iloc[-1])
        mean = float(series.mean())
        std  = float(series.std())
        zscore = (latest_return - mean) / std if std > 0 else 0.0

        is_if_anomaly = bool(labels[i] == -1)
        is_z_anomaly  = bool(abs(zscore) > 2)
        knn_info = knn_distance_by_ticker.get(ticker)
        is_knn_anomaly = bool(knn_info["is_anomaly"]) if knn_info else False

        fired = []
        if is_if_anomaly:
            fired.append("isolation_forest")
        if is_z_anomaly:
            fired.append("zscore")
        if include_knn and is_knn_anomaly:
            fired.append("knn_distance")

        if not fired:
            method = None
        elif len(fired) == 1:
            method = fired[0]
        elif set(fired) == {"isolation_forest", "zscore"}:
            method = "both"  # preserved exactly as before include_knn existed
        else:
            method = "+".join(fired)

        row = {
            "ticker":               ticker,
            "latest_weekly_return": round(latest_return, 4),
            "anomaly_score":        round(float(scores[i]), 4),
            "is_anomaly":           is_if_anomaly or is_z_anomaly or is_knn_anomaly,
            "zscore":               round(float(zscore), 4),
            "detection_method":     method,
        }
        if include_knn:
            row["knn_distance"] = round(knn_info["distance"], 4) if knn_info else None
        results.append(row)

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
        SELECT dp.ticker, dp.date, dp.close, c.name, c.country, c.sector
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

    meta = df.drop_duplicates("ticker").set_index("ticker")[["name", "country", "sector"]]
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
            "name":               meta.loc[ticker, "name"],
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


# A zero-distance edge (rho == 1 for two distinct tickers) must still be
# treated as an edge, not as scipy's dense-matrix convention for "no
# edge." 1e-6 is safely above the float-precision floor where scipy's
# sparse conversion starts silently dropping values (confirmed empirically
# in analytics/scripts/validate_distance_methods.py's test suite — 1e-9
# was dropped, 1e-6 is not) and negligible next to real distances, which
# range roughly 0-2.
_MST_ZERO_EPSILON = 1e-6


@router.get("/network")
def network(
    country: str = Query(...),
    period:  str = Query("1y"),
):
    """
    Minimum spanning tree over the correlation-distance matrix
    (d = sqrt(2*(1-rho)) on daily returns) for every company in a country —
    the sparsest graph that keeps every company connected to its closest
    peers, for a node-link visualization.
    """
    days = _period_to_days(period)

    df = fetch_df(
        """
        SELECT dp.ticker, dp.date, dp.close, c.name, c.sector
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

    meta = df.drop_duplicates("ticker").set_index("ticker")[["name", "sector"]]
    wide = _wide_prices(df)
    returns = wide.pct_change().dropna(how="all")

    tickers, dist = correlation_distance_matrix(returns)
    if len(tickers) < 2:
        raise HTTPException(
            status_code=422,
            detail=f"Need at least 2 tickers with data in '{country}', found {len(tickers)}",
        )

    safe = dist.copy()
    n = safe.shape[0]
    off_diag_zero = (safe == 0) & ~np.eye(n, dtype=bool)
    safe[off_diag_zero] = _MST_ZERO_EPSILON

    mst = minimum_spanning_tree(safe).toarray()
    edge_indices = np.argwhere(mst > 0)

    nodes = [
        {"ticker": t, "name": meta.loc[t, "name"], "sector": meta.loc[t, "sector"]}
        for t in tickers
    ]
    edges = [
        {
            "source":   tickers[i],
            "target":   tickers[j],
            "distance": round(float(dist[i, j]), 4),
        }
        for i, j in edge_indices
    ]

    computation_time_ms = round((time.perf_counter() - start) * 1000, 3)

    return {
        "country":            country,
        "period":             period,
        "nodes":              nodes,
        "edges":              edges,
        "computation_time_ms": computation_time_ms,
    }


@router.get("/similar/{ticker}")
def similar(
    ticker: str,
    n:      int = Query(5, ge=1, le=20),
    space:  str = Query("features", pattern="^(features|correlation)$"),
    scope:  str = Query("country", pattern="^(country|global)$"),
    period: str = Query("1y"),
):
    """
    The `n` companies closest to `ticker`:
      - `space=features`: Euclidean distance on standardized
        (mean_weekly_return, volatility) — same feature definition
        `/analytics/clusters` uses. `scope=global` allowed.
      - `space=correlation`: d = sqrt(2*(1-rho)) on daily returns, the
        same definition `/analytics/network` uses. **`scope=country`
        only** — comparing correlation across exchanges with
        non-overlapping trading days/holidays would conflate "didn't
        trade on the same days" with "genuinely uncorrelated", so
        `scope=global` is rejected (400) for this space rather than
        silently returning a distorted number.
    """
    ticker = ticker.upper()

    if space == "correlation" and scope == "global":
        raise HTTPException(
            status_code=400,
            detail="space=correlation only supports scope=country — cross-country correlation "
                   "would conflate non-synchronous trading calendars with genuine decorrelation.",
        )

    meta_lookup = fetch_df(
        "SELECT ticker, country FROM companies WHERE ticker = :ticker", {"ticker": ticker}
    )
    if meta_lookup.empty:
        raise HTTPException(status_code=404, detail=f"Unknown ticker '{ticker}'")
    own_country = meta_lookup.iloc[0]["country"]

    days = _period_to_days(period)
    country_filter = "AND c.country = :country" if scope == "country" else ""
    params = {"days": days}
    if scope == "country":
        params["country"] = own_country

    df = fetch_df(
        f"""
        SELECT dp.ticker, dp.date, dp.close, c.name, c.sector
        FROM daily_prices dp
        JOIN companies c ON dp.ticker = c.ticker
        WHERE dp.date >= CURRENT_DATE - (:days || ' days')::interval
          AND dp.close IS NOT NULL
          {country_filter}
        ORDER BY dp.date ASC
        """,
        params,
    )

    if df.empty or ticker not in df["ticker"].unique():
        raise HTTPException(status_code=404, detail=f"No price data for '{ticker}' in the requested scope")

    start = time.perf_counter()

    meta = df.drop_duplicates("ticker").set_index("ticker")[["name", "sector"]]
    wide = _wide_prices(df)

    if space == "features":
        weekly_returns = wide.resample("W-FRI").last().pct_change()
        mean_weekly_return = weekly_returns.mean(axis=0)
        volatility = weekly_returns.std(axis=0)
        candidates = [
            t for t in wide.columns
            if pd.notna(mean_weekly_return.get(t)) and pd.notna(volatility.get(t))
        ]
        if ticker not in candidates or len(candidates) < 2:
            raise HTTPException(status_code=422, detail=f"Not enough feature data for '{ticker}'")

        features = pd.DataFrame({
            "mean_weekly_return": mean_weekly_return[candidates],
            "volatility":         volatility[candidates],
        })
        X_scaled = StandardScaler().fit_transform(features.to_numpy())
        idx = {t: i for i, t in enumerate(candidates)}
        target_vec = X_scaled[idx[ticker]]
        dists = np.linalg.norm(X_scaled - target_vec, axis=1)
        pairs = [(t, float(dists[idx[t]])) for t in candidates if t != ticker]
    else:
        returns = wide.pct_change().dropna(how="all")
        candidates, dist_matrix = correlation_distance_matrix(returns)
        if ticker not in candidates or len(candidates) < 2:
            raise HTTPException(status_code=422, detail=f"Not enough return data for '{ticker}'")

        idx = {t: i for i, t in enumerate(candidates)}
        ti = idx[ticker]
        pairs = [(t, float(dist_matrix[ti, idx[t]])) for t in candidates if t != ticker]

    pairs.sort(key=lambda p: p[1])
    top = pairs[:n]

    results = [
        {
            "ticker":   t,
            "name":     meta.loc[t, "name"],
            "sector":   meta.loc[t, "sector"],
            "distance": round(d, 4),
        }
        for t, d in top
    ]

    computation_time_ms = round((time.perf_counter() - start) * 1000, 3)

    return {
        "ticker":             ticker,
        "space":              space,
        "scope":              scope,
        "country":            own_country if scope == "country" else None,
        "n":                  n,
        "results":            results,
        "computation_time_ms": computation_time_ms,
    }
