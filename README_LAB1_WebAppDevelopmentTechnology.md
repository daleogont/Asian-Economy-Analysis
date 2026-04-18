# Lab Work #1 — Web Application Development Technology

**Student:** Daniil Hontar
**Group:** KV-51MP
**Project:** Asian Capital Markets Intelligence Platform

---

## Note on technology choice

The standard stack for this course is Django (Python). With instructor approval, this lab uses **Python FastAPI** instead of Django. The justification: FastAPI is a modern, production-grade Python web framework with native async support, automatic OpenAPI documentation, and type validation via Pydantic — more representative of current industry practice for data-intensive APIs. The learning outcomes (server-side routing, request handling, database integration, API design) are fully met.

---

## Project overview

The Asian Capital Markets Intelligence Platform is a full-stack analytical system for monitoring and forecasting stock market dynamics across 14 Asian countries. The server-side component consists of two backends:

1. **Python FastAPI** — analytics engine (statistics, rolling averages, ARIMA forecasting)
2. **Node.js / Express** — data gateway (company data, price history, market aggregations)

Both connect to a shared **PostgreSQL 16** database and run in separate **Docker** containers orchestrated by Docker Compose.

---

## Technology stack

| Component       | Technology                                             |
|-----------------|--------------------------------------------------------|
| Analytics API   | Python 3.10, FastAPI 0.115, Uvicorn                   |
| Data processing | pandas 2.2, numpy 1.26, statsmodels 0.14              |
| Database ORM    | SQLAlchemy 2.0, psycopg2-binary                        |
| API Gateway     | Node.js 20, Express 5, node-cron                       |
| Database        | PostgreSQL 16                                          |
| Infrastructure  | Docker, Docker Compose, Nginx (reverse proxy)          |
| External APIs   | Yahoo Finance (OHLCV data), Twelve Data, World Bank    |

---

## System architecture

```
Client (React / Nginx) — port 3000
         │
         ├── /api/*         → Node.js Express  (port 4000)
         └── /analytics/*   → Python FastAPI    (port 8000)
                                     │
                          PostgreSQL database  (port 5432)
                          Tables: companies, daily_prices, forecasts
```

All services run in Docker containers with a shared internal network. PostgreSQL health checks ensure dependent services only start after the database is ready.

---

## Database structure

Defined in `data/schema.sql`:

### Table: `companies`

| Column   | Type          | Description                              |
|----------|---------------|------------------------------------------|
| ticker   | VARCHAR(20) PK| Yahoo Finance ticker symbol (unique ID)  |
| name     | VARCHAR(255)  | Full company name                        |
| country  | VARCHAR(100)  | Country (14 Asian markets)               |
| sector   | VARCHAR(100)  | GICS sector (11 sectors)                 |
| exchange | VARCHAR(50)   | Stock exchange (TSE, HKEX, KRX, etc.)   |

### Table: `daily_prices`

| Column   | Type          | Description                              |
|----------|---------------|------------------------------------------|
| id       | SERIAL PK     | Auto-increment row ID                    |
| ticker   | VARCHAR(20) FK| References companies(ticker)             |
| date     | DATE          | Trading date                             |
| open     | NUMERIC(18,6) | Opening price                            |
| high     | NUMERIC(18,6) | Daily high                               |
| low      | NUMERIC(18,6) | Daily low                                |
| close    | NUMERIC(18,6) | Closing price (primary analysis field)   |
| volume   | BIGINT        | Trading volume                           |
| currency | VARCHAR(10)   | Original currency (JPY, KRW, HKD, etc.) |

Unique constraint: `(ticker, date)` — prevents duplicate entries.
Indexes on `ticker`, `date`, and `(ticker, date DESC)` for query performance.

### Table: `forecasts`

| Column         | Type          | Description                          |
|----------------|---------------|--------------------------------------|
| id             | SERIAL PK     | Auto-increment row ID                |
| ticker         | VARCHAR(20) FK| References companies(ticker)         |
| forecast_date  | DATE          | Predicted trading date               |
| predicted_close| NUMERIC(18,6) | Model's predicted close price        |
| lower_bound    | NUMERIC(18,6) | 95% CI lower bound                   |
| upper_bound    | NUMERIC(18,6) | 95% CI upper bound                   |
| model          | VARCHAR(50)   | Model name (default: 'arima')        |
| created_at     | TIMESTAMP     | When forecast was generated          |

---

## API endpoints

### Python FastAPI — Analytics (`http://localhost:8000`)

#### `GET /health`
Service health check.

**Response:**
```json
{ "status": "ok" }
```

---

#### `GET /analytics/summary`
Descriptive statistics for a group of companies filtered by country and/or sector.

