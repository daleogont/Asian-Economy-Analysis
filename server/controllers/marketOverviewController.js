const companies = require('../../data/realCompanies.json');
const cache     = require('../../data/cache.json');

const getMarketOverview = (req, res) => {
  let totalMarketCap  = 0;
  let totalReturn     = 0;
  let totalStockPrice = 0;
  let count           = 0;
  const byCountry     = {};

  companies.forEach((company) => {
    const data = cache[company.ticker];
    if (
      !data ||
      typeof data.marketCap     !== 'number' ||
      typeof data.stockPrice    !== 'number' ||
      typeof data.previousClose !== 'number'
    )
      return;

    const weeklyReturn =
      ((data.stockPrice - data.previousClose) / data.previousClose) * 100;

    totalMarketCap  += data.marketCap;
    totalReturn     += weeklyReturn;
    totalStockPrice += data.stockPrice;
    count++;

    if (!byCountry[company.country]) {
      byCountry[company.country] = { marketCap: 0, companies: 0 };
    }
    byCountry[company.country].marketCap += data.marketCap;
    byCountry[company.country].companies++;
  });

  res.json({
    totalMarketCap,
    avgWeeklyReturn: count ? totalReturn / count : null,
    avgStockPrice:   count ? totalStockPrice / count : null,
    countries:       byCountry,
    totalCompanies:  count,
  });
};

module.exports = { getMarketOverview };
