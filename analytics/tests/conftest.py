import numpy as np
import pandas as pd
import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client():
    """Plain (non-context-manager) TestClient: routes work without running
    lifespan, which avoids every test depending on a live Postgres/Redis
    connection just to exercise request/response wiring."""
    return TestClient(app)


SYNTHETIC_SEED = 0
SYNTHETIC_N_DAYS = 1190
SYNTHETIC_START_PRICE = 160.0
SYNTHETIC_LOG_RETURN_STD = 0.015


def build_synthetic_price_series(
    seed: int = SYNTHETIC_SEED,
    n_days: int = SYNTHETIC_N_DAYS,
    start_price: float = SYNTHETIC_START_PRICE,
    log_return_std: float = SYNTHETIC_LOG_RETURN_STD,
) -> pd.DataFrame:
    """Deterministic stand-in for a real ticker snapshot. Raw price data
    (research/data/*.csv) is excluded from the repo because the provider's
    terms don't permit redistribution -- see research/README.md -- so test
    fixtures can't carry real prices either. A fixed-seed geometric random
    walk gives a ~4.7-year (1190 business day) daily-close series with
    realistic daily volatility, long enough to exercise a 504-day
    (~2 year) training window plus a 30-day horizon."""
    rng = np.random.RandomState(seed)
    log_returns = rng.normal(loc=0.0, scale=log_return_std, size=n_days)
    close = start_price * np.exp(np.cumsum(log_returns))
    dates = pd.bdate_range("2021-01-04", periods=n_days)
    return pd.DataFrame({
        "ticker": "TEST.XX",
        "country": "Testland",
        "date": dates.strftime("%Y-%m-%d"),
        "close": close,
    })


@pytest.fixture
def synthetic_price_series() -> pd.DataFrame:
    return build_synthetic_price_series()
