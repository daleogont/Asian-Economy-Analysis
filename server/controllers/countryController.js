const { getAllLatestPrices } = require("../utils/stockQueries");

const getCountries = async (req, res) => {
  try {
    const prices = await getAllLatestPrices();
    const map = {};

    for (const p of Object.values(prices)) {
      if (!p.price) continue;

      if (!map[p.country]) {
        map[p.country] = { weeklyReturns: [], sectors: {}, companyCount: 0 };
      }

      map[p.country].companyCount++;
      map[p.country].sectors[p.sector] =
        (map[p.country].sectors[p.sector] || 0) + 1;

      if (p.weekly_return !== null) {
        map[p.country].weeklyReturns.push(Number(p.weekly_return));
      }
    }

    const result = Object.entries(map).map(([country, d]) => ({
      country,
      companyCount: d.companyCount,
      sectors: d.sectors,
      averageWeeklyReturn:
        d.weeklyReturns.length > 0
          ? Number(
              (
                d.weeklyReturns.reduce((a, b) => a + b, 0) /
                d.weeklyReturns.length
              ).toFixed(2)
            )
          : null,
    }));

    result.sort((a, b) => b.companyCount - a.companyCount);
    res.json(result);
  } catch (err) {
    console.error("countryController error:", err.message);
    res.status(500).json({ error: "Failed to load countries" });
  }
};

module.exports = { getCountries };
