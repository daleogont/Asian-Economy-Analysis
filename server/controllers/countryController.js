// server/controllers/countryController.js
const path = require("path");
const fs   = require("fs");
const { getCache } = require("../utils/cacheStore");

const companiesPath = path.join(__dirname, "../../data/realCompanies.json");

const getCountries = async (req, res) => {
  try {
    const companies = JSON.parse(fs.readFileSync(companiesPath, "utf-8"));
    const cache     = getCache();

    const countryMap = {};

    companies.forEach(({ ticker, country, sector }) => {
      const data = cache.get(ticker);
      if (
        !data ||
        typeof data.stockPrice    !== "number" ||
        typeof data.previousClose !== "number"
      ) return;

      if (!countryMap[country]) {
        countryMap[country] = { totalCap: 0, sectors: {}, weeklyReturns: [] };
      }

      const cap = data.marketCap ?? 0;
      countryMap[country].totalCap += cap;
      countryMap[country].sectors[sector] =
        (countryMap[country].sectors[sector] || 0) + cap;

      const weeklyReturn =
        typeof data.weeklyReturn === "number"
          ? data.weeklyReturn
          : ((data.stockPrice - data.previousClose) / data.previousClose) * 100;
      countryMap[country].weeklyReturns.push(weeklyReturn);
    });

    const result = Object.entries(countryMap).map(([country, data]) => ({
      country,
      totalCap: data.totalCap,
      sectors:  data.sectors,
      averageWeeklyReturn:
        data.weeklyReturns.length > 0
          ? Number(
              (data.weeklyReturns.reduce((a, b) => a + b, 0) /
                data.weeklyReturns.length).toFixed(2)
            )
          : null,
    }));

    result.sort((a, b) => b.totalCap - a.totalCap);
    res.json(result);
  } catch (err) {
    console.error("countryController error:", err.message);
    res.status(500).json({ error: "Failed to load countries" });
  }
};

module.exports = { getCountries };
