import numpy as np
import pandas as pd

from app.models.base import BaseForecastModel

LAGS = (1, 2, 3, 5, 10, 20)
FEATURE_COLS = [f"lag_{lag}" for lag in LAGS] + ["time_idx"]


def build_supervised(series: pd.Series, lags=LAGS):
    """Turn a price series into (X, y): lagged closes + a time index feature."""
    df = pd.DataFrame({"y": series.to_numpy()}, index=series.index)
    for lag in lags:
        df[f"lag_{lag}"] = series.shift(lag).to_numpy()
    df["time_idx"] = np.arange(len(series))
    df = df.dropna()
    return df[[f"lag_{lag}" for lag in lags] + ["time_idx"]], df["y"]


class LaggedFeatureModel(BaseForecastModel):
    """Shared fit/predict for regressors trained on lagged close-price features.

    Subclasses only provide `_build_estimator()`. Forecasting beyond the
    training data is iterative: predict one step, append it to the price
    history, use it to build the lag features for the next step, repeat.
    """

    LAGS = LAGS

    def _build_estimator(self):
        raise NotImplementedError

    def fit(self, series: pd.Series):
        X, y = build_supervised(series, self.LAGS)
        self._model = self._build_estimator()
        self._model.fit(X, y)
        self._resid_std = float(np.std(y.to_numpy() - self._model.predict(X)))
        self._history_values = series.to_numpy().tolist()
        self._last_date = series.index[-1]
        self._freq = series.index.freq or "B"
        return self

    def predict(self, steps: int) -> dict:
        values = list(self._history_values)
        preds = []
        for _ in range(steps):
            row = {f"lag_{lag}": values[-lag] for lag in self.LAGS}
            row["time_idx"] = len(values)
            x_next = pd.DataFrame([row])[FEATURE_COLS]
            pred = float(self._model.predict(x_next)[0])
            preds.append(pred)
            values.append(pred)

        future_dates = pd.date_range(self._last_date, periods=steps + 1, freq=self._freq)[1:]
        mean = np.array(preds)
        margin = 1.96 * self._resid_std
        return {
            "dates": [d.strftime("%Y-%m-%d") for d in future_dates],
            "mean":  mean.tolist(),
            "lower": (mean - margin).tolist(),
            "upper": (mean + margin).tolist(),
        }
