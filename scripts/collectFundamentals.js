require("dotenv").config();
const axios = require("axios");
const pool  = require("../server/utils/db");

const INTERVAL_MS      = 1000;
const FETCH_TIMEOUT_MS = 20000;
const PYTHON_API_URL   = process.env.PYTHON_API_URL || "http://localhost:8000";
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

// Fundamentals are fetched by the python-api container (via yfinance) rather
// than spawning a local python3 subprocess, so yfinance only needs to be
// installed there — not on whatever host runs this script.
async function fetchFundamentals(ticker) {
  try {
    const { data } = await axios.get(
      `${PYTHON_API_URL}/internal/fundamentals/${encodeURIComponent(ticker)}`,
      { timeout: FETCH_TIMEOUT_MS }
    );
    if (data.error) return { error: data.error };
    return data;
  } catch (err) {
    const message = err.response?.data?.detail ?? err.message;
    return { error: message?.slice(0, 120) ?? "unknown error" };
  }
}

async function upsertFundamentals(client, ticker, f) {
  await client.query(
    `INSERT INTO fundamentals (ticker, pe_ratio, eps, dividend_yield, beta, market_cap, fetched_at)
     VALUES ($1, $2, $3, $4, $5, $6, NOW())
     ON CONFLICT (ticker) DO UPDATE SET
       pe_ratio       = EXCLUDED.pe_ratio,
       eps            = EXCLUDED.eps,
       dividend_yield = EXCLUDED.dividend_yield,
       beta           = EXCLUDED.beta,
       market_cap     = EXCLUDED.market_cap,
       fetched_at     = NOW()`,
    [
      ticker,
      f.pe_ratio ?? null,
      f.eps ?? null,
      f.dividend_yield ?? null,
      f.beta ?? null,
      f.market_cap ?? null,
    ]
  );
}

async function run() {
  const client = await pool.connect();
  try {
    const { rows: companies } = await client.query("SELECT ticker FROM companies ORDER BY ticker");

    console.log(`\n📊 ${companies.length} tickers — fetching fundamentals via yfinance\n`);

    let done = 0, ok = 0, failed = 0;
    for (const { ticker } of companies) {
      done++;
      const f = await fetchFundamentals(ticker);

      if (f.error) {
        failed++;
        console.warn(`[${done}/${companies.length}] ⚠️  ${ticker}: ${f.error}`);
      } else {
        await upsertFundamentals(client, ticker, f);
        ok++;
        const pe   = f.pe_ratio != null ? f.pe_ratio.toFixed?.(1) ?? f.pe_ratio : "—";
        const beta = f.beta != null ? f.beta.toFixed?.(1) ?? f.beta : "—";
        console.log(`ticker ${done}/${companies.length}: ${ticker} — pe=${pe} beta=${beta}`);
      }

      if (done < companies.length) await sleep(INTERVAL_MS);
    }

    console.log(`\n✅ Done. ${ok} updated, ${failed} failed/missing.`);
  } finally {
    client.release();
    await pool.end();
  }
}

run().catch((err) => { console.error(err); process.exit(1); });
