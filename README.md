# Asian Capital Markets Intelligence Platform

A full-stack analytical platform for monitoring and forecasting stock market dynamics across 14 Asian economies. Built as a dissertation project combining real financial data, descriptive analytics, and ARIMA-based time-series forecasting.

**Live coverage:** 272 companies · 14 countries · 11 sectors · 2 years of daily price history

---

## What it does

- Displays latest stock prices and weekly returns for 272 Asian companies
- Groups companies by country and sector with aggregated statistics
- Shows macro indicators (GDP, population, unemployment) via World Bank API
- Price history charts with 7-day and 30-day rolling moving averages
- ARIMA(1,1,1) price forecasting with 95% confidence intervals
- Summary statistics (mean, median, std dev) per country and sector
- Weekly return distribution histograms
- Top movers and sector leaders dashboards

---

## Architecture

```
Browser (React)
     │
     ▼
Nginx (port 3000)
  ├── /api/*          → Node.js / Express (port 4000)
  └── /analytics/*    → Python FastAPI    (port 8000)
                              │
                    PostgreSQL (port 5432)
                    131k+ daily price rows
```

---

## Tech stack

| Layer        | Technology                                      |
|--------------|-------------------------------------------------|
| Frontend     | React, Tailwind CSS, Recharts                   |
| API Gateway  | Node.js, Express, node-cron                     |
| Analytics    | Python 3.10, FastAPI, pandas, numpy, statsmodels|
| Database     | PostgreSQL 16                                   |
| Data sources | Yahoo Finance, Twelve Data, World Bank API      |
| Infra        | Docker, Docker Compose, Nginx                   |

---

## Quick start

**Requirements:** Docker + Docker Compose

```bash
# Clone and configure
git clone https://github.com/daleogont/Asian-Economy-Analysis.git
cd Asian-Economy-Analysis
cp .env.example .env          # add your TWELVE_DATA_KEY

# Start all services
docker compose up --build -d

# Apply database schema
docker compose exec postgres psql -U admin -d asianmarkets \
  -f /dev/stdin < data/schema.sql

# Seed companies into DB
docker compose exec node-api node scripts/seedCompanies.js

# Collect 2 years of price history (~30 min for all tickers)
node scripts/collectHistory.js
```

Open `http://localhost:3000`

---

## Environment variables

| Variable            | Required | Description                                    |
|---------------------|----------|------------------------------------------------|
| `TWELVE_DATA_KEY`   | No       | Twelve Data API key (fallback when Yahoo fails)|
| `POSTGRES_DB`       | Yes      | Database name (default: `asianmarkets`)        |
| `POSTGRES_USER`     | Yes      | DB user (default: `admin`)                     |
| `POSTGRES_PASSWORD` | Yes      | DB password (default: `secret`)                |
| `DATABASE_URL`      | Yes      | Full PostgreSQL connection string              |
| `PORT`              | No       | Node.js server port (default: `4000`)          |

---

## API reference

### Node.js API (`/api/*`)

| Method | Endpoint                              | Description                                         |
|--------|---------------------------------------|-----------------------------------------------------|
| GET    | `/api/health`                         | Server status and cache statistics                  |
| GET    | `/api/companies`                      | All 272 companies with latest price and weekly return|
| GET    | `/api/countries`                      | Aggregated stats per country                        |
| GET    | `/api/sectors`                        | Aggregated stats per sector                         |
| GET    | `/api/sector-leaders`                 | Highest-priced company per sector                   |
| GET    | `/api/market-overview`                | Platform-wide totals                                |
| GET    | `/api/top-movers?count=5&direction=up`| Top gainers or losers by weekly return              |
| GET    | `/api/macros?country=Japan`           | GDP, population, unemployment (World Bank)          |
| GET    | `/api/history/:ticker?period=1y`      | OHLCV history from DB (3m / 6m / 1y / 2y)         |

### Python Analytics API (`/analytics/*`)

| Method | Endpoint                                   | Description                                      |
|--------|--------------------------------------------|--------------------------------------------------|
| GET    | `/health`                                  | FastAPI health check                             |
| GET    | `/analytics/summary?country=&sector=`      | Mean, median, std, min, max for price and return |
| GET    | `/analytics/rolling/:ticker?window=30`     | Close prices + N-day rolling moving average      |
| GET    | `/analytics/forecast/:ticker?days=30`      | ARIMA(1,1,1) forecast + 95% confidence interval |

Full API documentation: see `postman_collection.json` and `openapi.yaml` in project root.

---

## Database schema

```sql
companies    — ticker, name, country, sector, exchange
daily_prices — ticker, date, open, high, low, close, volume, currency
forecasts    — ticker, forecast_date, predicted_close, lower_bound, upper_bound, model
```

---

## Project structure

```
├── analytics/              Python FastAPI service
│   └── app/
│       ├── main.py         App entry point + CORS
│       ├── db.py           SQLAlchemy connection
│       └── routers/
│           ├── summary.py  Descriptive statistics
│           ├── rolling.py  Rolling moving average
│           └── forecast.py ARIMA forecasting
├── client/                 React frontend
│   └── src/
│       ├── pages/          Home, Countries, Sections, country/*, section/*
│       └── components/     PriceHistoryChart, ForecastChart, SummaryStats,
│                           WeeklyReturnHistogram, WeeklyReturnIndicator
├── server/                 Node.js API
│   ├── controllers/        Business logic per route
│   ├── routes/             Express route definitions
│   └── utils/
│       ├── db.js           PostgreSQL pool
│       ├── dataService.js  Yahoo Finance / Twelve Data fetcher
│       ├── deltaFetch.js   Daily incremental price updater
│       └── stockQueries.js DB query helpers
├── scripts/
│   ├── seedCompanies.js    One-time company seeding
│   └── collectHistory.js   2-year history collection + delta updates
├── data/
│   ├── realCompanies.json  Master company registry (272 companies)
│   └── schema.sql          PostgreSQL schema
├── docker-compose.yml
├── postman_collection.json Full API collection (27 requests)
└── openapi.yaml            OpenAPI 3.0 spec for analytics API
```

---

## Data sources

- **Yahoo Finance** — free OHLCV chart API, no key required
- **Twelve Data** — fallback source, free tier (800 req/day)
- **World Bank API** — macro indicators, no key required

---

## Roadmap

- **Stage 1 (current):** Real data, 2y history, ARIMA forecasting, descriptive analytics
- **Stage 2:** Regression, clustering (K-means), anomaly detection, PostgreSQL migrations, Docker staging
- **Stage 3:** LSTM deep learning, NLP sentiment (FinBERT), macro integration (World Bank), XGBoost ensemble
