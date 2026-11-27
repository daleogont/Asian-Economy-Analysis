# Asian Capital Markets Intelligence Platform

A full-stack analytical platform for monitoring and forecasting stock market dynamics across
14 Asian economies. Built as a dissertation project combining real financial data, descriptive
analytics, nine interchangeable forecasting models with cost/accuracy benchmarking, unsupervised
ML (clustering, anomaly detection, correlation networks), and async task infrastructure.

**Live coverage:** 272 companies · 14 countries · 11 sectors · 5+ years of daily OHLCV history (346k+ rows)

---

## What it does

**Market data & dashboards**
- Latest stock prices, weekly returns, country/sector aggregates, top movers, sector leaders
- Macro indicators (GDP, population, unemployment) via the World Bank API, for 10 of the 14 countries
- Price history charts with configurable rolling moving averages
- Summary statistics (mean, median, std, min, max) per country and/or sector
- Weekly return distribution histograms

**Forecasting**
- One endpoint, nine interchangeable models: `arima`, `ets`, `sarima`, `prophet`, `ridge`,
  `random_forest`, `xgboost`, `lstm`, and a `naive` random-walk baseline every other model is
  scored against
- Every model reports the same cost metrics alongside its forecast — inference latency, train
  time, memory — plus holdout RMSE/MAE, so accuracy and compute cost are comparable model-to-model
- `enriched=true` adds fundamentals (P/E, beta, market cap, dividend yield) and macro features
  (GDP, unemployment) to the lagged-feature models (ridge/random_forest/xgboost)
- `random_forest`/`xgboost`/`lstm` responses are cached in Redis for 24h, with an `X-Cache`
  response header reporting HIT/MISS; the cache is flushed automatically by the nightly
  delta-fetch job
- Rolling-origin cross-validation and multi-ticker × multi-model batch benchmarking (with
  Friedman + pairwise Wilcoxon-Holm significance testing), both always asynchronous via Celery

**Cross-company analytics**
- Pairwise correlation of daily returns, with an optional hierarchical-clustering leaf order for
  heatmaps
- Anomaly detection on weekly returns (IsolationForest + Z-score, with an optional third
  kNN-distance detector)
- K-means clustering of all companies on return/volatility behavior
- Minimum spanning tree over the correlation-distance matrix, for network visualizations
- Nearest-neighbor "similar companies" lookup, in either feature space or correlation space

**Infrastructure**
- Async email notification and market analysis tasks via Celery + Redis, with a generic
  status/history API
- Real-time task completion events over WebSocket, consumed by a static admin dashboard
- Flower dashboard for live Celery queue/worker inspection

---

## Architecture

```
Browser (React)
     │
     ▼
Nginx (port 3000)
  ├── /api/*          → Node.js / Express   (port 4000)
  │                      proxies to companies/countries/sectors/market-overview/
  │                      top-movers/macros/history/fundamentals/health
  └── /analytics/*    → Python FastAPI      (port 8000)
                          summary/rolling/forecast/models/correlation/anomalies/
                          clusters/network/similar/validation/batch-benchmark

Direct only — no Nginx route (call port 8000 on the python-api container itself):
  /health   /admin   /tasks/*   /internal/*   /ws/tasks (WebSocket)

Node.js ──────▶ PostgreSQL (port 5432)            Python FastAPI ──────▶ same PostgreSQL
(reads)         346k+ daily price rows, companies,                       (reads + writes
                fundamentals, task_results                                task_results)

Celery Worker  ←→  Redis (broker + result backend + pub/sub + forecast cache)
Flower UI (port 5555)
```

The two backends are independent processes with no shared code — this repo's `openapi.yaml`
documents both under one file, with per-path `servers` entries since they're reachable at
different hosts/ports.

---

## Tech stack

| Layer          | Technology                                                                  |
|----------------|------------------------------------------------------------------------------|
| Frontend       | React 19, React Router 7, Tailwind CSS, Recharts, d3-force                  |
| API Gateway    | Node.js, Express, node-cron                                                 |
| Analytics API  | Python 3.11, FastAPI, pandas, numpy                                        |
| Forecasting    | statsmodels (ARIMA/ETS/SARIMAX), Prophet, scikit-learn (Ridge/RF/kNN/clustering), XGBoost, PyTorch (LSTM) |
| Async tasks    | Celery 5.3, Redis 7, Flower                                                  |
| Database       | PostgreSQL 16                                                               |
| Data sources   | Yahoo Finance, Twelve Data, World Bank API                                  |
| Infra          | Docker, Docker Compose, Nginx                                               |
| Testing        | Jest + React Testing Library, Cypress 13, pytest                            |

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

# Collect daily price history for every ticker (long-running; deltaFetch keeps it current after this)
node scripts/collectHistory.js

