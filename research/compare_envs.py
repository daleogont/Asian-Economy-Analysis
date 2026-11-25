"""
One-off: fit the 4 production (Tier A) models on an identical ticker+origin
slice and dump their forecasts as JSON, so the exact same invocation can be
run once on the host (research/.venv) and once inside the python-api
container, and the two JSON outputs diffed externally. Not part of the
regular pipeline -- a library-version-parity check only.

Usage: python research/compare_envs.py <ticker> <origin_idx>
"""
import json
import os
import sys

import pandas as pd
import sqlalchemy as sa

TICKER = sys.argv[1] if len(sys.argv) > 1 else "0388.HK"
ORIGIN_IDX = int(sys.argv[2]) if len(sys.argv) > 2 else 1044
PERIOD_DAYS = 5 * 365 + 10

DATABASE_URL = os.environ.get("DATABASE_URL") or os.environ.get(
    "RESEARCH_DATABASE_URL", "postgresql://admin:secret@localhost:5432/asianmarkets"
)
engine = sa.create_engine(DATABASE_URL, poolclass=sa.pool.NullPool)

df = pd.read_sql(
    sa.text(
        f"""
        SELECT date, close FROM daily_prices
        WHERE ticker = :ticker
          AND date >= CURRENT_DATE - INTERVAL '{PERIOD_DAYS} days'
          AND close IS NOT NULL
        ORDER BY date ASC
        """
    ),
    engine,
    params={"ticker": TICKER},
)
df["date"] = pd.to_datetime(df["date"])
df["close"] = df["close"].astype(float)
df = df.set_index("date").asfreq("B").ffill()
series = df["close"]
train = series.iloc[:ORIGIN_IDX]

if os.path.exists("/app/app"):
    sys.path.insert(0, "/app")
else:
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "analytics"))

from app.models.arima import ArimaModel  # noqa: E402
from app.models.ets import EtsModel  # noqa: E402
from app.models.prophet import ProphetModel  # noqa: E402
from app.models.sarima import SarimaModel  # noqa: E402

out = {}
for name, cls in [("arima", ArimaModel), ("ets", EtsModel), ("sarima", SarimaModel), ("prophet", ProphetModel)]:
    m = cls()
    m.fit(train)
    fc = m.predict(30)
    out[name] = fc["mean"]

print(json.dumps({"n_train": len(train), "last_date": str(train.index[-1].date()), "forecasts": out}))
