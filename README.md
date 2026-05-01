# Asian Capital Markets Intelligence Platform

A full-stack analytical platform for monitoring and forecasting stock market dynamics across 14 Asian economies. Built as a dissertation project combining real financial data, descriptive analytics, ARIMA-based time-series forecasting, and async task infrastructure.

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
- Async email notification and market analysis tasks via Celery + Redis
- Real-time task monitoring via WebSocket and Flower dashboard

---

## Architecture

```
Browser (React)
     │
     ▼
Nginx (port 3000)
  ├── /api/*          → Node.js / Express  (port 4000)
  └── /analytics/*    → Python FastAPI     (port 8000)
       └── /tasks/*        Celery tasks via Redis (port 6379)
       └── /ws/tasks        WebSocket — real-time task events
                                │
                    PostgreSQL (port 5432)
                    131k+ daily price rows
                    task_results table

Celery Worker  ←→  Redis (broker + result backend + pub/sub)
Flower UI (port 5555)
```

---

## Tech stack

| Layer        | Technology                                                         |
|--------------|--------------------------------------------------------------------|
| Frontend     | React 19, Tailwind CSS, Recharts                                   |
| API Gateway  | Node.js, Express, node-cron                                        |
| Analytics    | Python 3.11, FastAPI, pandas, numpy, statsmodels                   |
| Async tasks  | Celery 5.3, Redis 7, Flower                                        |
| Database     | PostgreSQL 16                                                      |
| Data sources | Yahoo Finance, Twelve Data, World Bank API                         |
| Infra        | Docker, Docker Compose, Nginx                                      |
| Testing      | Jest + React Testing Library, Cypress 13                           |

---

## Quick start

**Requirements:** Docker + Docker Compose

```bash
# Clone and configure
git clone https://github.com/daleogont/Asian-Economy-Analysis.git
cd Asian-Economy-Analysis
cp .env.example .env          # add your TWELVE_DATA_KEY

# Start all services (postgres, redis, node-api, python-api, celery-worker, flower, client)
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

| URL | Service |
|---|---|
| http://localhost:3000 | React frontend |
| http://localhost:4000 | Node.js API |
| http://localhost:8000 | Python FastAPI + analytics |
| http://localhost:8000/admin | Async task admin dashboard |
| http://localhost:5555 | Flower — Celery task monitor |

---

## Environment variables

| Variable            | Required | Description                                    |
|---------------------|----------|------------------------------------------------|
| `TWELVE_DATA_KEY`   | No       | Twelve Data API key (fallback when Yahoo fails)|
| `POSTGRES_DB`       | Yes      | Database name (default: `asianmarkets`)        |
| `POSTGRES_USER`     | Yes      | DB user (default: `admin`)                     |
| `POSTGRES_PASSWORD` | Yes      | DB password (default: `secret`)                |
| `DATABASE_URL`      | Yes      | Full PostgreSQL connection string              |
| `REDIS_URL`         | Yes      | Redis connection string (default: `redis://redis:6379/0`) |
| `PORT`              | No       | Node.js server port (default: `4000`)          |

---

## API reference

### Node.js API (`/api/*`)

| Method | Endpoint                              | Description                                          |
|--------|---------------------------------------|------------------------------------------------------|
| GET    | `/api/health`                         | Server status and cache statistics                   |
| GET    | `/api/companies`                      | All 272 companies with latest price and weekly return|
| GET    | `/api/countries`                      | Aggregated stats per country                         |
| GET    | `/api/sectors`                        | Aggregated stats per sector                          |
| GET    | `/api/sector-leaders`                 | Highest-priced company per sector                    |
| GET    | `/api/market-overview`                | Platform-wide totals                                 |
| GET    | `/api/top-movers?count=5&direction=up`| Top gainers or losers by weekly return               |
| GET    | `/api/macros?country=Japan`           | GDP, population, unemployment (World Bank)           |
| GET    | `/api/history/:ticker?period=1y`      | OHLCV history from DB (3m / 6m / 1y / 2y)          |

### Python Analytics API (`/analytics/*`)

| Method | Endpoint                                   | Description                                      |
|--------|--------------------------------------------|--------------------------------------------------|
| GET    | `/health`                                  | FastAPI health check                             |
| GET    | `/analytics/summary?country=&sector=`      | Mean, median, std, min, max for price and return |
| GET    | `/analytics/rolling/:ticker?window=30`     | Close prices + N-day rolling moving average      |
| GET    | `/analytics/forecast/:ticker?days=30`      | ARIMA(1,1,1) forecast + 95% confidence interval |

### Async Tasks API (`/tasks/*`)

| Method    | Endpoint                    | Description                                              |
|-----------|-----------------------------|----------------------------------------------------------|
| POST      | `/tasks/email`              | Trigger email notification task → returns `task_id`      |
| POST      | `/tasks/analysis`           | Trigger full market analysis task → returns `task_id`    |
| GET       | `/tasks/status/{task_id}`   | Poll task status and result from Redis result backend    |
| GET       | `/tasks/history`            | Load completed task history from PostgreSQL              |
| GET       | `/admin`                    | Admin dashboard HTML                                     |
| WebSocket | `/ws/tasks`                 | Real-time task completion broadcast (Redis pub/sub)      |

Full API documentation: see `postman_collection.json` and `openapi.yaml` in project root.

