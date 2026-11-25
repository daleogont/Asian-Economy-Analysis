"""
Research-only model variants for the rolling-origin benchmark:
  Tier B (baselines):   RandomWalkModel, RandomWalkDriftModel
  Tier C (optimized):   OptimizedArimaModel, OptimizedEtsModel, OptimizedProphetModel
  Tier D (ablation):    ProphetNoYearly (production Prophet, yearly_seasonality off)

All expose the same fit(series)/predict(steps) interface as the production
BaseForecastModel subclasses, so rolling_benchmark.py can drive every tier
identically. None of this is imported by, or imported from, production
code except to reuse ProphetModel's predict() for the ablation tier.
"""
import itertools
import logging
import os
import sys

import numpy as np
import pandas as pd
from prophet import Prophet
from statsmodels.tsa.arima.model import ARIMA
from statsmodels.tsa.exponential_smoothing.ets import ETSModel
from statsmodels.tsa.stattools import kpss

logging.getLogger("cmdstanpy").setLevel(logging.WARNING)
logging.getLogger("prophet").setLevel(logging.WARNING)

ANALYTICS_DIR = "/app" if os.path.exists("/app/app") else os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "analytics"
)
if ANALYTICS_DIR not in sys.path:
    sys.path.insert(0, ANALYTICS_DIR)
from app.models.prophet import ProphetModel as ProductionProphetModel  # noqa: E402


# ---------------------------------------------------------------------------
# Tier B — baselines
# ---------------------------------------------------------------------------
class RandomWalkModel:
    name = "random_walk"

    def __init__(self):
        self._last = None
        self._last_date = None
        self._freq = None

    def fit(self, series: pd.Series):
        self._last = float(series.iloc[-1])
        self._last_date = series.index[-1]
        self._freq = series.index.freq or "B"
        return self

    def predict(self, steps: int) -> dict:
        dates = pd.date_range(self._last_date, periods=steps + 1, freq=self._freq)[1:]
        mean = [self._last] * steps
        return {
            "dates": [d.strftime("%Y-%m-%d") for d in dates],
            "mean": mean, "lower": mean, "upper": mean,
        }


class RandomWalkDriftModel:
    name = "random_walk_drift"

    def __init__(self):
        self._last = None
        self._drift = None
        self._last_date = None
        self._freq = None

    def fit(self, series: pd.Series):
        self._last = float(series.iloc[-1])
        diffs = series.diff().dropna()
        self._drift = float(diffs.mean()) if len(diffs) else 0.0
        self._last_date = series.index[-1]
        self._freq = series.index.freq or "B"
        return self

    def predict(self, steps: int) -> dict:
        dates = pd.date_range(self._last_date, periods=steps + 1, freq=self._freq)[1:]
        mean = [self._last + self._drift * (i + 1) for i in range(steps)]
        return {
            "dates": [d.strftime("%Y-%m-%d") for d in dates],
            "mean": mean, "lower": mean, "upper": mean,
        }


# ---------------------------------------------------------------------------
# Tier C — optimized
# ---------------------------------------------------------------------------
def _select_d_kpss(series: pd.Series, max_d: int = 2, alpha: float = 0.05) -> int:
    """KPSS null = stationary. Difference while we reject the null."""
    s = series.copy()
    d = 0
    while d < max_d:
        try:
            _, pvalue = kpss(s.dropna(), regression="c", nlags="auto")[:2]
        except Exception:
            break
        if pvalue < alpha:
            s = s.diff().dropna()
            d += 1
        else:
            break
    return d


class OptimizedArimaModel:
    """ARIMA(p,d,q) with d chosen by KPSS and (p,q) grid-searched by AIC
    over 0..3 — the statsmodels-only alternative to pmdarima.auto_arima."""

    name = "arima_optimized"
    P_RANGE = range(4)
    Q_RANGE = range(4)

    def __init__(self):
        self._result = None
        self.selected_order = None

    def fit(self, series: pd.Series):
        d = _select_d_kpss(series)
        best, best_aic, best_order = None, np.inf, None
        for p, q in itertools.product(self.P_RANGE, self.Q_RANGE):
            if p == 0 and q == 0:
                continue
            try:
                res = ARIMA(series, order=(p, d, q)).fit()
                if np.isfinite(res.aic) and res.aic < best_aic:
                    best, best_aic, best_order = res, res.aic, (p, d, q)
            except Exception:
                continue
        if best is None:
            best = ARIMA(series, order=(1, 1, 1)).fit()
            best_order = (1, 1, 1)
        self._result = best
        self.selected_order = best_order
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


