const { getAllLatestPrices } = require("../utils/stockQueries");

const getMarketOverview = async (req, res) => {
  try {
    const prices    = await getAllLatestPrices();
    const byCountry = {};
    let returns = [], count = 0;

    for (const p of Object.values(prices)) {
      if (!p.price) continue;

      count++;
      if (p.weekly_return !== null) returns.push(Number(p.weekly_return));

      if (!byCountry[p.country]) byCountry[p.country] = { companies: 0 };
      byCountry[p.country].companies++;
    }

    res.json({
      totalCompanies:  count,
      avgWeeklyReturn: returns.length
        ? Number((returns.reduce((a, b) => a + b, 0) / returns.length).toFixed(2))
        : null,
      countries: byCountry,
    });
  } catch (err) {
    console.error("marketOverviewController error:", err.message);
    res.status(500).json({ error: "Failed to get market overview" });
  }
};

module.exports = { getMarketOverview };
