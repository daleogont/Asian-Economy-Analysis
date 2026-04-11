const { getAllLatestPrices } = require("../utils/stockQueries");

const getSectorLeaders = async (req, res) => {
  try {
    const prices  = await getAllLatestPrices();
    const leaders = {};

    for (const p of Object.values(prices)) {
      if (!p.price) continue;

      const price = Number(p.price);
      if (!leaders[p.sector] || price > leaders[p.sector].stockPrice) {
        leaders[p.sector] = {
          name:         p.name,
          ticker:       p.ticker,
          country:      p.country,
          sector:       p.sector,
          exchange:     p.exchange,
          stockPrice:   price,
          weeklyReturn: p.weekly_return !== null ? Number(p.weekly_return) : null,
          currency:     p.currency,
        };
      }
    }

    res.json(Object.values(leaders));
  } catch (err) {
    console.error("sectorLeadersController error:", err.message);
    res.status(500).json({ error: "Failed to get sector leaders" });
  }
};

module.exports = { getSectorLeaders };
