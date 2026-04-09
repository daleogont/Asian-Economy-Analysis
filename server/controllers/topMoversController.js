// server/controllers/topMoversController.js
const path = require("path");
const fs   = require("fs");
const { getCache } = require("../utils/cacheStore");

const companiesPath = path.join(__dirname, "../../data/realCompanies.json");

const getTopMovers = (req, res) => {
  const count     = parseInt(req.query.count) || 5;
  const direction = req.query.direction === "down" ? "down" : "up";

  const companies = JSON.parse(fs.readFileSync(companiesPath, "utf-8"));
  const cache     = getCache();

  const valid = companies
    .map((company) => {
      const data = cache.get(company.ticker);
      if (
        !data ||
        typeof data.stockPrice    !== "number" ||
        typeof data.previousClose !== "number"
      ) return null;

      const weeklyReturn =
        typeof data.weeklyReturn === "number"
          ? data.weeklyReturn
          : ((data.stockPrice - data.previousClose) / data.previousClose) * 100;

      return {
        name:         company.name,
        ticker:       company.ticker,
        country:      company.country,
        sector:       company.sector,
        stockPrice:   data.stockPrice,
        marketCap:    data.marketCap ?? 0,
        weeklyReturn: Number(weeklyReturn.toFixed(2)),
      };
    })
    .filter(Boolean);

  valid.sort((a, b) =>
    direction === "down"
      ? a.weeklyReturn - b.weeklyReturn
      : b.weeklyReturn - a.weeklyReturn
  );

  res.json(valid.slice(0, count));
};

module.exports = { getTopMovers };
