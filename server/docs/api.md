# API Documentation

## 1. /api/companies

**Method:** GET  
**Description:** Returns a list of valid companies with their minimal financial metrics.

**Response Example:**
[
  {
    "name": "Sumitomo Mitsui Trust Holdings",
    "ticker": "8309.T",
    "country": "Japan",
    "sector": "Finance",
    "marketCap": 2789819285504,
    "stockPrice": 3846,
    "weeklyReturn": 0.03
  },
  ...
]

---

## 2. /api/sectors

**Method:** GET  
**Description:** Returns aggregated statistics for each sector (marketWeight, average weeklyReturn).

**Response Example:**
[
  {
    "name": "Finance",
    "marketWeight": 18.7,
    "weeklyReturn": 0.2
  },
  ...
]

---

## 3. /api/countries

**Method:** GET  
**Description:** Returns aggregated statistics for each country (totalCap, sectors).

**Response Example:**
[
  {
    "country": "Japan",
    "totalCap": 21983224954888,
    "sectors": {
      "Finance": 2789819285504,
      "Technology": 10994632884224,
      ...
    }
  },
  ...
]

---

## 4. /api/macros?country=Japan

**Method:** GET  
**Description:** Returns macroeconomic data for a given country.
**Query Parameters:**  
- `country` (string): Name of the country (Japan, China, India, Singapore, Thailand)

**Response Example:**
{
  "country": "Japan",
  "code": "JP",
  "gdp": 4459370000000,
  "population": 124950000,
  "unemployment": 2.8
}

---

## 5. /api/top-movers?limit=5

**Method:** GET  
**Description:** Returns the top N companies with the highest (or lowest) weekly return.
**Query Parameters:**  
- `limit` (integer, optional): Number of companies to return (default: 5)

**Response Example:**
[
  {
    "name": "SoftBank Group",
    "ticker": "9984.T",
    "country": "Japan",
    "sector": "Technology",
    "marketCap": 10994632884224,
    "stockPrice": 7427,
    "weeklyReturn": 4.1
  },
  ...
]

---

## 6. /api/sector-leaders

**Method:** GET  
**Description:** Returns one leader-company for each sector (highest marketCap).

**Response Example:**
[
  {
    "name": "SoftBank Group",
    "ticker": "9984.T",
    "country": "Japan",
    "sector": "Technology",
    "marketCap": 10994632884224,
    "stockPrice": 7427,
    "weeklyReturn": 4.1
  },
  ...
]

---

## 7. /api/market-overview

**Method:** GET  
**Description:** Returns aggregated market overview including average returns and total capitalization by sector/country.

**Response Example:**
{
  "totalMarketCap": 12900000000000,
  "averageWeeklyReturn": 0.51,
  "sectorStats": [...],
  "countryStats": [...]
}