# Collect fundamentals (P/E, beta, market cap, dividend yield) for every ticker
node scripts/collectFundamentals.js
```

Open `http://localhost:3000`

| URL                          | Service                                            |
|-------------------------------|-----------------------------------------------------|
| http://localhost:3000         | React frontend                                       |
| http://localhost:4000         | Node.js API (direct)                                 |
| http://localhost:8000         | Python FastAPI + analytics (direct)                  |
| http://localhost:8000/admin   | Async task admin dashboard                           |
| http://localhost:8000/docs    | FastAPI's own auto-generated Swagger UI              |
| http://localhost:5555         | Flower — Celery task monitor                         |

---

## Environment variables

| Variable            | Required | Description                                                |
|---------------------|----------|--------------------------------------------------------------|
| `TWELVE_DATA_KEY`   | No       | Twelve Data API key (fallback when Yahoo Finance fails)      |
| `POSTGRES_DB`       | Yes      | Database name (default: `asianmarkets`)                      |
| `POSTGRES_USER`     | Yes      | DB user (default: `admin`)                                   |
| `POSTGRES_PASSWORD` | Yes      | DB password (default: `secret`)                               |
| `DATABASE_URL`      | Yes      | Full PostgreSQL connection string                              |
| `REDIS_URL`         | Yes      | Redis connection string (default: `redis://redis:6379/0`)      |
| `PORT`              | No       | Node.js server port (default: `4000`)                         |

---

## API reference

Full, verified-against-source documentation lives in **`openapi.yaml`** (validates clean with
`npx @redocly/cli lint openapi.yaml`) and **`postman_collection.json`** — both cover the Node
gateway and the Python analytics service. The tables below are a quick-reference summary.

### Node.js gateway (`/api/*`)

| Method | Endpoint                                | Description                                               |
|--------|------------------------------------------|-------------------------------------------------------------|
| GET    | `/api/health`                            | Gateway status + in-memory price-cache composition          |
| GET    | `/api/companies`                         | All companies with a valid price, latest price + weekly return |
| GET    | `/api/countries`                         | Per-country aggregates (company count, sector breakdown, avg return) |
| GET    | `/api/sectors`                           | Per-sector aggregates                                       |
| GET    | `/api/sector-leaders`                    | Highest-*price* company per sector (currency-naive, not market cap) |
| GET    | `/api/market-overview`                   | Platform-wide totals                                        |
| GET    | `/api/top-movers?count=5&direction=up`   | Top gainers or losers by weekly return                      |
| GET    | `/api/macros?country=Japan`              | GDP, population, unemployment (World Bank; 10 of 14 countries) |
| GET    | `/api/history/:ticker?period=1y`         | Raw OHLCV history (3m / 6m / 1y / 2y)                        |
| GET    | `/api/fundamentals/:ticker`               | Stored P/E, EPS, dividend yield, beta, market cap            |

### Python analytics API (`/analytics/*`, `/health`, `/internal/*`)

| Method | Endpoint                                                  | Description                                            |
|--------|-------------------------------------------------------------|------------------------------------------------------------|
| GET    | `/health`                                                    | FastAPI health check                                      |
| GET    | `/analytics/summary?country=&sector=`                        | Mean, median, std, min, max for price and weekly return   |
| GET    | `/analytics/rolling/:ticker?window=30&period=1y`              | Close prices + N-day rolling moving average               |
| GET    | `/analytics/forecast/:ticker?days=30`                         | ARIMA(1,1,1)-only forecast (legacy, kept for compatibility)|
| GET    | `/analytics/models/forecast/:ticker?model=&days=&enriched=`   | Any of the 9 models + cost metrics; `X-Cache` on cached ones |
| GET    | `/analytics/correlation?country=&order=`                      | Pairwise return correlation, optional clustered leaf order |
| GET    | `/analytics/anomalies?country=&include_knn=`                   | IsolationForest + Z-score (+ optional kNN) anomaly flags   |
| GET    | `/analytics/clusters?n_clusters=5`                             | K-means clustering on return/volatility, market-wide        |
| GET    | `/analytics/network?country=`                                  | Minimum spanning tree over correlation distance            |
| GET    | `/analytics/similar/:ticker?space=&scope=`                     | Nearest companies by feature or correlation distance       |
| POST   | `/analytics/validation/rolling/:ticker`                        | Start rolling-origin CV (async) — returns `task_id`         |
| POST   | `/analytics/batch-benchmark`                                    | Start a ticker × model benchmark (async) — returns `task_id`|
| GET    | `/analytics/batch-benchmark/:task_id/status`                   | Progress-aware status (`{done, total}`)                    |
| GET    | `/analytics/batch-benchmark/:task_id/results`                  | Final benchmark results + optional significance stats       |
| GET    | `/internal/fundamentals/:ticker`                                | Internal-only — live yfinance fetch (used by the collector script) |
| DELETE | `/internal/cache/invalidate`                                    | Internal-only — flushes the forecast cache (used by deltaFetch) |

