"""One-off diagnostic: does cmdstanpy's L-BFGS optimizer actually run, or
does it fall back to Newton, for a single Prophet fit on a fixed
ticker/origin? Prints the optimizer actually used and the forecast."""
import logging
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import fetch_series  # noqa: E402

logging.basicConfig(level=logging.DEBUG)

import pandas as pd  # noqa: E402
from prophet import Prophet  # noqa: E402

TICKER = "0001.HK"
ORIGIN_IDX = 1224  # same as the "full-window" timing check earlier in this session

series = fetch_series(TICKER, period_days=5 * 365 + 10)
train = series.iloc[:ORIGIN_IDX]
df = pd.DataFrame({"ds": train.index, "y": train.to_numpy()})

print(f"PID={os.getpid()} CWD={os.getcwd()}")
print(f"train n={len(train)} last_date={train.index[-1]}")

m = Prophet(daily_seasonality=False, weekly_seasonality=True, yearly_seasonality=True)
m.fit(df)

print("params keys:", list(m.params.keys()) if hasattr(m, "params") else None)
future = pd.date_range(train.index[-1], periods=31, freq="B")[1:]
fc = m.predict(pd.DataFrame({"ds": future}))
print("first 5 yhat:", fc["yhat"].to_numpy()[:5].tolist())
print("last 5 yhat:", fc["yhat"].to_numpy()[-5:].tolist())
