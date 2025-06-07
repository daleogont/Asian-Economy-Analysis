const companies = require('../../data/realCompanies.json');
const cache     = require('../../data/cache.json');

const getSectorLeaders = (req, res) => {
  const leaders = {};
  companies.forEach((company) => {
    const data = cache[company.ticker];
    if (!data || typeof data.marketCap !== 'number') return;
    if (
      !leaders[company.sector] ||
      data.marketCap > leaders[company.sector].marketCap
    ) {
      leaders[company.sector] = {
        name:      company.name,
        ticker:    company.ticker,
        country:   company.country,
        sector:    company.sector,
        marketCap: data.marketCap,
        stockPrice:data.stockPrice,
      };
    }
  });
  res.json(Object.values(leaders));
};

module.exports = { getSectorLeaders };