### Async Tasks API (`/tasks/*`)

| Method    | Endpoint                    | Description                                              |
|-----------|-----------------------------|----------------------------------------------------------|
| POST      | `/tasks/email`               | Trigger email notification task → returns `task_id`      |
| POST      | `/tasks/analysis`             | Trigger full market analysis task → returns `task_id`     |
| GET       | `/tasks/status/{task_id}`     | Generic poll — works for any task queued by this API      |
| GET       | `/tasks/history`              | Load completed task history from PostgreSQL               |
| GET       | `/admin`                       | Admin dashboard HTML                                      |
| WebSocket | `/ws/tasks`                    | Real-time task completion broadcast (Redis pub/sub)        |

None of the above requires authentication — the services sit behind Docker's network boundary,
with no auth layer in front of either backend. **Important:** `/health`, `/admin`, `/tasks/*`,
`/internal/*`, and `/ws/tasks` are *not* reachable through the Nginx proxy on port 3000 — only
`/api/*` and `/analytics/*` have an Nginx route. Call port 8000 directly for the rest.

---

## Async Tasks

The analytics service uses **Celery 5.3** with **Redis 7** as broker and result backend. Named
queues separate workload classes:

| Queue               | Tasks                                                                | Description |
|---------------------|-----------------------------------------------------------------------|---|
| `email_queue`       | `send_email_notification`                                             | Simulates weekly market alert emails (no real email sent). Fetches top 5 movers from the DB automatically if none are provided. |
| `longrunning_queue` | `run_market_analysis`, `run_rolling_validation`, `run_batch_benchmark` | Per-country aggregate stats; rolling-origin cross-validation; multi-ticker × multi-model benchmarking. |

**Real-time events:** when a task completes, the worker publishes a JSON event to a Redis
`task_events` pub/sub channel. FastAPI's async listener forwards it to every connected
WebSocket client (`/ws/tasks`) instantly — the admin dashboard uses this instead of polling.

**Persistence:** every completed task is saved to the `task_results` PostgreSQL table (created
automatically on startup), so `GET /tasks/history` can load past results.

**Start Celery worker manually:**
```bash
celery -A app.celery_app:celery_app worker \
  --loglevel=info \
  -Q email_queue,longrunning_queue \
  --concurrency=2
```

---

## Testing

### Jest unit tests — 48 tests

Run from `client/`:
```bash
npm test
# runs: react-scripts test --watchAll=false --coverage
```

Covers `Home`, `CountryPage`, `SectionPage`, `SummaryStats`, `PriceHistoryChart`, and the
client-side model-comparison score utility (`utils/score.js`). All axios calls mocked with
`jest.mock('axios')`; Recharts mocked inline to avoid JSDOM/ResizeObserver issues.

### Cypress E2E tests — 14 tests, 3 suites

> Requires both `npm start` (port 3000) and the Express backend (port 4000) running.

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

### Python tests — pytest, 55 test functions

Run from `analytics/`:
```bash
pytest
```

Covers the ML routers (correlation/anomalies/clusters/network/similar/kNN), the base forecast
model's metrics contract, the naive baseline, rolling-origin validation, batch benchmarking, the
correlation-distance method, and score-sensitivity analysis for the client-side comparison score.

---

## Documentation & research artifacts

| File / directory | Description |
|---|---|
| `openapi.yaml` | OpenAPI 3.0 spec covering both the Python analytics API and the Node.js gateway |
| `postman_collection.json` | Postman collection (v2.1.0 schema) — every endpoint above, with descriptions, example parameters, and a test script on the model-forecast requests |
| `research/` | Standalone rolling-origin benchmark for the written paper — runs outside Docker against the production model classes, read-only (see `research/README.md`) |
| `research/legacy/benchmark_results.csv` | Early 80/20 holdout 30-ticker × 4-model benchmark output, superseded by the rolling-origin benchmark in `research/results/` |
| `README_LAB1_WebAppDevelopmentTechnology.md` | Lab 1 report — backend architecture, Docker, data pipeline |
| `README_LAB2_WebInterfaceProgramming.md` | Lab 2 report — React frontend, component structure |
| `README_LAB3_WebInterfaceTesting.md` | Lab 3 report — Jest unit tests + Cypress E2E tests |
| `README_RGR_AsyncTasks.md` | РГР report — Celery async tasks, Redis, WebSocket |

---

## Database schema

