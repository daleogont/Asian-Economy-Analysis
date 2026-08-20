import os
import time
import tracemalloc

import numpy as np
import pandas as pd
import psutil

_process = psutil.Process(os.getpid())


class BaseForecastModel:
    """Every forecasting model subclasses this and implements fit/predict.

    `run()` wraps fit+predict with CE performance metrics (latency, train
    time, peak memory) and RMSE/MAE computed on a holdout split, so no
    individual model has to reimplement that measurement logic.
    """

    name = "base"

    def fit(self, series: pd.Series):
        raise NotImplementedError

    def predict(self, steps: int) -> dict:
        """Return {"dates": [...], "mean": [...], "lower": [...], "upper": [...]}."""
        raise NotImplementedError

    def _holdout_rmse_mae(self, series: pd.Series, holdout_frac: float):
        split = int(len(series) * (1 - holdout_frac))
        split = min(max(split, 1), len(series) - 1) if len(series) > 1 else 0
        train, holdout = series.iloc[:split], series.iloc[split:]

        if len(train) < 2 or len(holdout) == 0:
            return None, None

        try:
            # Subclasses that need extra constructor config (e.g. enriched
            # features) can set self._init_kwargs so the holdout clone is
            # configured identically to the real model, not reset to
            # defaults. Models with no-arg constructors (arima/ets/sarima/
            # prophet) never set this, so type(self)() behavior is unchanged.
            init_kwargs = getattr(self, "_init_kwargs", {})
            holdout_model = type(self)(**init_kwargs)
            holdout_model.fit(train)
            pred = holdout_model.predict(len(holdout))
            actual = holdout.to_numpy()
            predicted = np.asarray(pred["mean"][: len(actual)], dtype=float)
            if len(predicted) != len(actual):
                return None, None
            rmse = float(np.sqrt(np.mean((predicted - actual) ** 2)))
            mae = float(np.mean(np.abs(predicted - actual)))
            return rmse, mae
        except Exception:
            return None, None

    def run(self, series: pd.Series, steps: int, holdout_frac: float = 0.2) -> dict:
        rmse, mae = self._holdout_rmse_mae(series, holdout_frac)

        tracemalloc.start()
        rss_before = _process.memory_info().rss

        train_start = time.perf_counter()
        self.fit(series)
        train_time_s = time.perf_counter() - train_start

        infer_start = time.perf_counter()
        forecast = self.predict(steps)
        inference_latency_ms = (time.perf_counter() - infer_start) * 1000

        _, traced_peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        rss_delta = max(_process.memory_info().rss - rss_before, 0)
        memory_mb = max(traced_peak, rss_delta) / (1024 * 1024)

        return {
            "model_name": self.name,
            "forecast": forecast,
            "metrics": {
                "inference_latency_ms": round(inference_latency_ms, 3),
                "train_time_s": round(train_time_s, 4),
                "memory_mb": round(memory_mb, 3),
                "model_name": self.name,
                "rmse": round(rmse, 4) if rmse is not None else None,
                "mae": round(mae, 4) if mae is not None else None,
            },
        }
