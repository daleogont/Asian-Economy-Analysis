"""
STEP 1 — export the benchmark tickers' daily closes to a CSV snapshot and
record provenance (date range, row counts, sha256) in manifest.json.

Usage: research/.venv/bin/python research/snapshot.py
"""
import json
import os
import sys
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import PAPER_TICKERS, fetch_df, sha256_file  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(HERE, "data")
PERIOD_DAYS = 5 * 365  # full available window; rolling_benchmark.py slices per origin


def main():
    today_str = date.today().isoformat()
    csv_path = os.path.join(DATA_DIR, f"snapshot_{today_str}.csv")

    df = fetch_df(
        f"""
        SELECT dp.ticker, c.country, dp.date, dp.close
        FROM daily_prices dp
        JOIN companies c ON c.ticker = dp.ticker
        WHERE dp.ticker = ANY(:t)
          AND dp.date >= CURRENT_DATE - INTERVAL '{PERIOD_DAYS} days'
          AND dp.close IS NOT NULL
        ORDER BY dp.ticker, dp.date
        """,
        {"t": PAPER_TICKERS},
    )
    df.to_csv(csv_path, index=False)

    per_ticker = (
        df.groupby("ticker")["date"]
        .agg(min_date="min", max_date="max", row_count="count")
        .reset_index()
    )
    missing = sorted(set(PAPER_TICKERS) - set(df["ticker"].unique()))

    manifest = {
        "generated_at": today_str,
        "csv_file": os.path.basename(csv_path),
        "csv_sha256": sha256_file(csv_path),
        "n_tickers_requested": len(PAPER_TICKERS),
        "n_tickers_found": len(per_ticker),
        "missing_tickers": missing,
        "global_min_date": str(df["date"].min()) if len(df) else None,
        "global_max_date": str(df["date"].max()) if len(df) else None,
        "db_staleness_note": (
            "daily_prices MAX(date) lagged ~2 months behind wall-clock "
            "'today' at snapshot time; see README.md for detail."
        ),
        "per_ticker": per_ticker.assign(
            min_date=per_ticker["min_date"].astype(str),
            max_date=per_ticker["max_date"].astype(str),
        ).to_dict(orient="records"),
    }

    manifest_path = os.path.join(DATA_DIR, "manifest.json")
    with open(manifest_path, "w") as f:
        json.dump(manifest, f, indent=2)

    print(f"Wrote {csv_path} ({len(df)} rows, {len(per_ticker)} tickers)")
    print(f"Wrote {manifest_path}")
    if missing:
        print(f"WARNING missing tickers: {missing}")


if __name__ == "__main__":
    main()