```sql
companies      — ticker, name, country, sector, exchange
daily_prices   — ticker, date, open, high, low, close, volume, currency   (346k+ rows)
fundamentals   — ticker, pe_ratio, eps, dividend_yield, beta, market_cap, fetched_at
task_results   — task_id, operation, input_data, result, status, completed_at, created_at
forecasts      — ticker, forecast_date, predicted_close, lower_bound, upper_bound, model
                 (defined in schema.sql; not currently written by any endpoint —
                 forecasts are computed on demand and cached in Redis instead)
```

---

## Project structure

```
├── analytics/               Python FastAPI service
│   ├── app/
│   │   ├── main.py          App entry point, WebSocket, lifespan, LSTM warmup
│   │   ├── db.py            SQLAlchemy connection + fetch_df helper
│   │   ├── cache.py         Redis client + forecast cache key helper
│   │   ├── celery_app.py    Celery instance, two queues
│   │   ├── tasks.py         send_email_notification, run_market_analysis,
│   │   │                    run_rolling_validation, run_batch_benchmark
│   │   ├── validation.py    Rolling-origin cross-validation engine
│   │   ├── batch_benchmark.py  Single-holdout benchmark + Friedman/Wilcoxon-Holm stats
│   │   ├── models/          ArimaModel, EtsModel, SarimaModel, ProphetModel, RidgeModel,
│   │   │                    RandomForestModel, XgboostModel, LstmModel, NaiveModel
│   │   ├── static/admin.html   Async task admin dashboard
│   │   └── routers/
│   │       ├── summary.py / rolling.py / forecast.py   Descriptive stats, rolling MA, legacy ARIMA
│   │       ├── models.py        Unified multi-model forecast + CE metrics + Redis cache
│   │       ├── analytics_ml.py  Correlation, anomalies (+kNN), clusters, network, similar
│   │       ├── validation.py / batch_benchmark.py   Async validation & benchmarking endpoints
│   │       ├── internal.py      Internal-only fundamentals fetch + cache invalidation
│   │       └── tasks.py         Task trigger + status + history endpoints
│   ├── tests/                55 pytest test functions
│   └── scripts/              score_sensitivity.py and other analysis scripts
├── client/                   React frontend
│   └── src/
│       ├── __tests__/        Jest unit tests (48 tests)
│       ├── pages/             Home, Countries, Sections, Research, ModelComparison,
│       │                      BatchBenchmark, country/*, section/*
│       ├── components/        PriceHistoryChart, ForecastChart, ClusterScatter,
│       │                      CompanyNetwork, ParetoChart, SummaryStats, …
│       └── utils/score.js     Client-side model-comparison scoring (accuracy vs. cost tradeoff)
│   └── cypress/e2e/           Cypress E2E tests (14 tests)
├── server/                    Node.js gateway
│   ├── controllers/           Business logic per route
│   ├── routes/                Express route definitions (companies, countries, sectors,
│   │                          sector-leaders, market-overview, top-movers, macro, history,
│   │                          fundamentals, health)
│   └── utils/
│       ├── db.js              PostgreSQL pool
│       ├── dataService.js     Yahoo Finance / Twelve Data fetcher + cache prewarm
│       ├── deltaFetch.js       Daily incremental price updater + forecast-cache invalidation
│       └── stockQueries.js     DB query helpers
├── scripts/
│   ├── seedCompanies.js       One-time company seeding
│   ├── collectHistory.js       Full OHLCV history collection
│   ├── backfillHistory.js      Historical backfill helper
│   ├── collectFundamentals.js  Calls the Python service's internal yfinance endpoint, upserts
│   └── fetchAllToCache.js      Cache prewarm helper
├── research/                   Standalone rolling-origin benchmark for the written paper
├── data/
│   ├── realCompanies.json      Master company registry (272 companies)
│   └── schema.sql               PostgreSQL schema
├── docker-compose.yml           All services: postgres, redis, node-api, python-api,
│                                celery-worker, flower, client
├── postman_collection.json       Full API collection (Node + Python, with test scripts)
└── openapi.yaml                  OpenAPI 3.0 spec for both backends
```

---

## Data sources

- **Yahoo Finance** — free OHLCV chart API, no key required
- **Twelve Data** — fallback source, free tier (800 req/day)
- **World Bank API** — macro indicators, no key required (10 of the 14 countries mapped)

---

## Status

All three originally-planned stages are implemented and running: real market data with a
multi-year history, nine forecasting models with cost/accuracy benchmarking (ARIMA, ETS,
SARIMA, Prophet, Ridge, Random Forest, XGBoost, LSTM, naive baseline), fundamentals/macro
feature enrichment, correlation/anomaly/cluster/network analytics, rolling-origin validation
and batch benchmarking with significance testing, async task infrastructure (Celery + Redis +
WebSocket), and a Jest/Cypress/pytest test suite across all three services.

`research/` holds a standalone benchmark built for the accompanying written paper, kept
deliberately isolated from the production code path it reads from.