**Query parameters:**

| Parameter | Type   | Required | Description               |
|-----------|--------|----------|---------------------------|
| country   | string | No       | e.g. `Japan`, `India`     |
| sector    | string | No       | e.g. `Financials`, `Energy`|

**Response:**
```json
{
  "filters": { "country": "Japan", "sector": null },
  "companyCount": 22,
  "price": {
    "mean": 3241.85, "median": 1850.5, "std": 4102.33,
    "min": 112.4, "max": 19800.0, "count": 22
  },
  "weeklyReturn": {
    "mean": 0.42, "median": 0.31, "std": 1.87,
    "min": -3.12, "max": 4.55, "count": 22
  }
}
```

---

#### `GET /analytics/rolling/{ticker}`
Daily close prices with N-day rolling moving average.

**Path parameters:** `ticker` — Yahoo Finance symbol (e.g. `9988.HK`)

**Query parameters:**

| Parameter | Type    | Default | Constraints | Description              |
|-----------|---------|---------|-------------|--------------------------|
| window    | integer | 30      | 2–200       | Rolling window in days   |
| period    | string  | 1y      | 3m/6m/1y/2y | History window          |

**Response:**
```json
{
  "ticker": "9988.HK",
  "window": 30,
  "period": "1y",
  "data": [
    { "date": "2024-01-02", "close": 72.45, "ma30": 71.80 },
    { "date": "2024-01-03", "close": 73.10, "ma30": 71.95 }
  ]
}
```

---

#### `GET /analytics/forecast/{ticker}`
ARIMA(1,1,1) price forecast with 95% confidence interval.

**Path parameters:** `ticker` — Yahoo Finance symbol

**Query parameters:**

| Parameter | Type    | Default | Constraints | Description                |
|-----------|---------|---------|-------------|----------------------------|
| days      | integer | 30      | 7–90        | Forecast horizon in days   |
| period    | string  | 1y      | 6m/1y/2y    | Training history window    |

Requires minimum 60 rows of history. Returns 422 if insufficient data.

**Response:**
```json
{
  "ticker": "9988.HK",
  "model": "ARIMA(1,1,1)",
  "days": 30,
  "period": "1y",
  "history": [
    { "date": "2024-01-02", "actual": 72.45 }
  ],
  "forecast": [
    { "date": "2025-01-06", "predicted": 74.32, "lower": 68.11, "upper": 80.53 }
  ]
}
```

---

### Node.js API — Data Gateway (`http://localhost:4000`)

| Method | Endpoint                              | Description                                         |
|--------|---------------------------------------|-----------------------------------------------------|
| GET    | `/api/health`                         | Server status and live-data cache statistics        |
| GET    | `/api/companies`                      | All 272 companies with latest price and weekly return|
| GET    | `/api/countries`                      | Aggregated stats per country                        |
| GET    | `/api/sectors`                        | Aggregated stats per sector                         |
| GET    | `/api/sector-leaders`                 | Highest-priced company per sector                   |
| GET    | `/api/market-overview`                | Platform-wide totals (companies, avg return)        |
| GET    | `/api/top-movers?count=5&direction=up`| Top gainers or losers by weekly return              |
| GET    | `/api/macros?country=Japan`           | GDP, population, unemployment from World Bank       |
| GET    | `/api/history/:ticker?period=1y`      | OHLCV history from DB (3m / 6m / 1y / 2y)         |

---

## Data pipeline

```
realCompanies.json (272 companies)
        │
        ▼ scripts/seedCompanies.js
  companies table (PostgreSQL)
        │
        ▼ scripts/collectHistory.js (Yahoo Finance → fallback: Twelve Data)
  daily_prices table (131k+ rows, 2 years)
        │
        ▼ Node.js delta fetch (startup + cron 23:30 UTC daily)
  incremental daily updates
        │
        ▼ Python FastAPI
  analytics endpoints (reads directly from DB)
```


---

## Running the project

```bash
# Start all Docker services
docker compose up --build -d

# Apply DB schema
docker compose exec postgres psql -U admin -d asianmarkets -f /dev/stdin < data/schema.sql

# Seed companies
docker compose exec node-api node scripts/seedCompanies.js

# Collect 2y price history
node scripts/collectHistory.js
```

Full OpenAPI documentation for the analytics API: see `openapi.yaml` in project root.
Postman collection with all 27 requests: see `postman_collection.json` in project root.

---

## Google Drive Report

**URL:** `https://docs.google.com/document/d/1RQGuEa_BeF6HygheNGAJxgz_Gvc1pdyMAmZfvHKZiwQ/edit?tab=t.0`
