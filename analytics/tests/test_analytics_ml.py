from unittest.mock import patch

import numpy as np
import pandas as pd
import pytest

from app.routers.analytics_ml import correlation_distance_matrix, hierarchical_leaf_order


def _synthetic_prices(tickers, n_days=120, seed=0):
    """Rows shaped like the daily_prices x companies join query every
    analytics_ml.py endpoint runs: ticker, date, close, name, country, sector."""
    rng = np.random.RandomState(seed)
    dates = pd.bdate_range("2025-01-01", periods=n_days)
    rows = []
    base = {t: 100.0 + i * 10 for i, t in enumerate(tickers)}
    for t in tickers:
        walk = base[t] + np.cumsum(rng.normal(0, 1, n_days))
        for d, price in zip(dates, walk):
            rows.append({
                "ticker": t, "date": d.strftime("%Y-%m-%d"), "close": float(price),
                "name": f"{t} Inc.", "country": "Testland", "sector": "Testing",
            })
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# correlation_distance_matrix / hierarchical_leaf_order — pure functions
# ---------------------------------------------------------------------------
def test_correlation_distance_matrix_shape_and_diagonal():
    returns = pd.DataFrame({
        "A": [0.01, -0.02, 0.03, 0.0],
        "B": [0.02, -0.01, 0.025, 0.01],
        "C": [-0.01, 0.02, -0.03, 0.0],
    })
    tickers, dist = correlation_distance_matrix(returns)
    assert tickers == ["A", "B", "C"]
    assert dist.shape == (3, 3)
    assert np.allclose(np.diag(dist), 0.0)
    assert np.allclose(dist, dist.T)  # symmetric
    assert (dist >= 0).all()


def test_hierarchical_leaf_order_is_a_permutation():
    tickers = ["A", "B", "C", "D"]
    returns = pd.DataFrame({
        "A": [0.01, 0.02, -0.01, 0.03, 0.01],
        "B": [0.012, 0.021, -0.009, 0.029, 0.011],  # near-identical to A
        "C": [-0.02, -0.03, 0.04, -0.01, -0.02],
        "D": [-0.019, -0.028, 0.041, -0.009, -0.021],  # near-identical to C
    })
    _, dist = correlation_distance_matrix(returns)
    order = hierarchical_leaf_order(tickers, dist)
    assert sorted(order) == sorted(tickers)
    # correlated pairs should end up adjacent in leaf order
    idx = {t: i for i, t in enumerate(order)}
    assert abs(idx["A"] - idx["B"]) == 1
    assert abs(idx["C"] - idx["D"]) == 1


def test_hierarchical_leaf_order_under_three_tickers_is_noop():
    tickers = ["A", "B"]
    dist = np.array([[0, 0.5], [0.5, 0]])
    assert hierarchical_leaf_order(tickers, dist) == ["A", "B"]


# ---------------------------------------------------------------------------
# API-level
# ---------------------------------------------------------------------------
def test_correlation_clustered_order_returns_ordered_tickers(client):
    df = _synthetic_prices(["AAA", "BBB", "CCC"])
    with patch("app.routers.analytics_ml.fetch_df", return_value=df):
        resp = client.get("/analytics/correlation?country=Testland&order=clustered")
    assert resp.status_code == 200
    body = resp.json()
    assert body["order"] == "clustered"
    assert sorted(body["orderedTickers"]) == sorted(body["tickers"])


def test_correlation_default_order_has_no_ordered_tickers(client):
    df = _synthetic_prices(["AAA", "BBB", "CCC"])
    with patch("app.routers.analytics_ml.fetch_df", return_value=df):
        resp = client.get("/analytics/correlation?country=Testland")
    assert resp.status_code == 200
    assert resp.json()["orderedTickers"] is None


def test_clusters_includes_company_name(client):
    df = _synthetic_prices(["AAA", "BBB", "CCC", "DDD", "EEE", "FFF"])
    with patch("app.routers.analytics_ml.fetch_df", return_value=df):
        resp = client.get("/analytics/clusters?n_clusters=2&period=1y")
    assert resp.status_code == 200
    companies = resp.json()["companies"]
    assert len(companies) > 0
    assert all("name" in c and c["name"].endswith("Inc.") for c in companies)


def test_network_returns_mst_with_n_minus_one_edges(client):
    df = _synthetic_prices(["AAA", "BBB", "CCC", "DDD"])
    with patch("app.routers.analytics_ml.fetch_df", return_value=df):
        resp = client.get("/analytics/network?country=Testland&period=1y")
    assert resp.status_code == 200
    body = resp.json()
    assert len(body["nodes"]) == 4
    assert len(body["edges"]) == 3  # MST on 4 nodes always has n-1 edges
    for edge in body["edges"]:
        assert edge["distance"] >= 0


def test_network_requires_at_least_two_tickers(client):
    df = _synthetic_prices(["AAA"])
    with patch("app.routers.analytics_ml.fetch_df", return_value=df):
        resp = client.get("/analytics/network?country=Testland&period=1y")
    assert resp.status_code == 422
