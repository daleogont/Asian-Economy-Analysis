const axios = require("axios");
const pool  = require("./db");

const INTERVAL_MS = 8000;
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

const HEADERS = {
  "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
  Accept: "application/json, text/plain, */*",
  "Accept-Language": "en-US,en;q=0.9",
  Referer: "https://finance.yahoo.com/",
};

// Fetch daily OHLCV from Yahoo Finance for a given period1 (JS Date) to today
async function fetchHistory(ticker, period1) {
  const hosts  = ["query1.finance.yahoo.com", "query2.finance.yahoo.com"];
  const host   = hosts[Math.floor(Math.random() * hosts.length)];
  const p1     = Math.floor(period1.getTime() / 1000);
  const p2     = Math.floor(Date.now() / 1000);
  const url    = `https://${host}/v8/finance/chart/${encodeURIComponent(ticker)}?interval=1d&period1=${p1}&period2=${p2}`;

  const resp   = await axios.get(url, { headers: HEADERS, timeout: 15000 });
  const result = resp.data?.chart?.result?.[0];
  if (!result) return [];

  const timestamps = result.timestamp ?? [];
  const quote      = result.indicators?.quote?.[0] ?? {};
  const currency   = result.meta?.currency ?? "USD";

  return timestamps.map((ts, i) => ({
    date:     new Date(ts * 1000),
    open:     quote.open?.[i]   ?? null,
    high:     quote.high?.[i]   ?? null,
    low:      quote.low?.[i]    ?? null,
    close:    quote.close?.[i]  ?? null,
    volume:   quote.volume?.[i] ?? null,
    currency,
  })).filter((r) => r.close != null);
}

async function insertRows(client, ticker, rows) {
  let count = 0;
  for (const r of rows) {
    const res = await client.query(
      `INSERT INTO daily_prices (ticker, date, open, high, low, close, volume, currency)
       VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
       ON CONFLICT (ticker, date) DO NOTHING`,
      [ticker, r.date, r.open, r.high, r.low, r.close, r.volume, r.currency]
    );
    count += res.rowCount;
  }
  return count;
}

async function runDeltaFetch() {
  const client = await pool.connect();
  try {
    const { rows: allCompanies } = await client.query("SELECT ticker FROM companies");

    const res = await client.query(
      "SELECT ticker, MAX(date) AS last_date FROM daily_prices GROUP BY ticker"
    );
    const latest = {};
    for (const row of res.rows) latest[row.ticker] = new Date(row.last_date);

    const today     = new Date(); today.setHours(0, 0, 0, 0);
    const yesterday = new Date(today - 86400000);
    const twoYearsAgo = new Date(Date.now() - 730 * 86400000);

    const toUpdate = allCompanies.filter((c) => {
      const last = latest[c.ticker];
      return !last || last < yesterday;
    });

    if (toUpdate.length === 0) {
      console.log("📦 All tickers up to date — skipping delta fetch");
      return;
    }

    console.log(`\n🔄 Delta fetch: ${toUpdate.length} tickers need updating\n`);
    let totalRows = 0;

    for (let i = 0; i < toUpdate.length; i++) {
      const { ticker } = toUpdate[i];
      const fromDate   = latest[ticker]
        ? new Date(latest[ticker].getTime() + 86400000)
        : twoYearsAgo;

      try {
        const rows     = await fetchHistory(ticker, fromDate);
        const inserted = await insertRows(client, ticker, rows);
        totalRows += inserted;
        if (inserted > 0) console.log(`✅ ${ticker} +${inserted} rows`);
      } catch (err) {
        console.warn(`⚠️  Delta ${ticker}: ${err.message?.slice(0, 70)}`);
      }

      if (i < toUpdate.length - 1) await sleep(INTERVAL_MS);
    }

    console.log(`\n✅ Delta fetch done — ${totalRows} new rows added`);
  } finally {
    client.release();
  }
}

module.exports = { runDeltaFetch };
