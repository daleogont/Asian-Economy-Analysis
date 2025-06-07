const yahooFinance = require("yahoo-finance2").default;
const fs = require("fs");
const path = require("path");
const { convertToUSD } = require("./currencyService"); 

const cachePath = path.resolve(__dirname, "../../data/cache.json");


let cache = {};
if (fs.existsSync(cachePath)) {
  try {
    cache = JSON.parse(fs.readFileSync(cachePath, "utf-8"));
  } catch {
    cache = {};
  }
}

const fetchCompanyData = async (ticker) => {
  if (cache[ticker]) {
    return cache[ticker];
  }
  try {
    const quote = await yahooFinance.quoteSummary(ticker, {
      modules: ["price", "summaryDetail", "financialData"],
    });

    if (!quote || !quote.price) return null;

    const price = quote.price;
    const finance = quote.financialData || {};
    const currency = price.currency || "USD";

    if (
      typeof price.regularMarketPrice !== "number" ||
      typeof price.regularMarketPreviousClose !== "number" ||
      typeof price.marketCap !== "number"
    ) return null;

    const stockPriceUSD = convertToUSD(price.regularMarketPrice, currency);
    const marketCapUSD = convertToUSD(price.marketCap, currency);

    const data = {
      ticker,
      stockPrice: stockPriceUSD,
      marketCap: marketCapUSD,
      peRatio: finance.trailingPE ?? null,
      previousClose: convertToUSD(price.regularMarketPreviousClose, currency),
      currency, 
    };

    cache[ticker] = data;
    fs.writeFileSync(cachePath, JSON.stringify(cache, null, 2));

    return data;
  } catch (error) {
    console.error(`❌ Yahoo error for ${ticker}:`, error.message);
    return null;
  }
};

module.exports = { fetchCompanyData };
