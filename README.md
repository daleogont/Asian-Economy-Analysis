# Asian Economy Analysis

A full-stack dashboard for tracking stock market data across 10 Asian economies — Japan, China, India, Thailand, Singapore, South Korea, Malaysia, Indonesia, Taiwan, and Saudi Arabia.

---

## What it does

- Displays live (or cached) stock prices, weekly returns, and market cap for ~183 companies
- Groups companies by country and sector
- Shows macro indicators (GDP, population, unemployment) via World Bank API
- Includes a research page with curated articles for each country
- Interactive Asia map, sector leaders, top movers

---

## Tech stack

| Layer    | Technology |
|----------|------------|
| Frontend | React, Tailwind CSS, Recharts |
| Backend  | Node.js, Express |
| Data     | Yahoo Finance (free), Twelve Data (API key), seed fallback |

---

## Setup

**Requirements:** Node.js 18+

```bash
# Install server dependencies
npm install

# Install client dependencies
npm install --prefix client
```

Create a `.env` file in the project root:

```
TWELVE_DATA_KEY=your_api_key_here
```

---

## Running

```bash
npm run dev        # starts both server (port 4000) and client (port 3000)
npm run server     # server only
npm run client     # client only
```

Open `http://localhost:3000`

---

## How data fetching works

The server uses a **3-tier fallback** strategy:

```
Tier 1 — Yahoo Finance   free, no key required
    ↓ if 429 or error
Tier 2 — Twelve Data     requires API key (800 req/day on free tier)
    ↓ if error
Tier 3 — Seed / cache    static fallback, always available
```

On startup, all tickers without live data are queued for background fetching at 1 request per 8 seconds (~25 min for 183 tickers). The website is immediately usable with seed data while the queue runs.

Live data is saved to `data/cache.json` with a 12-hour TTL. On restart, cached data is loaded instantly — usually 0 re-fetches needed.

---

## API endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/companies` | All companies with stock data |
| GET | `/api/sectors` | Sectors with market weight and weekly return |
| GET | `/api/countries` | Countries with total market cap and avg return |
| GET | `/api/top-movers?count=5&direction=up` | Top gaining or losing stocks |
| GET | `/api/sector-leaders` | Best company per sector by market cap |
| GET | `/api/market-overview` | Aggregated market stats |
| GET | `/api/macros?country=Japan` | GDP, population, unemployment (World Bank) |
| GET | `/api/health` | Server status + cache stats |

---

## Project structure

```
├── client/               React frontend
│   └── src/
│       ├── pages/        Home, Countries, Sections, Research, country/*, section/*
│       └── components/   Shared UI components
├── server/
│   ├── controllers/      Request handlers for each route
│   ├── routes/           Express route definitions
│   └── utils/
│       ├── dataService.js   3-tier fetch logic + background queue
│       ├── cacheStore.js    Persistent in-memory cache with seed fallback
│       └── currencyService.js  USD conversion rates
├── data/
│   ├── realCompanies.json   Master list of 183 companies
│   ├── seed.json            Static price data (fallback)
│   └── cache.json           Live data written at runtime (gitignored)
└── .env                     API keys (gitignored)
```

---

## Environment variables

| Variable | Required | Description |
|----------|----------|-------------|
| `TWELVE_DATA_KEY` | No | Twelve Data API key. Without it, only Yahoo Finance is used. Free tier: 800 req/day. |
| `PORT` | No | Server port (default: 4000) |

---

## Data sources

- **Yahoo Finance** — free chart API, no key needed
- **Twelve Data** — [twelvedata.com](https://twelvedata.com), free tier sufficient
- **World Bank API** — macro indicators, no key needed
- **seed.json** — manually curated fallback prices, used when both live sources fail
