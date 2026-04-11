const { getAllLatestPrices } = require("../utils/stockQueries");

const getCompanies = async (req, res) => {
  try {
    const prices = await getAllLatestPrices();

    const results = Object.values(prices)
      .filter((p) => p.price != null)
      .map((p) => ({
        name:         p.name,
        ticker:       p.ticker,
        country:      p.country,
        sector:       p.sector,
        exchange:     p.exchange,
        stockPrice:   Number(p.price),
        weeklyReturn: p.weekly_return !== null ? Number(p.weekly_return) : null,
        currency:     p.currency,
        marketCap:    null,
      }));

    res.json(results);
  } catch (err) {
    console.error("companyController error:", err.message);
    res.status(500).json({ error: "Failed to fetch company data" });
  }
};

module.exports = { getCompanies };
