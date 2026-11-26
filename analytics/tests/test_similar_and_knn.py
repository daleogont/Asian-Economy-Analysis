from unittest.mock import patch

import numpy as np
import pandas as pd
import pytest

from tests.test_analytics_ml import _synthetic_prices


def _mixed_country_prices(n_days=120, seed=0):
    """Two countries: Testland (AAA, BBB close together; CCC far) and
    Otherland (DDD) -- so scope=country vs scope=global actually differ."""
    rng = np.random.RandomState(seed)
    dates = pd.bdate_range("2025-01-01", periods=n_days)
    specs = [("AAA", "Testland", 100.0, 1.0), ("BBB", "Testland", 100.0, 1.0), ("CCC", "Testland", 500.0, 1.0), ("DDD", "Otherland", 100.0, 1.0)]
    rows = []
    for ticker, country, start, vol in specs:
        walk = start + np.cumsum(rng.normal(0, vol, n_days))
        for d, price in zip(dates, walk):
            rows.append({
                "ticker": ticker, "date": d.strftime("%Y-%m-%d"), "close": float(price),
                "name": f"{ticker} Inc.", "country": country, "sector": "Testing",
            })
    return pd.DataFrame(rows)


def _companies_meta(df):
    return df.drop_duplicates("ticker")[["ticker", "country"]]


# ---------------------------------------------------------------------------
# /analytics/similar/{ticker}
# ---------------------------------------------------------------------------
def test_similar_defaults_to_country_scope(client):
    prices = _mixed_country_prices()

    def fake_fetch_df(query, params=None):
        if "FROM companies" in query and "daily_prices" not in query:
            return _companies_meta(prices)
        return prices[prices["country"] == "Testland"] if "c.country = :country" in query else prices

    with patch("app.routers.analytics_ml.fetch_df", side_effect=fake_fetch_df):
        resp = client.get("/analytics/similar/AAA?space=features")
    assert resp.status_code == 200
    body = resp.json()
    assert body["scope"] == "country"
    assert body["country"] == "Testland"
    returned_tickers = {r["ticker"] for r in body["results"]}
    assert "DDD" not in returned_tickers  # Otherland excluded by default


def test_similar_global_scope_allowed_for_features(client):
    prices = _mixed_country_prices()

    def fake_fetch_df(query, params=None):
        if "FROM companies" in query and "daily_prices" not in query:
            return _companies_meta(prices)
        return prices

    with patch("app.routers.analytics_ml.fetch_df", side_effect=fake_fetch_df):
        resp = client.get("/analytics/similar/AAA?space=features&scope=global")
    assert resp.status_code == 200
    body = resp.json()
    assert body["scope"] == "global"
    assert body["country"] is None


def test_similar_correlation_rejects_global_scope(client):
    resp = client.get("/analytics/similar/AAA?space=correlation&scope=global")
    assert resp.status_code == 400


def test_similar_unknown_ticker_404(client):
    with patch("app.routers.analytics_ml.fetch_df", return_value=pd.DataFrame()):
        resp = client.get("/analytics/similar/NOPE.XX")
    assert resp.status_code == 404


def test_similar_results_sorted_ascending_by_distance(client):
    prices = _mixed_country_prices()

    def fake_fetch_df(query, params=None):
        if "FROM companies" in query and "daily_prices" not in query:
            return _companies_meta(prices)
        return prices[prices["country"] == "Testland"]

    with patch("app.routers.analytics_ml.fetch_df", side_effect=fake_fetch_df):
        resp = client.get("/analytics/similar/AAA?space=features&n=2")
    results = resp.json()["results"]
    distances = [r["distance"] for r in results]
    assert distances == sorted(distances)


# ---------------------------------------------------------------------------
# kNN-distance detector in /analytics/anomalies
# ---------------------------------------------------------------------------
def test_anomalies_default_response_unaffected_by_knn_feature(client):
    df = _synthetic_prices(["AAA", "BBB", "CCC", "DDD", "EEE", "FFF"])
    with patch("app.routers.analytics_ml.fetch_df", return_value=df):
        resp = client.get("/analytics/anomalies?country=Testland&period=1y")
    assert resp.status_code == 200
    for c in resp.json()["companies"]:
        assert "knn_distance" not in c


def test_anomalies_include_knn_adds_field_without_removing_existing_ones(client):
    df = _synthetic_prices(["AAA", "BBB", "CCC", "DDD", "EEE", "FFF"])
    with patch("app.routers.analytics_ml.fetch_df", return_value=df):
        resp = client.get("/analytics/anomalies?country=Testland&period=1y&include_knn=true&knn_k=2")
    assert resp.status_code == 200
    companies = resp.json()["companies"]
    assert all("knn_distance" in c for c in companies)
    assert all("zscore" in c and "anomaly_score" in c for c in companies)
