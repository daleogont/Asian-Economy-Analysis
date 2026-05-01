const pool = require("./db");

// Returns latest price + 5-day return for every ticker in one query
async function getAllLatestPrices() {
  const { rows } = await pool.query(`
    WITH latest AS (
      SELECT DISTINCT ON (ticker) ticker, close, date, currency
      FROM daily_prices
      ORDER BY ticker, date DESC
    ),
    week_ago AS (
      SELECT DISTINCT ON (dp.ticker) dp.ticker, dp.close AS week_close
      FROM daily_prices dp
      JOIN latest l USING (ticker)
      WHERE dp.date <= l.date - INTERVAL '7 days'
      ORDER BY dp.ticker, dp.date DESC
    )
    SELECT
      c.ticker, c.name, c.country, c.sector, c.exchange,
      l.close                                              AS price,
      l.currency,
      CASE WHEN wa.week_close > 0
        THEN ROUND(((l.close - wa.week_close) / wa.week_close * 100)::numeric, 2)
        ELSE NULL
      END                                                  AS weekly_return
    FROM companies c
    LEFT JOIN latest  l  USING (ticker)
    LEFT JOIN week_ago wa USING (ticker)
  `);
  // Return as map: ticker → row
  const map = {};
  for (const r of rows) map[r.ticker] = r;
  return map;
}

// Returns OHLCV history for one ticker
async function getTickerHistory(ticker, days = 365) {
  const { rows } = await pool.query(
    `SELECT date, open, high, low, close, volume, currency
     FROM daily_prices
     WHERE ticker = $1
       AND date >= CURRENT_DATE - ($2 || ' days')::interval
     ORDER BY date ASC`,
    [ticker, days]
  );
  return rows;
}

// Returns the single latest price row for one ticker
async function getLatestPrice(ticker) {
  const { rows } = await pool.query(
    `SELECT close, currency, date
     FROM daily_prices
     WHERE ticker = $1
     ORDER BY date DESC LIMIT 1`,
    [ticker]
  );
  return rows[0] ?? null;
}

module.exports = { getAllLatestPrices, getTickerHistory, getLatestPrice };
