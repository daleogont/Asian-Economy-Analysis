const fs   = require('fs');
const path = require('path');

const companiesPath = path.join(__dirname, '../../data/realCompanies.json');
const cachePath     = path.join(__dirname, '../../data/cache.json');

const getCountries = async (req, res) => {
  try {
    const companies = JSON.parse(fs.readFileSync(companiesPath, 'utf-8'));
    const cache     = JSON.parse(fs.readFileSync(cachePath, 'utf-8'));

    const countryMap = {};

    companies.forEach((company) => {
      const { ticker, country, sector } = company;
      const data = cache[ticker];
      if (
        !data ||
        typeof data.marketCap !== 'number' ||
        typeof data.stockPrice !== 'number' ||
        typeof data.previousClose !== 'number'
      )
        return;

      if (!countryMap[country]) {
        countryMap[country] = {
          totalCap:      0,
          sectors:       {},
          weeklyReturns: [],
        };
      }

      countryMap[country].totalCap += data.marketCap;
      countryMap[country].sectors[sector] =
        (countryMap[country].sectors[sector] || 0) + data.marketCap;

      const weeklyReturn =
        ((data.stockPrice - data.previousClose) / data.previousClose) * 100;
      countryMap[country].weeklyReturns.push(weeklyReturn);
    });

    const result = Object.entries(countryMap).map(([country, data]) => ({
      country,
      totalCap: data.totalCap,
      sectors: data.sectors,
      averageWeeklyReturn:
        data.weeklyReturns.length > 0
          ? Number(
              (
                data.weeklyReturns.reduce((a, b) => a + b, 0) /
                data.weeklyReturns.length
              ).toFixed(2)
            )
          : null,
    }));

    result.sort((a, b) => b.totalCap - a.totalCap);
    res.json(result);
  } catch (err) {
    console.error('countryController error:', err.message);
    res.status(500).json({ error: 'Не вдалося завантажити країни' });
  }
};

module.exports = { getCountries };
