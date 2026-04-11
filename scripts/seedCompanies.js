require("dotenv").config();
const pool      = require("../server/utils/db");
const companies = require("../data/realCompanies.json");

async function seed() {
  const client = await pool.connect();
  try {
    let inserted = 0, skipped = 0;
    for (const { ticker, name, country, sector, exchange } of companies) {
      const res = await client.query(
        `INSERT INTO companies (ticker, name, country, sector, exchange)
         VALUES ($1, $2, $3, $4, $5)
         ON CONFLICT (ticker) DO NOTHING`,
        [ticker, name, country, sector, exchange]
      );
      res.rowCount > 0 ? inserted++ : skipped++;
    }
    console.log(`✅ Companies seeded — inserted: ${inserted}, skipped: ${skipped}`);
  } finally {
    client.release();
    await pool.end();
  }
}

seed().catch((err) => { console.error(err); process.exit(1); });
