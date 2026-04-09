// server/controllers/marketOverviewController.js
const path = require("path");
const fs   = require("fs");
const { getCache } = require("../utils/cacheStore");

const companiesPath = path.join(__dirname, "../../data/realCompanies.json");

const getMarketOverview = (req, res) => {
  const companies = JSON.parse(fs.readFileSync(companiesPath, "utf-8"));
  const cache     = getCache();

  let totalMarketCap  = 0;
  let totalReturn     = 0;
  let totalStockPrice = 0;
  let count           = 0;
  const byCountry     = {};

  companies.forEach((company) => {
    const data = cache.get(company.ticker);
    if (
      !data ||
      typeof data.stockPrice    !== "number" ||
      typeof data.previousClose !== "number"
    ) return;

    const cap = data.marketCap ?? 0;
    const weeklyReturn =
      typeof data.weeklyReturn === "number"
        ? data.weeklyReturn
        : ((data.stockPrice - data.previousClose) / data.previousClose) * 100;

    totalMarketCap  += cap;
    totalReturn     += weeklyReturn;
    totalStockPrice += data.stockPrice;
    count++;

    if (!byCountry[company.country]) {
      byCountry[company.country] = { marketCap: 0, companies: 0 };
    }
    byCountry[company.country].marketCap += cap;
    byCountry[company.country].companies++;
  });

  res.json({
    totalMarketCap,
    avgWeeklyReturn: count ? totalReturn     / count : null,
    avgStockPrice:   count ? totalStockPrice / count : null,
    countries:       byCountry,
    totalCompanies:  count,
  });
};

module.exports = { getMarketOverview };
