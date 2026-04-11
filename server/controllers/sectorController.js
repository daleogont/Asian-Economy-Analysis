const { getAllLatestPrices } = require("../utils/stockQueries");

const getSectors = async (req, res) => {
  try {
    const prices = await getAllLatestPrices();
    const map    = {};

    for (const p of Object.values(prices)) {
      if (!p.price) continue;

      if (!map[p.sector]) {
        map[p.sector] = { returns: [], companyCount: 0 };
      }

      map[p.sector].companyCount++;
      if (p.weekly_return !== null) {
        map[p.sector].returns.push(Number(p.weekly_return));
      }
    }

    const result = Object.entries(map).map(([sector, d]) => ({
      name:                sector,
      companyCount:        d.companyCount,
      averageWeeklyReturn: d.returns.length > 0
        ? Number((d.returns.reduce((a, b) => a + b, 0) / d.returns.length).toFixed(2))
        : null,
    }));

    result.sort((a, b) => a.name.localeCompare(b.name));
    res.json(result);
  } catch (err) {
    console.error("sectorController error:", err.message);
    res.status(500).json({ error: "Failed to process sectors" });
  }
};

module.exports = { getSectors };
