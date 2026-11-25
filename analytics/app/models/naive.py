import numpy as np
import pandas as pd

from app.models.base import BaseForecastModel


class NaiveModel(BaseForecastModel):
    """Random-walk baseline: forecast = last observed close, repeated for
    every horizon step. Required so every other model's accuracy can be
    reported relative to it (RMSE / RMSE_naive).

    `season_period` turns this into a seasonal-naive variant instead:
    forecast = the value from `season_period` steps ago, tiled forward.
    Default (None) is the plain random walk.
    """

    name = "naive"

    def __init__(self, season_period: int | None = None):
        self.season_period = season_period
        self._init_kwargs = {"season_period": season_period}
        self._history = None
        self._last_date = None
        self._freq = None
        self._resid_std = 0.0

    def fit(self, series: pd.Series):
        self._history = series.to_numpy(dtype=float)
        self._last_date = series.index[-1]
        self._freq = series.index.freq or "B"
        diffs = np.diff(self._history)
        self._resid_std = float(np.std(diffs)) if len(diffs) else 0.0
        return self

    def predict(self, steps: int) -> dict:
        future_dates = pd.date_range(self._last_date, periods=steps + 1, freq=self._freq)[1:]

        if self.season_period and self.season_period > 0 and len(self._history) >= self.season_period:
            tail = self._history[-self.season_period:]
            mean = np.array([tail[i % self.season_period] for i in range(steps)], dtype=float)
        else:
            mean = np.full(steps, self._history[-1], dtype=float)

        # Flat +/-1.96*sigma band, same convention as the lag-feature models
        # (base.py has no analytic CI for a constant forecast either).
        margin = 1.96 * self._resid_std
        return {
            "dates": [d.strftime("%Y-%m-%d") for d in future_dates],
            "mean":  mean.tolist(),
            "lower": (mean - margin).tolist(),
            "upper": (mean + margin).tolist(),
        }
