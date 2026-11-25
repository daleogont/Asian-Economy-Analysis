import os
import sys

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts"))
from validate_distance_methods import cluster_ari_vs_sector, mst_same_sector_share  # noqa: E402


def test_mst_same_sector_share_prefers_within_sector_edges():
    # A,B in sector X; C,D in sector Y. Within-sector pairs are close (d=1),
    # cross-sector pairs are far (d=10). MST must pick both within-sector
    # edges plus exactly one bridging edge -> 2/3 same-sector.
    tickers = ["A", "B", "C", "D"]
    sectors = ["X", "X", "Y", "Y"]
    dist = np.array([
        [0,  1, 10, 10],
        [1,  0, 10, 10],
        [10, 10,  0,  1],
        [10, 10,  1,  0],
    ], dtype=float)

    share, n_edges = mst_same_sector_share(dist, sectors)
    assert n_edges == 3  # MST on 4 nodes always has n-1 edges
    assert share == pytest.approx(2 / 3)


def test_mst_same_sector_share_handles_exact_zero_distance():
    # Two distinct tickers with rho == 1 (d == 0) must still be treated as
    # an edge, not as "no edge" (scipy's dense-matrix convention for 0).
    tickers = ["A", "B", "C"]
    sectors = ["X", "X", "Y"]
    dist = np.array([
        [0, 0, 5],
        [0, 0, 5],
        [5, 5, 0],
    ], dtype=float)

    share, n_edges = mst_same_sector_share(dist, sectors)
    assert n_edges == 2
    assert share == pytest.approx(0.5)


def test_cluster_ari_perfect_match_when_clusters_align_with_sectors():
    # Two well-separated blobs, sector labels matching the blobs exactly.
    rng = np.random.RandomState(0)
    group_a = rng.normal(loc=0.0, scale=0.1, size=(5, 2))
    group_b = rng.normal(loc=10.0, scale=0.1, size=(5, 2))
    features = pd.DataFrame(
        np.vstack([group_a, group_b]),
        columns=["mean_weekly_return", "volatility"],
    )
    sectors = ["X"] * 5 + ["Y"] * 5

    ari = cluster_ari_vs_sector(features, sectors, n_clusters=2)
    assert ari == pytest.approx(1.0, abs=1e-6)


def test_cluster_ari_low_when_sectors_are_random_noise():
    rng = np.random.RandomState(0)
    group_a = rng.normal(loc=0.0, scale=0.1, size=(5, 2))
    group_b = rng.normal(loc=10.0, scale=0.1, size=(5, 2))
    features = pd.DataFrame(
        np.vstack([group_a, group_b]),
        columns=["mean_weekly_return", "volatility"],
    )
    # Sectors interleaved, uncorrelated with which blob a point is in.
    sectors = ["X", "Y"] * 5

    ari = cluster_ari_vs_sector(features, sectors, n_clusters=2)
    assert ari < 0.5