---

## Async Tasks

The analytics service uses **Celery 5.3** with **Redis 7** as broker and result backend. Two named queues handle different workload classes:

| Queue | Task | Description |
|---|---|---|
| `email_queue` | `send_email_notification` | Simulates weekly market alert emails to a user list. Fetches top 5 movers from DB automatically if none provided. |
| `longrunning_queue` | `run_market_analysis` | Full analytics pass: fetches all tickers, computes per-country stats (avg price, avg/best/worst weekly return). |

**Real-time events:** when a task completes, the worker publishes a JSON event to a Redis `task_events` pub/sub channel. FastAPI's async listener forwards it to all connected WebSocket clients instantly.

**Persistence:** every completed task is saved to the `task_results` PostgreSQL table (created automatically on startup), enabling the admin dashboard to load historical results on page load.

**Start Celery worker manually:**
```bash
celery -A app.celery_app:celery_app worker \
  --loglevel=info \
  -Q email_queue,longrunning_queue \
  --concurrency=2
```

---

## Testing

### Jest Unit Tests — 41 tests, 5 suites

Run from `client/`:
```bash
npm test
# runs: react-scripts test --watchAll=false --coverage
```

| Suite | Tests | Coverage |
|---|---|---|
| `Home.test.jsx` | 9 | `Home.jsx` 100% statements |
| `CountryPage.test.jsx` | 9 | `CountryPage.jsx` 84% |
| `SectionPage.test.jsx` | 10 | `SectionPage.jsx` 83% |
| `SummaryStats.test.jsx` | 7 | `SummaryStats.jsx` 100% |
| `PriceHistoryChart.test.jsx` | 7 | `PriceHistoryChart.jsx` 92% |

All axios calls mocked with `jest.mock('axios')`. Recharts mocked inline to avoid JSDOM/ResizeObserver issues.

### Cypress E2E Tests — 14 tests, 3 suites

> Requires both `npm start` (port 3000) and Express backend (port 4000) running.

```bash
cd client
npm run cypress:open   # interactive
npm run cypress:run    # headless
```

| Suite | Tests |
|---|---|
| `homepage.cy.js` | 5 — heading, stat cards, country grid, tables |
| `navigation.cy.js` | 5 — Countries, Sections, Research, country page, section page |
| `countryPage.cy.js` | 4 — card click, company table, row expand, tab switch |

---

## Documentation & Testing artifacts

| File | Description |
|---|---|
| `openapi.yaml` | OpenAPI 3.0 spec for the Python analytics API |
| `postman_collection.json` | Postman collection — 30 requests across all APIs |
| `README_LAB1_WebAppDevelopmentTechnology.md` | Lab 1 report — backend architecture, Docker, data pipeline |
| `README_LAB2_WebInterfaceProgramming.md` | Lab 2 report — React frontend, component structure |
| `README_LAB3_WebInterfaceTesting.md` | Lab 3 report — Jest unit tests + Cypress E2E tests |
| `README_RGR_AsyncTasks.md` | РГР report — Celery async tasks, Redis, WebSocket |

---

## Database schema

```sql
companies     — ticker, name, country, sector, exchange
daily_prices  — ticker, date, open, high, low, close, volume, currency
forecasts     — ticker, forecast_date, predicted_close, lower_bound, upper_bound, model
task_results  — task_id, operation, input_data, result, status, completed_at, created_at
```

---

## Project structure

```
├── analytics/              Python FastAPI service
│   └── app/
│       ├── main.py         App entry point, WebSocket, lifespan
│       ├── db.py           SQLAlchemy connection + fetch_df helper
│       ├── celery_app.py   Celery instance, two queues
│       ├── tasks.py        send_email_notification, run_market_analysis
│       ├── static/
│       │   └── admin.html  Async task admin dashboard
│       └── routers/
│           ├── summary.py  Descriptive statistics
│           ├── rolling.py  Rolling moving average
│           ├── forecast.py ARIMA forecasting
│           └── tasks.py    Task trigger + status + history endpoints
├── client/                 React frontend
│   └── src/
│       ├── __tests__/      Jest unit tests (41 tests)
│       ├── pages/          Home, Countries, Sections, country/*, section/*
│       └── components/     PriceHistoryChart, ForecastChart, SummaryStats, …
│   └── cypress/e2e/        Cypress E2E tests (14 tests)
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
├── docker-compose.yml      All services: postgres, redis, node-api, python-api,
│                           celery-worker, flower, client
├── postman_collection.json Full API collection (30 requests)
└── openapi.yaml            OpenAPI 3.0 spec for analytics API
```

---

## Data sources

- **Yahoo Finance** — free OHLCV chart API, no key required
- **Twelve Data** — fallback source, free tier (800 req/day)
- **World Bank API** — macro indicators, no key required

---

## Roadmap

- **Stage 1 ✅ Complete:** Real data, 2y history, ARIMA forecasting, descriptive analytics, async task infrastructure (Celery + Redis + WebSocket), Jest unit tests (41), Cypress E2E tests (14)
- **Stage 2:** Regression, clustering (K-means), anomaly detection, PostgreSQL migrations, Docker staging
- **Stage 3:** LSTM deep learning, NLP sentiment (FinBERT), macro integration (World Bank), XGBoost ensemble
