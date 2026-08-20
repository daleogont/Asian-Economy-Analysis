import numpy as np
import pandas as pd

from app.models import feature_builder
from app.models.base import BaseForecastModel

LAGS = (1, 2, 3, 5, 10, 20)
FEATURE_COLS = [f"lag_{lag}" for lag in LAGS] + ["time_idx"]
_LAG_COL_NAMES = {f"lag_{lag}" for lag in LAGS}


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

    Stage 2 behavior (price-only lags + time index) is the default. Passing
    `use_enriched_features=True` (plus `ticker`/`country`/`db_conn`) switches
    to `feature_builder.build_features()`, which adds static fundamentals
    and macro features alongside the same lag features.
    """

    LAGS = LAGS

    def __init__(self, use_enriched_features=False, ticker=None, country=None, db_conn=None):
        self.use_enriched_features = use_enriched_features
        self.ticker = ticker
        self.country = country
        self.db_conn = db_conn
        # Read by BaseForecastModel._holdout_rmse_mae so the holdout clone
        # it creates is configured identically to this instance, instead of
        # falling back to price-only features.
        self._init_kwargs = {
            "use_enriched_features": use_enriched_features,
            "ticker": ticker,
            "country": country,
            "db_conn": db_conn,
        }
        self._feature_cols = FEATURE_COLS
        self._static_feature_row = {}

    def _build_estimator(self):
        raise NotImplementedError

    def _build_features(self, series: pd.Series):
        if self.use_enriched_features:
            raw = feature_builder.build_features(series, self.ticker, self.country, self.db_conn)
            feature_cols = [c for c in raw.columns if c != "y"]
            raw = raw.dropna(subset=feature_cols + ["y"])
            return raw[feature_cols], raw["y"], feature_cols
        X, y = build_supervised(series, self.LAGS)
        return X, y, FEATURE_COLS

    def fit(self, series: pd.Series):
        X, y, feature_cols = self._build_features(series)
        self._feature_cols = feature_cols
        self._model = self._build_estimator()
        self._model.fit(X, y)
        self._resid_std = float(np.std(y.to_numpy() - self._model.predict(X)))
        self._history_values = series.to_numpy().tolist()
        self._last_date = series.index[-1]
        self._freq = series.index.freq or "B"
        # Enriched (non-lag, non-time-index) features are static per
        # ticker/country, so just broadcast the fitted row's values across
        # every future forecast step.
        last_row = X.iloc[-1]
        self._static_feature_row = {
            c: last_row[c] for c in feature_cols if c not in _LAG_COL_NAMES and c != "time_idx"
        }
        return self

    def predict(self, steps: int) -> dict:
        values = list(self._history_values)
        preds = []
        for _ in range(steps):
            row = {f"lag_{lag}": values[-lag] for lag in self.LAGS}
            row["time_idx"] = len(values)
            row.update(self._static_feature_row)
            x_next = pd.DataFrame([row])[self._feature_cols]
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
