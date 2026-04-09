// server/controllers/sectorController.js
const path = require("path");
const fs   = require("fs");
const { getCache } = require("../utils/cacheStore");

const companiesPath = path.join(__dirname, "../../data/realCompanies.json");

const getSectors = async (req, res) => {
  try {
    const companies = JSON.parse(fs.readFileSync(companiesPath, "utf-8"));
    const cache     = getCache();

    const sectorData   = {};
    let totalMarketCap = 0;

    companies.forEach((company) => {
      const cached = cache.get(company.ticker);
      if (
        !cached ||
        typeof cached.stockPrice    !== "number" ||
        typeof cached.previousClose !== "number"
      ) return;

      const marketCap = cached.marketCap ?? 0;
      const { stockPrice, previousClose } = cached;
      const weeklyReturn =
        typeof cached.weeklyReturn === "number"
          ? cached.weeklyReturn
          : ((stockPrice - previousClose) / previousClose) * 100;

      if (!sectorData[company.sector]) {
        sectorData[company.sector] = {
          name: company.sector,
          totalCap: 0,
          weightedReturnSum: 0,
        };
      }

      sectorData[company.sector].totalCap          += marketCap;
      sectorData[company.sector].weightedReturnSum += weeklyReturn * marketCap;
      totalMarketCap += marketCap;
    });

    const result = Object.values(sectorData).map((sector) => ({
      name:         sector.name,
      marketWeight: Number(((sector.totalCap / totalMarketCap) * 100).toFixed(2)),
      weeklyReturn:
        sector.totalCap > 0
          ? Number((sector.weightedReturnSum / sector.totalCap).toFixed(2))
          : null,
    }));

    result.sort((a, b) => b.marketWeight - a.marketWeight);
    res.json(result);
  } catch (error) {
    console.error("sectorController error:", error.message);
    res.status(500).json({ error: "Failed to process sectors" });
  }
};

module.exports = { getSectors };
