# Lab Work #1 — Web Interface Programming

**Student:** Daniil Hontar
**Group:** KV-51MP
**Project:** Asian Capital Markets Intelligence Platform

---

## Project overview

The frontend of the Asian Capital Markets Intelligence Platform is a single-page application (SPA) built with React. It provides an interactive dashboard for exploring stock market data, analytics, and price forecasts across 14 Asian economies and 272 companies.

The interface consumes two backend APIs — Node.js for raw company data and Python FastAPI for analytics — and renders charts, tables, histograms, and forecast visualizations in real time.

---

## Technology stack

| Technology        | Purpose                                              |
|-------------------|------------------------------------------------------|
| React 18          | Component-based SPA framework                       |
| React Router v6   | Client-side routing (SPA navigation)                |
| Tailwind CSS      | Utility-first styling, responsive layout            |
| Recharts          | Chart library (line charts, bar charts, histograms) |
| Axios             | HTTP client for API requests                        |
| Nginx             | Serves the production build, proxies API requests   |
| Docker            | Containerized build and deployment                  |

---

## Application pages

### Implemented pages

#### `Home` — `/`
Platform-wide dashboard.
- Summary cards: total companies, average weekly return, top sector, largest market
- **Weekly return distribution histogram** — all 272 companies, green/red bars
- Country grid with flags, company count, weekly return indicator
- Top Movers table (top 5 weekly gainers)
- Sector Leaders table (highest-priced company per sector)

#### `Countries` — `/countries`
Grid overview of all 14 countries with flags, company counts, and average returns. Each card links to the country detail page.

#### `CountryPage` — `/country/:slug`
Detailed view for a single country (e.g. `/country/japan`, `/country/south-korea`).
- Macro indicators: GDP, population, unemployment rate (World Bank API)
- Market statistics cards: avg price, median price, std dev, avg weekly return
- **Weekly return histogram** for companies in that country
- Sortable company table: stock price, weekly return with color indicators
- Click any company row to expand:
  - **Price History tab** — line chart with period selector (3m / 6m / 1y / 2y) and rolling average toggle (7d / 30d)
  - **Forecast tab** — ARIMA(1,1,1) chart with actual prices + forecast line + 95% CI bands, days selector (7 / 14 / 30 / 60)
- Loading state while fetching, error state on API failure, empty state if no data

**Available country pages:**
China, Hong Kong, India, Indonesia, Japan, Malaysia, Pakistan, Saudi Arabia, Singapore, South Korea, Taiwan, Thailand, UAE, Vietnam

#### `Sections` — `/sections`
Grid overview of all 11 GICS sectors with company counts and average returns. Each card links to the sector detail page.

#### `SectionPage` — `/section/:slug`
Detailed view for a single sector (e.g. `/section/financials`, `/section/information-technology`).
- Sector leader banner (company with highest stock price in sector)
- Market statistics cards: avg price, median price, std dev, weekly return range
- **Weekly return histogram** for companies in that sector
- Company table with stock price and weekly return (same expand/collapse behavior as CountryPage)
- Price History and Forecast charts per selected company
- Loading, error, and empty states

**Available sector pages:**
Communication Services, Consumer Discretionary, Consumer Staples, Energy, Financials, Health Care, Industrials, Information Technology, Materials, Real Estate, Utilities


---

## Component library

| Component               | Description                                                  |
|-------------------------|--------------------------------------------------------------|
| `Header`                | Top navigation bar with logo and main links                  |
| `Subheader`             | Dropdown menus for Sectors and Countries                     |
| `Footer`                | Site footer                                                  |
| `Loader`                | Full-screen spinner shown while server health check runs     |
| `WeeklyReturnHistogram` | Bar chart histogram of return distribution (green/red bars)  |
| `WeeklyReturnIndicator` | Inline color-coded return badge with arrow                   |
| `PriceHistoryChart`     | Line chart: close price + optional rolling average           |
| `ForecastChart`         | Line chart: historical + ARIMA forecast + CI bands           |
| `SummaryStats`          | Stat cards (mean, median, std dev, best/worst return)        |

---

## Routing structure

```
/                          Home dashboard
/countries                 All countries grid
/country/japan             Japan detail page
/country/china             China detail page
/country/hong-kong         Hong Kong detail page
/country/india             India detail page
/country/indonesia         Indonesia detail page
/country/malaysia          Malaysia detail page
/country/pakistan          Pakistan detail page
/country/saudi-arabia      Saudi Arabia detail page
/country/singapore         Singapore detail page
/country/south-korea       South Korea detail page
/country/taiwan            Taiwan detail page
/country/thailand          Thailand detail page
/country/uae               UAE detail page
/country/vietnam           Vietnam detail page
/sections                  All sectors grid
/section/financials
/section/information-technology
/section/energy
/section/health-care
/section/real-estate
/section/utilities
/section/industrials
/section/consumer-discretionary
/section/consumer-staples
/section/materials
/section/communication-services
/research                  Research articles page
```

---

## UI/UX features

- **Responsive layout** — tested in Chrome DevTools across mobile (375px), tablet (768px), and desktop (1280px+) breakpoints using Tailwind's `sm:`, `md:`, `lg:` prefixes
- **Loading states** — spinner/message on all async data fetches (country pages, sector pages, charts)
- **Error states** — red message displayed if API call fails, with clear human-readable text
- **Empty states** — graceful "No data available" message if a country/sector returns zero companies
- **Interactive charts** — hover tooltips on all Recharts components with formatted values
- **Expand/collapse rows** — click a company row in any table to toggle price history and forecast charts inline
- **Tab navigation** — History / Forecast tabs within expanded company rows

---

## Build and deployment

The React app is built with `react-scripts build` and served by Nginx inside a Docker container.

Nginx proxies API requests:
```nginx
location /api/        { proxy_pass http://node-api:4000; }
location /analytics/  { proxy_pass http://python-api:8000; }
location /            { try_files $uri /index.html; }
```

This ensures all `/api/*` and `/analytics/*` requests go to the correct backend while React Router handles all other routes on the client side.

```bash
# Build and start frontend container
docker compose build client
docker compose up -d client

# Open in browser
open http://localhost:3000
```

---

## Google Drive Report

**URL:** `https://docs.google.com/document/d/18gOlfxCOEoCAH0wK0i6AukZG3dvCwd8ZOLh2xnFPW1g/edit?tab=t.0`
