import pandas as pd
from statsmodels.tsa.statespace.sarimax import SARIMAX

from app.models.base import BaseForecastModel


class SarimaModel(BaseForecastModel):
    """SARIMA — order=(1,1,1), seasonal_order=(1,1,0,5) (5-day trading week)."""

    name = "sarima"

    def __init__(self, order=(1, 1, 1), seasonal_order=(1, 1, 0, 5)):
        self.order = order
        self.seasonal_order = seasonal_order
        self._result = None

    def fit(self, series: pd.Series):
        model = SARIMAX(
            series,
            order=self.order,
            seasonal_order=self.seasonal_order,
            enforce_stationarity=False,
            enforce_invertibility=False,
        )
        self._result = model.fit(disp=False)
        return self

    def predict(self, steps: int) -> dict:
        forecast_res = self._result.get_forecast(steps=steps)
        mean = forecast_res.predicted_mean
        conf = forecast_res.conf_int(alpha=0.05)
        return {
            "dates": [d.strftime("%Y-%m-%d") for d in mean.index],
            "mean":  mean.to_numpy().tolist(),
            "lower": conf.iloc[:, 0].to_numpy().tolist(),
            "upper": conf.iloc[:, 1].to_numpy().tolist(),
        }