class OptimizedEtsModel:
    """ETS(error, trend, seasonal) via statsmodels' state-space ETSModel
    (supports multiplicative error, unlike the Holt-Winters class the
    production EtsModel uses), AICc-selected over:
      error    {add, mul}
      trend    {none, add, damped-add}
      seasonal {none, add(5)}
    """

    name = "ets_optimized"
    TREND_CONFIGS = [(None, False), ("add", False), ("add", True)]
    SEASONAL_OPTIONS = [None, "add"]
    ERROR_OPTIONS = ["add", "mul"]

    def __init__(self):
        self._result = None
        self._resid_std = None
        self.selected_config = None

    def fit(self, series: pd.Series):
        best, best_aicc, best_cfg = None, np.inf, None
        for error, (trend, damped), seasonal in itertools.product(
            self.ERROR_OPTIONS, self.TREND_CONFIGS, self.SEASONAL_OPTIONS
        ):
            kwargs = dict(error=error, trend=trend, damped_trend=damped)
            if seasonal:
                kwargs.update(seasonal=seasonal, seasonal_periods=5)
            try:
                res = ETSModel(series, **kwargs).fit(disp=False)
                if np.isfinite(res.aicc) and res.aicc < best_aicc:
                    best, best_aicc, best_cfg = res, res.aicc, kwargs
            except Exception:
                continue
        if best is None:
            best = ETSModel(series, error="add", trend="add", seasonal="add", seasonal_periods=5).fit(disp=False)
            best_cfg = {"error": "add", "trend": "add", "seasonal": "add", "seasonal_periods": 5}
        self._result = best
        self.selected_config = best_cfg
        self._resid_std = float(np.std(np.asarray(best.resid, dtype=float)))
        return self

    def predict(self, steps: int) -> dict:
        forecast = self._result.forecast(steps)
        margin = 1.96 * self._resid_std
        mean = forecast.to_numpy()
        return {
            "dates": [d.strftime("%Y-%m-%d") for d in forecast.index],
            "mean": mean.tolist(),
            "lower": (mean - margin).tolist(),
            "upper": (mean + margin).tolist(),
        }


class OptimizedProphetModel:
    """Prophet tuned over changepoint_prior_scale x yearly_seasonality,
    model-selected on the last 30 days of the training window (held out
    from the tuning fits, then the winning config is refit on the full
    training window for the actual forecast)."""

    name = "prophet_optimized"
    GRID_CPS = [0.001, 0.01, 0.1, 0.5]
    GRID_YEARLY = [False, True]
    VAL_LEN = 30
    DEFAULT_CFG = (0.05, True)  # Prophet's own default changepoint_prior_scale

    def __init__(self):
        self._model = None
        self._last_date = None
        self._freq = None
        self.selected_config = None

    def _fit_one(self, train_df: pd.DataFrame, cps: float, yearly: bool) -> Prophet:
        m = Prophet(
            daily_seasonality=False, weekly_seasonality=True,
            yearly_seasonality=yearly, changepoint_prior_scale=cps,
        )
        m.fit(train_df)
        return m

    def fit(self, series: pd.Series):
        freq = series.index.freq or "B"
        best_cfg = None
        if len(series) > self.VAL_LEN * 2:
            train2, val = series.iloc[:-self.VAL_LEN], series.iloc[-self.VAL_LEN:]
            train2_df = pd.DataFrame({"ds": train2.index, "y": train2.to_numpy()})
            best_rmse = np.inf
            for cps, yearly in itertools.product(self.GRID_CPS, self.GRID_YEARLY):
                try:
                    m = self._fit_one(train2_df, cps, yearly)
                    future = pd.date_range(train2.index[-1], periods=self.VAL_LEN + 1, freq=freq)[1:]
                    fc = m.predict(pd.DataFrame({"ds": future}))
                    pred = fc["yhat"].to_numpy()[: len(val)]
                    rmse = float(np.sqrt(np.mean((pred - val.to_numpy()) ** 2)))
                    if rmse < best_rmse:
                        best_rmse, best_cfg = rmse, (cps, yearly)
                except Exception:
                    continue
        self.selected_config = best_cfg or self.DEFAULT_CFG
        cps, yearly = self.selected_config

        self._last_date = series.index[-1]
        self._freq = freq
        df = pd.DataFrame({"ds": series.index, "y": series.to_numpy()})
        self._model = self._fit_one(df, cps, yearly)
        return self

    def predict(self, steps: int) -> dict:
        future_dates = pd.date_range(self._last_date, periods=steps + 1, freq=self._freq)[1:]
        forecast = self._model.predict(pd.DataFrame({"ds": future_dates}))
        return {
            "dates": [d.strftime("%Y-%m-%d") for d in future_dates],
            "mean": forecast["yhat"].to_numpy().tolist(),
            "lower": forecast["yhat_lower"].to_numpy().tolist(),
            "upper": forecast["yhat_upper"].to_numpy().tolist(),
        }


# ---------------------------------------------------------------------------
# Tier D — ablation (production Prophet minus yearly seasonality)
# ---------------------------------------------------------------------------
class ProphetNoYearly(ProductionProphetModel):
    """Identical to the production ProphetModel except yearly_seasonality
    is forced off. predict() is inherited unchanged from the production
    class."""

    name = "prophet_no_yearly"

    def fit(self, series: pd.Series):
        self._last_date = series.index[-1]
        self._freq = series.index.freq or "B"
        df = pd.DataFrame({"ds": series.index, "y": series.to_numpy()})
        self._model = Prophet(daily_seasonality=False, weekly_seasonality=True, yearly_seasonality=False)
        self._model.fit(df)
        return self
