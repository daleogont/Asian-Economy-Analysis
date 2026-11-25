"""
Quantitative validation of the distance-based methods used elsewhere in
the app: do MST edges and K-means clusters actually line up with GICS
sector, or are they just noise? Two checks, per country and overall:

  1. MST same-sector edge share — of all edges in the minimum spanning
     tree over the correlation-distance matrix (d = sqrt(2*(1-rho))),
     what fraction connect two companies in the same GICS sector?
  2. Adjusted Rand Index between K-means clusters (mean weekly return +
     volatility — same feature definition as /analytics/clusters) and
     GICS sector labels.

Run inside the python-api container:
    docker compose exec python-api python scripts/validate_distance_methods.py
"""
import logging
import os
import sys
import warnings

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
import pandas as pd
from scipy.sparse.csgraph import minimum_spanning_tree
from sklearn.cluster import KMeans
from sklearn.metrics import adjusted_rand_score
from sklearn.preprocessing import StandardScaler

from app.db import fetch_df
from app.routers.analytics_ml import _wide_prices, correlation_distance_matrix

warnings.filterwarnings("ignore")
logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger("validate_distance_methods")

PERIOD_DAYS = 365  # 1y — same default as /analytics/clusters and /analytics/correlation
N_CLUSTERS = 5     # same default as /analytics/clusters
MIN_TICKERS_FOR_CLUSTERING = N_CLUSTERS + 1


def mst_same_sector_share(dist_matrix: np.ndarray, sectors: list) -> tuple[float, int]:
    """Builds the MST over `dist_matrix` and returns (same-sector edge
    share, n_edges). A zero-distance edge (rho == 1 for two distinct
    tickers) is nudged to a small epsilon first, since scipy's sparse
    conversion drops values near float precision (empirically, 1e-9 was
    still dropped; 1e-6 is safely above that floor and negligible next to
    real distances, which range roughly 0-2)."""
    safe = dist_matrix.copy()
    n = safe.shape[0]
    off_diag_zero = (safe == 0) & ~np.eye(n, dtype=bool)
    safe[off_diag_zero] = 1e-6

    mst = minimum_spanning_tree(safe).toarray()
    edges = np.argwhere(mst > 0)
    if len(edges) == 0:
        return 0.0, 0

    same_sector = sum(1 for i, j in edges if sectors[i] == sectors[j])
    return same_sector / len(edges), len(edges)


def cluster_ari_vs_sector(features: pd.DataFrame, sectors: list, n_clusters: int = N_CLUSTERS) -> float:
    """KMeans on standardized features vs GICS sector labels, scored by
    adjusted Rand index (0 = no better than random, 1 = perfect match)."""
    X_scaled = StandardScaler().fit_transform(features.to_numpy())
    labels = KMeans(n_clusters=n_clusters, random_state=42, n_init=10).fit_predict(X_scaled)
    return float(adjusted_rand_score(labels, sectors))


def _build_universe(period_days: int = PERIOD_DAYS) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Returns (meta, returns): meta indexed by ticker with country/sector,
    returns = daily pct-change matrix (date x ticker)."""
    df = fetch_df(
        """
        SELECT dp.ticker, dp.date, dp.close, c.country, c.sector
        FROM daily_prices dp
        JOIN companies c ON dp.ticker = c.ticker
        WHERE dp.date >= CURRENT_DATE - (:days || ' days')::interval
          AND dp.close IS NOT NULL
        ORDER BY dp.date ASC
        """,
        {"days": period_days},
    )
    meta = df.drop_duplicates("ticker").set_index("ticker")[["country", "sector"]]
    wide = _wide_prices(df)
    returns = wide.pct_change().dropna(how="all")
    return meta, returns


def _weekly_features(wide_prices: pd.DataFrame, tickers: list) -> pd.DataFrame:
    weekly_returns = wide_prices[tickers].resample("W-FRI").last().pct_change()
    return pd.DataFrame({
        "mean_weekly_return": weekly_returns.mean(axis=0),
        "volatility":         weekly_returns.std(axis=0),
    }).dropna()


def validate_group(label: str, tickers: list, meta: pd.DataFrame, returns: pd.DataFrame) -> dict:
    tickers = [t for t in tickers if t in returns.columns]
    if len(tickers) < 3:
        return {"group": label, "n_tickers": len(tickers), "skipped": "fewer than 3 tickers"}

    group_tickers, dist = correlation_distance_matrix(returns[tickers])
    sectors = [meta.loc[t, "sector"] for t in group_tickers]
    same_sector_share, n_edges = mst_same_sector_share(dist, sectors)

    result = {
        "group": label,
        "n_tickers": len(group_tickers),
        "mst_edges": n_edges,
        "mst_same_sector_share": round(same_sector_share, 4),
    }

    wide = returns[group_tickers].add(1).cumprod()  # reconstruct a price-like series for weekly resampling
    features = _weekly_features(wide, group_tickers)
    if len(features) >= MIN_TICKERS_FOR_CLUSTERING:
        feat_sectors = [meta.loc[t, "sector"] for t in features.index]
        result["ari_vs_sector"] = round(cluster_ari_vs_sector(features, feat_sectors), 4)
    else:
        result["ari_vs_sector"] = None

    return result


def main():
    meta, returns = _build_universe()
    results = []

    for country, group in meta.groupby("country"):
        results.append(validate_group(country, list(group.index), meta, returns))

    results.append(validate_group("ALL (overall)", list(meta.index), meta, returns))

    header = f"{'group':<20} {'n_tickers':>9} {'mst_edges':>9} {'mst_same_sector':>16} {'ari_vs_sector':>14}"
    logger.info(header)
    logger.info("-" * len(header))
    for r in results:
        if "skipped" in r:
            logger.info(f"{r['group']:<20} {r['n_tickers']:>9}  skipped: {r['skipped']}")
            continue
        ari = f"{r['ari_vs_sector']:.4f}" if r["ari_vs_sector"] is not None else "n/a"
        logger.info(
            f"{r['group']:<20} {r['n_tickers']:>9} {r['mst_edges']:>9} "
            f"{r['mst_same_sector_share']:>16.4f} {ari:>14}"
        )

    return results


if __name__ == "__main__":
    main()
