# РГР — Web Application Development Technology
## Організація виконання асинхронних задач

**Student:** Daniil Hontar, group KV-51MP  
**GitHub Repository:** https://github.com/daleogont/Asian-Economy-Analysis

---

## Google Drive Report

**URL:** `https://docs.google.com/document/d/1trda7YwKVgQBy4OTbQgBQ4ONMaccDsWqYRm4kOAipGo/edit?tab=t.0`

---

## Overview

This РГР extends the existing Python FastAPI analytics service (`analytics/`) with a Celery-based async task infrastructure backed by Redis. Two task queues handle different workload classes. A WebSocket endpoint broadcasts real-time task completion events to all connected browser clients. An admin dashboard at `/admin` allows triggering tasks and monitoring results.

No existing endpoints were modified. Node.js, React, and PostgreSQL schema were not touched.

---

## Async Tasks

### `send_email_notification` — queue: `email_queue`

Simulates sending weekly market alert emails to a list of users.

- Accepts a list of user email addresses
- If no top movers are provided, fetches the top 5 weekly gainers from PostgreSQL automatically
- Logs each simulated send with user address and top movers count
- No real SMTP — operation is fully simulated with structured logging
- Saves result to `task_results` PostgreSQL table
- Publishes completion event to Redis `task_events` pub/sub channel

**Trigger:** `POST /tasks/email`

### `run_market_analysis` — queue: `longrunning_queue`

Runs a full descriptive analytics pass across all companies in the database.

- Fetches all tickers and prices in a single optimised SQL query
- Groups results by country using pandas
- Computes per-country: company count, avg price, avg/best/worst weekly return
- Saves result to `task_results` PostgreSQL table
- Publishes completion event to Redis `task_events` pub/sub channel

**Trigger:** `POST /tasks/analysis`

---

## Queue Architecture

```
FastAPI (port 8000)
  ├── POST /tasks/email      → send task to email_queue
  ├── POST /tasks/analysis   → send task to longrunning_queue
  ├── GET  /tasks/status/:id → poll Celery result backend (Redis)
  ├── GET  /tasks/history    → query task_results table (PostgreSQL)
  ├── GET  /admin            → admin dashboard HTML
  └── WS   /ws/tasks         → WebSocket broadcast (Redis pub/sub)
                                        │
                              Redis (broker + result backend + pub/sub)
                                        │
            ┌───────────────────────────┴───────────────────────┐
            │                                                   │
       email_queue                                    longrunning_queue
  send_email_notification                          run_market_analysis
```

---

## How to Run

### With Docker (recommended)

```bash
# Start all services: postgres, redis, python-api, celery-worker, flower, node-api, client
docker compose up --build

# Or in detached mode
docker compose up --build -d
```

Services started:
| Service | URL | Description |
|---|---|---|
| React frontend | http://localhost:3000 | Main application |
| Node.js API | http://localhost:4000 | Market data API |
| Python FastAPI | http://localhost:8000 | Analytics + task API |
| Admin Dashboard | http://localhost:8000/admin | Task admin panel |
| Flower | http://localhost:5555 | Celery task monitor |
| Redis | localhost:6379 | Broker + result backend |

### Start Celery Worker manually (outside Docker)

```bash
cd analytics

# Install dependencies
pip install -r requirements.txt

# Start worker consuming BOTH queues
celery -A app.celery_app:celery_app worker \
  --loglevel=info \
  -Q email_queue,longrunning_queue \
  --concurrency=2

# Or start separate workers per queue
celery -A app.celery_app:celery_app worker --loglevel=info -Q email_queue --concurrency=2
celery -A app.celery_app:celery_app worker --loglevel=info -Q longrunning_queue --concurrency=1

# Start Flower monitoring UI
celery -A app.celery_app:celery_app flower --port=5555 --broker=redis://localhost:6379/0
```

### Environment variables required

| Variable | Value | Description |
|---|---|---|
| `REDIS_URL` | `redis://localhost:6379/0` | Redis broker and result backend |
| `DATABASE_URL` | `postgresql://admin:secret@localhost:5432/asianmarkets` | PostgreSQL connection |

---

## API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| POST | `/tasks/email` | Trigger `send_email_notification` task, returns `task_id` |
| POST | `/tasks/analysis` | Trigger `run_market_analysis` task, returns `task_id` |
| GET | `/tasks/status/{task_id}` | Poll task status and result from Redis |
| GET | `/tasks/history` | Load completed task history from PostgreSQL |
| GET | `/admin` | Admin dashboard HTML page |
| WS | `/ws/tasks` | WebSocket — real-time task completion events |

---

## WebSocket Event Format

When a task completes, a JSON message is broadcast to all connected WebSocket clients:

```json
{
  "task_id": "3f2a1b...",
  "operation": "run_market_analysis",
  "status": "success",
  "result": {
    "countries_analyzed": 14,
    "country_stats": { "Japan": { "company_count": 80, "avg_weekly_return": 1.23 } }
  },
  "completed_at": "2026-04-18T12:00:00+00:00"
}
```

---

## PostgreSQL — `task_results` Table

Created automatically on FastAPI startup (`CREATE TABLE IF NOT EXISTS`).

```sql
CREATE TABLE IF NOT EXISTS task_results (
    task_id      VARCHAR     PRIMARY KEY,
    operation    VARCHAR     NOT NULL,
    input_data   JSONB,
    result       JSONB,
    status       VARCHAR     NOT NULL,
    completed_at TIMESTAMPTZ,
    created_at   TIMESTAMPTZ DEFAULT NOW()
);
```

---

## New Files

```
analytics/
├── app/
│   ├── celery_app.py          Celery instance, two queues, Redis config
│   ├── tasks.py               send_email_notification + run_market_analysis
│   ├── static/
│   │   └── admin.html         Admin dashboard (WebSocket + trigger buttons)
│   ├── main.py                Updated: lifespan, WebSocket, /admin, tasks router
│   └── routers/
│       └── tasks.py           POST /email, POST /analysis, GET /status, GET /history
└── requirements.txt           Added: celery[redis], redis, flower, websockets

docker-compose.yml             Added: redis, celery-worker, flower services
```
