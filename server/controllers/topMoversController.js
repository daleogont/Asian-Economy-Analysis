
const companies = require('../../data/realCompanies.json');
const cache     = require('../../data/cache.json');

const getTopMovers = (req, res) => {
  const count     = parseInt(req.query.count) || 5;
  const direction = req.query.direction === 'down' ? 'down' : 'up';

  const validCompanies = companies
    .map((company) => {
      const data = cache[company.ticker];
      if (
        !data ||
        typeof data.stockPrice !== 'number' ||
        typeof data.previousClose !== 'number'
      ) return null;

      const weeklyReturn =
        ((data.stockPrice - data.previousClose) / data.previousClose) * 100;

      return {
        name:         company.name,
        ticker:       company.ticker,
        country:      company.country,
        sector:       company.sector,
        stockPrice:   data.stockPrice,
        marketCap:    data.marketCap,
        weeklyReturn: Number(weeklyReturn.toFixed(2)),
      };
    })
    .filter(Boolean);

  validCompanies.sort((a, b) =>
    direction === 'down'
      ? a.weeklyReturn - b.weeklyReturn
      : b.weeklyReturn - a.weeklyReturn
  );

  res.json(validCompanies.slice(0, count));
};

module.exports = { getTopMovers };
