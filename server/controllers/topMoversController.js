const { getAllLatestPrices } = require("../utils/stockQueries");

const getTopMovers = async (req, res) => {
  try {
    const count     = Math.min(parseInt(req.query.count) || 5, 20);
    const direction = req.query.direction === "down" ? "down" : "up";
    const prices    = await getAllLatestPrices();

    const valid = Object.values(prices)
      .filter((p) => p.price != null && p.weekly_return !== null)
      .map((p) => ({
        name:         p.name,
        ticker:       p.ticker,
        country:      p.country,
        sector:       p.sector,
        stockPrice:   Number(p.price),
        weeklyReturn: Number(p.weekly_return),
        currency:     p.currency,
      }));

    valid.sort((a, b) =>
      direction === "down"
        ? a.weeklyReturn - b.weeklyReturn
        : b.weeklyReturn - a.weeklyReturn
    );

    res.json(valid.slice(0, count));
  } catch (err) {
    console.error("topMoversController error:", err.message);
    res.status(500).json({ error: "Failed to get top movers" });
  }
};

module.exports = { getTopMovers };
