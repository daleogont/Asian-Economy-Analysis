const currencyToUSD = {
    JPY:   0.006934,
    CNY:   0.1391,
    HKD:   0.1274,
    INR:   0.01164,
    SGD:   0.7755,
    KRW:   0.0007,
    IDR:   0.0000612,
    MYR:   0.2353,
    TWD:   0.0334,
    SAR:   0.266667,
    THB:   0.0308,
    USD:   1
  };
  
  function convertToUSD(value, currency) {
    const rate = currencyToUSD[currency];
    if (rate == null) {
      console.warn(`[currencyService] Unknown currency "${currency}" — returning raw value`);
      return value;
    }
    return value * rate;
  }
  
  module.exports = {
    convertToUSD
  };
  