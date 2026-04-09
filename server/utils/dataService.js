const axios  = require("axios");
const { convertToUSD }        = require("./currencyService");
const { getCached, setCached } = require("./cacheStore");
const { TWELVE_DATA_KEY }      = require("../config");

const FETCH_INTERVAL_MS = 8000; // 7.5 req/min — within Twelve Data free tier limit

const YAHOO_HEADERS = {
  "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
  Accept: "application/json, text/plain, */*",
  "Accept-Language": "en-US,en;q=0.9",
  Referer: "https://finance.yahoo.com/",
};

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

let _yahooCoolUntil      = 0;
let _twelveDataCoolUntil = 0;

// Converts Yahoo-style tickers (e.g. "8306.T") to Twelve Data format ("8306:TSE")
const SUFFIX_TO_EXCHANGE = {
  ".TWO": "TPEX",
  ".TW":  "TWSE",
  ".T":   "TSE",
  ".HK":  "HKEX",
  ".KS":  "KRX",
  ".NS":  "NSE",
  ".SS":  "SSE",
  ".SZ":  "SZSE",
  ".BK":  "SET",
  ".SI":  "SGX",
  ".JK":  "IDX",
  ".KL":  "KLSE",
  ".SR":  "TADAWUL",
};

function toTwelveSymbol(yahooTicker) {
  for (const [suffix, exchange] of Object.entries(SUFFIX_TO_EXCHANGE)) {
    if (yahooTicker.endsWith(suffix)) {
      return `${yahooTicker.slice(0, -suffix.length)}:${exchange}`;
    }
  }
  return yahooTicker; // US / no suffix — pass through
}

async function fetchFromYahoo(ticker) {
  const hosts = ["query1.finance.yahoo.com", "query2.finance.yahoo.com"];
  const host  = hosts[Math.floor(Math.random() * hosts.length)];
  const url   = `https://${host}/v8/finance/chart/${encodeURIComponent(ticker)}?interval=1d&range=5d`;

  const resp   = await axios.get(url, { headers: YAHOO_HEADERS, timeout: 12000 });
  const result = resp.data?.chart?.result?.[0];
  if (!result) return null;

  const meta         = result.meta;
  const closes       = result.indicators?.quote?.[0]?.close ?? [];
  const currentPrice = meta.regularMarketPrice;
  const prevClose    = meta.chartPreviousClose;
  const currency     = meta.currency || "USD";

  if (currentPrice == null || prevClose == null) return null;

  const validCloses  = closes.filter((c) => c != null);
  const firstClose   = validCloses.length > 1 ? validCloses[0] : prevClose;
  const weeklyReturn = firstClose ? ((currentPrice - firstClose) / firstClose) * 100 : 0;

  return {
    ticker,
    stockPrice:    convertToUSD(currentPrice, currency),
    previousClose: convertToUSD(prevClose, currency),
    weeklyReturn:  Number(weeklyReturn.toFixed(2)),
    marketCap: null, peRatio: null, currency, source: "yahoo",
  };
}

async function fetchFromTwelveData(ticker) {
  if (!TWELVE_DATA_KEY || Date.now() < _twelveDataCoolUntil) return null;

  try {
    const symbol = toTwelveSymbol(ticker);
    const resp = await axios.get(
      `https://api.twelvedata.com/quote?symbol=${encodeURIComponent(symbol)}&apikey=${TWELVE_DATA_KEY}`,
      { timeout: 12000 }
    );
    const d = resp.data;
    if (!d || d.status === "error" || !d.close) return null;

    const currentPrice = parseFloat(d.close);
    const prevClose    = parseFloat(d.previous_close);
    const currency     = d.currency || "USD";
    if (isNaN(currentPrice) || isNaN(prevClose)) return null;

    return {
      ticker,
      stockPrice:    convertToUSD(currentPrice, currency),
      previousClose: convertToUSD(prevClose, currency),
      weeklyReturn:  Number((parseFloat(d.percent_change) || 0).toFixed(2)),
      marketCap: null, peRatio: null, currency, source: "twelve",
    };
  } catch (err) {
    if (err.response?.status === 429) {
      _twelveDataCoolUntil = Date.now() + 2 * 60 * 1000;
      console.warn("⏸️  Twelve Data 429 — cooling down 2 min");
    }
    return null;
  }
}

// Tries Yahoo then Twelve Data. Returns null if both fail.
async function fetchLive(ticker) {
  if (Date.now() >= _yahooCoolUntil) {
    try {
      const data = await fetchFromYahoo(ticker);
      if (data) return data;
    } catch (err) {
      if (err.response?.status === 429) {
        _yahooCoolUntil = Date.now() + 2 * 60 * 1000;
        console.warn("⏸️  Yahoo 429 — switching to Twelve Data for 2 min");
      } else {
        console.warn(`⚠️  Yahoo failed for ${ticker}: ${err.message?.slice(0, 70)}`);
      }
    }
  }
  return fetchFromTwelveData(ticker);
}

const _queue = [];
let _running = false;

async function runQueue() {
  if (_running) return;
  _running = true;

  while (_queue.length > 0) {
    const ticker   = _queue.shift();
    const existing = getCached(ticker);
    if (existing && !existing.isSeed) { continue; }

    try {
      const data = await fetchLive(ticker);
      if (data) {
        setCached(ticker, data);
        const tag  = data.source === "twelve" ? "📊 [12D]" : "✅";
        const sign = data.weeklyReturn >= 0 ? "+" : "";
        console.log(`${tag} ${ticker} — ${data.currency} ${data.stockPrice.toFixed(4)} (${sign}${data.weeklyReturn}%)`);
      } else {
        console.warn(`⚠️  ${ticker}: no live data`);
      }
    } catch (err) {
      console.error(`❌ ${ticker}: ${err.message?.slice(0, 80)}`);
    }

    await sleep(FETCH_INTERVAL_MS);
  }

  _running = false;
  console.log("✅ Background fetch complete.");
}

// Cache-only lookup — live fetches happen only via the background queue.
const fetchCompanyData = async (ticker) => getCached(ticker) ?? null;

// Queues all tickers that have no live data yet (seed-only or missing).
const prewarmCache = async (companies) => {
  const unique  = [...new Map(companies.map((c) => [c.ticker, c])).values()];
  const toFetch = unique.filter((c) => { const d = getCached(c.ticker); return !d || d.isSeed; });

  if (toFetch.length === 0) {
    console.log("📦 All tickers have live data — skipping pre-warm");
    return;
  }

  const mins = Math.ceil((toFetch.length * FETCH_INTERVAL_MS) / 60000);
  console.log(`\n🔄 Queuing ${toFetch.length} tickers (≈${mins} min)...\n`);
  for (const { ticker } of toFetch) _queue.push(ticker);
  runQueue();
};

const scheduleCrumbFetch = () => {};

module.exports = { fetchCompanyData, prewarmCache, scheduleCrumbFetch };
