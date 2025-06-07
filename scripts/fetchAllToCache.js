const yahooFinance = require("yahoo-finance2").default;
const fs = require("fs");
const path = require("path");
const { convertToUSD } = require("../server/utils/currencyService");
const companies = require("../data/realCompanies.json");

const cachePath = path.join(__dirname, "../data/cache.json");

(async () => {
  const cache = {};

  for (const company of companies) {
    const ticker = company.ticker;
    try {
      const quote = await yahooFinance.quoteSummary(ticker, {
        modules: ["price", "summaryDetail", "financialData"],
      });

      const price = quote?.price || {};
      const currency = price.currency || "USD";

      cache[ticker] = {
        ticker,
        stockPrice: convertToUSD(price.regularMarketPrice ?? 0, currency),
        marketCap:    convertToUSD(price.marketCap ?? 0, currency),
        previousClose: convertToUSD(price.regularMarketPreviousClose ?? 0, currency),
        currency,
      };
      console.log(`[+] ${ticker} — OK`);
    } catch {
      cache[ticker] = null;
      console.log(`[x] ${ticker} — error`);
    }
  }

  fs.writeFileSync(cachePath, JSON.stringify(cache, null, 2));
  console.log("Готово! Дані збережено у /data/cache.json");
  process.exit(0);
})();
