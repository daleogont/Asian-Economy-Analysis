const path = require("path");
const fs = require("fs");
const { fetchCompanyData } = require("../utils/yahooService");

const companiesPath = path.join(__dirname, "../../data/realCompanies.json");

const getCompanies = async (req, res) => {
  try {
    const rawData = fs.readFileSync(companiesPath, "utf-8");
    const companies = JSON.parse(rawData);

    const results = await Promise.all(
      companies.map(async (company) => {
        try {
          const data = await fetchCompanyData(company.ticker);

          if (
            !data ||
            typeof data.marketCap !== "number" ||
            typeof data.stockPrice !== "number" ||
            typeof data.previousClose !== "number"
          ) {
            console.warn(`⚠️ Недостатньо даних для ${company.ticker}`);
            return null;
          }

          const weeklyReturn =
            ((data.stockPrice - data.previousClose) / data.previousClose) * 100;

          return {
            name: company.name,
            ticker: company.ticker,
            country: company.country,
            sector: company.sector,
            marketCap: data.marketCap,
            stockPrice: data.stockPrice,
            weeklyReturn: Number(weeklyReturn.toFixed(2)),
          };
        } catch (err) {
          console.error(`❌ Помилка при запиті до Yahoo для ${company.ticker}:`, err.message);
          return null;
        }
      })
    );

    const unique = {};
    results.filter(Boolean).forEach((company) => {
      const key = `${company.country}|${company.sector}`;
      if (!unique[key] || company.stockPrice > unique[key].stockPrice) {
        unique[key] = company;
      }
    });

    const sorted = Object.values(unique).sort((a, b) => {
      if (a.country !== b.country) return a.country.localeCompare(b.country);
      return a.sector.localeCompare(b.sector);
    });

    res.json(sorted);
  } catch (error) {
    console.error("🔥 Фатальна помилка в getCompanies:", error.message);
    res.status(500).json({ error: "Не вдалося отримати дані про компанії" });
  }
};

module.exports = { getCompanies };
