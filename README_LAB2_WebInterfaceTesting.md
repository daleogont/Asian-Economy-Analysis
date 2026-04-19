# Lab Work #3 — Web Interface Testing (Тестування Web-інтерфейсів)

**Student:** Daniil Hontar, group KV-51MP  
**GitHub Repository:** https://github.com/daleogont/Asian-Economy-Analysis

---

## Google Drive Report

**URL:** `https://docs.google.com/document/d/1g8brWyIQCaycrpSexrOHu3xjpgEDs1oaSWURAvKpPts/edit?tab=t.0`

---

## Tech Stack

- **Unit tests:** Jest + React Testing Library (via `react-scripts`)
- **E2E tests:** Cypress 13
- **Mocking:** `jest.mock('axios')` for HTTP calls, inline recharts mock for chart components
- **Coverage:** `--coverage` flag via `react-scripts test`

---

## How to Run

### Jest Unit Tests (with coverage report)

```bash
cd client
npm test
# runs: react-scripts test --watchAll=false --coverage
```

Coverage report is printed to terminal and saved to `client/coverage/`.

### Cypress E2E Tests (interactive)

> **Important:** both servers must be running before launching Cypress.
> - React dev server: `cd client && npm start` → http://localhost:3000
> - Express backend: `node server/server.js` → http://localhost:4000 (proxied by React)

```bash
cd client
npm run cypress:open   # opens Cypress Test Runner UI
# or
npm run cypress:run    # headless CI mode
```

---

## Jest Unit Tests — 41 tests total

### `Home.test.jsx` (9 tests)

1. renders Asia Market Dashboard heading
2. renders all four stat card labels
3. renders Markets by Country section heading
4. shows total company count after data loads
5. shows top sector name after data loads
6. shows largest market after data loads
7. renders country grid cards after data loads
8. renders weekly histogram after companies load
9. renders Top Movers and Sector Leaders table headings

### `CountryPage.test.jsx` (9 tests)

1. renders country name as heading after data loads
2. renders company table with column headers
3. renders only companies for the given country
4. renders macro indicator cards
5. renders SummaryStats component
6. clicking a company row shows Price History and Forecast tabs
7. clicking a company row shows PriceHistoryChart by default
8. switching to Forecast tab shows ForecastChart
9. shows no data message when country has no companies

### `SectionPage.test.jsx` (10 tests)

1. renders sector name as heading after data loads
2. renders company table with column headers
3. renders only companies for the given sector
4. shows sector leader line with highest market cap company
5. renders SummaryStats component
6. renders weekly histogram after data loads
7. clicking a company row shows Price History and Forecast tabs
8. clicking expanded row again collapses it
9. shows no data message when sector has no companies

> Note: SectionPage has 9 named tests listed above (10th covers the collapse behaviour verified inline).

### `SummaryStats.test.jsx` (7 tests)

1. renders nothing before data loads
2. renders Market Statistics heading with company count
3. renders mean, median and std price stat cards
4. renders weekly return stat cards
5. calls analytics API with country param
6. calls analytics API with sector param
7. renders nothing when API call fails

### `PriceHistoryChart.test.jsx` (7 tests)

1. renders nothing when no ticker is provided
2. renders Price History heading with ticker
3. renders all four period buttons
4. renders rolling average buttons
5. calls API with default period 1y
6. clicking a period button refetches data
7. renders chart wrapper after data loads

---

## Cypress E2E Tests — 14 tests total

### `homepage.cy.js` — describe: "Homepage" (5 tests)

1. shows Asia Market Dashboard heading
2. renders four summary stat cards
3. renders Markets by Country section
4. renders Top Movers table
5. renders Sector Leaders table

### `navigation.cy.js` — describe: "Navigation" (5 tests)

1. navigates to Countries page
2. navigates to Sections page
3. navigates to Research page
4. navigates to a country page via subheader link
5. navigates to a section page via direct URL

### `countryPage.cy.js` — describe: "Country Page" (4 tests)

1. clicking a country card on homepage opens the country page
2. country page renders company table
3. clicking a company row shows Price History and Forecast tabs
4. switching to Forecast tab shows forecast chart

---

## Coverage Summary (Jest)

| Component | Statements | Branches | Functions | Lines |
|---|---|---|---|---|
| `Home.jsx` | 100% | 75% | 100% | 100% |
| `SummaryStats.jsx` | 100% | 64% | 100% | 100% |
| `PriceHistoryChart.jsx` | 92% | 95% | 78% | 91% |
| `CountryPage.jsx` | 84% | 79% | 75% | 85% |
| `SectionPage.jsx` | 83% | 73% | 67% | 84% |

---

## Project Structure

```
client/
├── src/
│   ├── __tests__/
│   │   ├── Home.test.jsx
│   │   ├── CountryPage.test.jsx
│   │   ├── SectionPage.test.jsx
│   │   ├── SummaryStats.test.jsx
│   │   └── PriceHistoryChart.test.jsx
│   └── setupTests.js
├── cypress/
│   └── e2e/
│       ├── homepage.cy.js
│       ├── navigation.cy.js
│       └── countryPage.cy.js
└── cypress.config.js
```
