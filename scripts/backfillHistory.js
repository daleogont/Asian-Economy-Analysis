// One-time backfill: collectHistory.js/deltaFetch.js only look at MAX(date)
// to decide whether a ticker "needs fetching," so tickers already current
// through today never get their pre-2024 history filled in even though the
// fetch window was extended to 5 years. This script instead looks at
// MIN(date) and pulls the missing older history for any ticker that's short
// of the full 5-year window.
require("dotenv").config();
const axios = require("axios");
const pool  = require("../server/utils/db");
const { TWELVE_DATA_KEY } = require("../server/config");

const INTERVAL_MS = 8000;
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

const YAHOO_HEADERS = {
  "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
  Accept: "*/*",
};

const SUFFIX_TO_EXCHANGE = {
  ".TWO": "TPEX", ".TW": "TWSE", ".T": "TSE", ".HK": "HKEX",
  ".KS": "KRX", ".NS": "NSE", ".SS": "SSE", ".SZ": "SZSE",
  ".BK": "SET", ".SI": "SGX", ".JK": "IDX", ".KL": "KLSE",
  ".SR": "TADAWUL", ".VN": "HOSE", ".PS": "PSE", ".AE": "ADX", ".KA": "PSX",
};

function toTwelveSymbol(ticker) {
  for (const [suffix, exchange] of Object.entries(SUFFIX_TO_EXCHANGE)) {
    if (ticker.endsWith(suffix)) return `${ticker.slice(0, -suffix.length)}:${exchange}`;
  }
  return ticker;
}

let yahooCoolUntil = 0;

async function fetchFromYahoo(ticker) {
  if (Date.now() < yahooCoolUntil) return null;
  const hosts = ["query1.finance.yahoo.com", "query2.finance.yahoo.com"];
  const host  = hosts[Math.floor(Math.random() * hosts.length)];
  const url   = `https://${host}/v8/finance/chart/${encodeURIComponent(ticker)}?interval=1d&range=5y`;

  const resp   = await axios.get(url, { headers: YAHOO_HEADERS, timeout: 15000 });
  const result = resp.data?.chart?.result?.[0];
  if (!result) return null;

  const timestamps = result.timestamp ?? [];
  const quote      = result.indicators?.quote?.[0] ?? {};
  const currency   = result.meta?.currency ?? "USD";

  return timestamps.map((ts, i) => ({
    date: new Date(ts * 1000), open: quote.open?.[i] ?? null,
    high: quote.high?.[i] ?? null, low: quote.low?.[i] ?? null,
    close: quote.close?.[i] ?? null, volume: quote.volume?.[i] ?? null, currency,
  })).filter((r) => r.close != null);
}

async function fetchFromTwelveData(ticker) {
  if (!TWELVE_DATA_KEY) return null;
  const symbol    = toTwelveSymbol(ticker);
  const startDate = new Date(Date.now() - 1825 * 86400000).toISOString().split("T")[0];
  const url = `https://api.twelvedata.com/time_series?symbol=${encodeURIComponent(symbol)}&interval=1day&start_date=${startDate}&outputsize=1825&apikey=${TWELVE_DATA_KEY}`;

  const resp = await axios.get(url, { timeout: 15000 });
  const data = resp.data;
  if (!data || data.status === "error" || !Array.isArray(data.values)) return null;

  const currency = data.meta?.currency ?? "USD";
  return data.values.map((v) => ({
    date: new Date(v.datetime), open: parseFloat(v.open) || null,
    high: parseFloat(v.high) || null, low: parseFloat(v.low) || null,
    close: parseFloat(v.close) || null, volume: parseInt(v.volume) || null, currency,
  })).filter((r) => r.close != null);
}

async function fetchHistory(ticker) {
  try {
    const rows = await fetchFromYahoo(ticker);
    if (rows && rows.length > 0) return { rows, source: "yahoo" };
  } catch (err) {
    if (err.response?.status === 429) {
      yahooCoolUntil = Date.now() + 3 * 60 * 1000;
      console.warn("⏸️  Yahoo 429 — cooling 3 min, switching to Twelve Data");
    }
  }

  const rows = await fetchFromTwelveData(ticker);
  return rows ? { rows, source: "twelve" } : null;
}

async function getEarliestDates(client) {
  const res = await client.query(
    "SELECT ticker, MIN(date) AS earliest_date FROM daily_prices GROUP BY ticker"
  );
  const map = {};
  for (const row of res.rows) map[row.ticker] = new Date(row.earliest_date);
  return map;
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

async function run() {
  const client = await pool.connect();
  try {
    const { rows: companies } = await client.query("SELECT ticker FROM companies ORDER BY ticker");
    const earliest = await getEarliestDates(client);

    const today       = new Date(); today.setHours(0, 0, 0, 0);
    const fiveYearsAgo = new Date(today.getTime() - 1825 * 86400000);
    // 30-day grace period: tickers already essentially at the 5-year mark
    // (off by a few trading days due to holidays/listing dates) don't need
    // a wasted re-fetch.
    const cutoffWithBuffer = new Date(fiveYearsAgo.getTime() + 30 * 86400000);

    const toBackfill = companies.filter(({ ticker }) => {
      const min = earliest[ticker];
      return !min || min > cutoffWithBuffer;
    });

    console.log(`\n📜 ${companies.length} tickers — ${toBackfill.length} need older history backfilled`);
    console.log(`⏱  Estimated time: ~${Math.ceil(toBackfill.length * INTERVAL_MS / 60000)} min\n`);

    let done = 0, totalRows = 0;
    for (const { ticker } of toBackfill) {
      done++;
      const earliestStr = earliest[ticker]
        ? earliest[ticker].toISOString().split("T")[0]
        : "no data yet";

      try {
        const result = await fetchHistory(ticker);
        if (result) {
          const inserted = await insertRows(client, ticker, result.rows);
          totalRows += inserted;
          const tag = result.source === "twelve" ? "[12D]" : "✅";
          console.log(`ticker ${done}/${toBackfill.length}: ${ticker} — earliest date was ${earliestStr}, fetching older history... ${tag} +${inserted} rows`);
        } else {
          console.warn(`ticker ${done}/${toBackfill.length}: ${ticker} — earliest date was ${earliestStr}, fetching older history... ⚠️  no data`);
        }
      } catch (err) {
        console.warn(`ticker ${done}/${toBackfill.length}: ${ticker} — earliest date was ${earliestStr}, fetching older history... ⚠️  ${err.message?.slice(0, 60)}`);
      }

      if (done % 50 === 0 || done === toBackfill.length) {
        console.log(`\n📊 Progress: ${done}/${toBackfill.length} tickers processed, ${totalRows} rows added so far\n`);
      }

      if (done < toBackfill.length) await sleep(INTERVAL_MS);
    }

    const { rows: [{ min, max, count }] } = await client.query(
      "SELECT MIN(date), MAX(date), COUNT(*) FROM daily_prices"
    );
    console.log(`\n✅ Backfill done. ${totalRows} new rows added.`);
    console.log(`   daily_prices: MIN(date)=${min}, MAX(date)=${max}, COUNT=${count}`);
  } finally {
    client.release();
    await pool.end();
  }
}

run().catch((err) => { console.error(err); process.exit(1); });
