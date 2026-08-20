import logging

import pandas as pd
from prophet import Prophet

from app.models.base import BaseForecastModel

logging.getLogger("cmdstanpy").setLevel(logging.WARNING)
logging.getLogger("prophet").setLevel(logging.WARNING)


class ProphetModel(BaseForecastModel):
    """Meta Prophet — daily seasonality off, weekly + yearly seasonality on."""

    name = "prophet"

    def __init__(self):
        self._model = None
        self._last_date = None
        self._freq = None

    def fit(self, series: pd.Series):
        self._last_date = series.index[-1]
        self._freq = series.index.freq or "B"
        df = pd.DataFrame({"ds": series.index, "y": series.to_numpy()})
        self._model = Prophet(
            daily_seasonality=False,
            weekly_seasonality=True,
            yearly_seasonality=True,
        )
        self._model.fit(df)
        return self

    def predict(self, steps: int) -> dict:
        future_dates = pd.date_range(self._last_date, periods=steps + 1, freq=self._freq)[1:]
        forecast = self._model.predict(pd.DataFrame({"ds": future_dates}))
        return {
            "dates": [d.strftime("%Y-%m-%d") for d in future_dates],
            "mean":  forecast["yhat"].to_numpy().tolist(),
            "lower": forecast["yhat_lower"].to_numpy().tolist(),
            "upper": forecast["yhat_upper"].to_numpy().tolist(),
        }
