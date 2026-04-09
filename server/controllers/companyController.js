const path = require("path");
const fs   = require("fs");
const { fetchCompanyData } = require("../utils/dataService");

const companiesPath = path.join(__dirname, "../../data/realCompanies.json");

const getCompanies = async (req, res) => {
  try {
    const companies = JSON.parse(fs.readFileSync(companiesPath, "utf-8"));

    const results = await Promise.all(
      companies.map(async (company) => {
        try {
          const data = await fetchCompanyData(company.ticker);

          if (
            !data ||
            typeof data.stockPrice    !== "number" ||
            typeof data.previousClose !== "number"
          ) {
            console.warn(`⚠️  No data for ${company.ticker}`);
            return null;
          }

          const weeklyReturn =
            typeof data.weeklyReturn === "number"
              ? data.weeklyReturn
              : ((data.stockPrice - data.previousClose) / data.previousClose) * 100;

          return {
            name:         company.name,
            ticker:       company.ticker,
            country:      company.country,
            sector:       company.sector,
            marketCap:    data.marketCap ?? 0,
            stockPrice:   data.stockPrice,
            weeklyReturn: Number(weeklyReturn.toFixed(2)),
            dataSource:   data.source   ?? "cache",
            isSeed:       data.isSeed   ?? false,
          };
        } catch (err) {
          console.error(`❌ Error fetching ${company.ticker}:`, err.message);
          return null;
        }
      })
    );

    // One representative per country+sector (highest stock price)
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
  } catch (err) {
    console.error("🔥 Fatal error in getCompanies:", err.message);
    res.status(500).json({ error: "Failed to fetch company data" });
  }
};

module.exports = { getCompanies };
