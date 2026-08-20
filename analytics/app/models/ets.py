import numpy as np
import pandas as pd
from statsmodels.tsa.holtwinters import ExponentialSmoothing

from app.models.base import BaseForecastModel


class EtsModel(BaseForecastModel):
    """ETS / Holt-Winters — additive trend + additive seasonality."""

    name = "ets"

    def __init__(self, seasonal_periods: int = 5):
        self.seasonal_periods = seasonal_periods
        self._result = None
        self._resid_std = None

    def fit(self, series: pd.Series):
        model = ExponentialSmoothing(
            series,
            trend="add",
            seasonal="add",
            seasonal_periods=self.seasonal_periods,
            initialization_method="estimated",
        )
        self._result = model.fit()
        self._resid_std = float(np.std(self._result.resid))
        return self

    def predict(self, steps: int) -> dict:
        forecast = self._result.forecast(steps)
        margin = 1.96 * self._resid_std
        mean = forecast.to_numpy()
        return {
            "dates": [d.strftime("%Y-%m-%d") for d in forecast.index],
            "mean":  mean.tolist(),
            "lower": (mean - margin).tolist(),
            "upper": (mean + margin).tolist(),
        }
