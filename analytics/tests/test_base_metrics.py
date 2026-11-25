import pandas as pd

from app.models.naive import NaiveModel


def test_run_reports_separate_tracemalloc_and_rss_metrics():
    idx = pd.bdate_range("2024-01-01", periods=100)
    series = pd.Series(range(100), index=idx, dtype=float)

    result = NaiveModel().run(series, steps=5)
    metrics = result["metrics"]

    assert "memory_mb" in metrics
    assert "rss_mb" in metrics
    assert metrics["memory_mb"] >= 0
    assert metrics["rss_mb"] >= 0
