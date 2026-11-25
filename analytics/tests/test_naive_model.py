import pandas as pd

from app.models.naive import NaiveModel


def _series(values):
    idx = pd.bdate_range("2024-01-01", periods=len(values))
    return pd.Series(values, index=idx)


def test_naive_forecast_is_flat_last_value():
    s = _series([10.0, 11.0, 9.0, 12.0, 15.0])
    m = NaiveModel()
    m.fit(s)
    out = m.predict(5)
    assert out["mean"] == [15.0] * 5
    assert len(out["dates"]) == 5


def test_naive_confidence_band_widens_with_volatility():
    calm   = _series([10.0, 10.1, 9.9, 10.0, 10.1])
    choppy = _series([10.0, 15.0, 5.0, 14.0, 6.0])

    calm_margin   = NaiveModel().fit(calm).predict(3)
    choppy_margin = NaiveModel().fit(choppy).predict(3)

    calm_width   = calm_margin["upper"][0] - calm_margin["lower"][0]
    choppy_width = choppy_margin["upper"][0] - choppy_margin["lower"][0]
    assert choppy_width > calm_width


def test_seasonal_naive_tiles_the_season():
    # period=3 season: [1, 2, 3, 1, 2, 3, ...] -> next 3 steps repeat [1, 2, 3]
    s = _series([1.0, 2.0, 3.0, 1.0, 2.0, 3.0])
    m = NaiveModel(season_period=3)
    m.fit(s)
    out = m.predict(3)
    assert out["mean"] == [1.0, 2.0, 3.0]


def test_naive_registered_in_model_registry():
    from app.routers.models import MODEL_REGISTRY

    assert "naive" in MODEL_REGISTRY
    assert MODEL_REGISTRY["naive"] is NaiveModel


def test_naive_not_cached():
    from app.routers.models import CACHEABLE_MODELS

    assert "naive" not in CACHEABLE_MODELS
