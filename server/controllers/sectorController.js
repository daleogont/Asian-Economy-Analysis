const fs   = require('fs');
const path = require('path');

const companiesPath = path.join(__dirname, '../../data/realCompanies.json');
const cachePath     = path.join(__dirname, '../../data/cache.json');

const getSectors = async (req, res) => {
  try {
    const companies = JSON.parse(fs.readFileSync(companiesPath, 'utf-8'));
    const cache     = JSON.parse(fs.readFileSync(cachePath, 'utf-8'));

    const sectorData = {}; 
    let totalMarketCap = 0;

    companies.forEach((company) => {
      const cached = cache[company.ticker];
      if (
        !cached ||
        typeof cached.marketCap !== 'number' ||
        typeof cached.stockPrice !== 'number' ||
        typeof cached.previousClose !== 'number'
      )
        return;

      const { marketCap, stockPrice, previousClose } = cached;
      const weeklyReturn = ((stockPrice - previousClose) / previousClose) * 100;

      if (!sectorData[company.sector]) {
        sectorData[company.sector] = {
          name: sectorData[company.sector]?.name || company.sector,
          totalCap: 0,
          weightedReturnSum: 0,
        };
      }

      sectorData[company.sector].totalCap += marketCap;
      sectorData[company.sector].weightedReturnSum += weeklyReturn * marketCap;
      totalMarketCap += marketCap;
    });

    const result = Object.values(sectorData).map((sector) => {
      const marketWeight = (sector.totalCap / totalMarketCap) * 100;
      const weightedWeeklyReturn = sector.totalCap > 0
        ? sector.weightedReturnSum / sector.totalCap
        : null;

      return {
        name:         sector.name,
        marketWeight: Number(marketWeight.toFixed(2)),
        weeklyReturn: weightedWeeklyReturn !== null
          ? Number(weightedWeeklyReturn.toFixed(2))
          : null,
      };
    });

    result.sort((a, b) => b.marketWeight - a.marketWeight);
    res.json(result);
  } catch (error) {
    console.error('Помилка при обробці секторів:', error.message);
    res.status(500).json({ error: 'Не вдалося обробити сектори' });
  }
};

module.exports = { getSectors };
