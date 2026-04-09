// server/controllers/sectorLeadersController.js
const path = require("path");
const fs   = require("fs");
const { getCache } = require("../utils/cacheStore");

const companiesPath = path.join(__dirname, "../../data/realCompanies.json");

const getSectorLeaders = (req, res) => {
  const companies = JSON.parse(fs.readFileSync(companiesPath, "utf-8"));
  const cache     = getCache();

  const leaders = {};

  companies.forEach((company) => {
    const data = cache.get(company.ticker);
    if (!data || typeof data.stockPrice !== "number") return;

    const cap = data.marketCap ?? 0;
    if (
      !leaders[company.sector] ||
      cap > (leaders[company.sector].marketCap ?? 0)
    ) {
      leaders[company.sector] = {
        name:       company.name,
        ticker:     company.ticker,
        country:    company.country,
        sector:     company.sector,
        marketCap:  cap,
        stockPrice: data.stockPrice,
      };
    }
  });

  res.json(Object.values(leaders));
};

module.exports = { getSectorLeaders };
