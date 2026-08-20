import pandas as pd
from statsmodels.tsa.arima.model import ARIMA

from app.models.base import BaseForecastModel


class ArimaModel(BaseForecastModel):
    name = "arima"

    def __init__(self, order=(1, 1, 1)):
        self.order = order
        self._result = None

    def fit(self, series: pd.Series):
        self._result = ARIMA(series, order=self.order).fit()
        return self

    def predict(self, steps: int) -> dict:
        forecast_res = self._result.get_forecast(steps=steps)
        mean = forecast_res.predicted_mean
        conf = forecast_res.conf_int(alpha=0.05)
        return {
            "dates": [d.strftime("%Y-%m-%d") for d in mean.index],
            "mean": mean.to_numpy().tolist(),
            "lower": conf.iloc[:, 0].to_numpy().tolist(),
            "upper": conf.iloc[:, 1].to_numpy().tolist(),
        }
