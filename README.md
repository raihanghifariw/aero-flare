# Aero-Flare 🔥

<p align="center">
  <strong>Autonomous Wildfire Intelligence & Multimodal Satellite Triage Platform</strong>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Next.js-14.2-black?style=flat-square&logo=next.js" alt="Next.js 14" />
  <img src="https://img.shields.io/badge/FastAPI-0.111-009688?style=flat-square&logo=fastapi" alt="FastAPI" />
  <img src="https://img.shields.io/badge/Python-3.10+-3776AB?style=flat-square&logo=python" alt="Python 3.10+" />
  <img src="https://img.shields.io/badge/TypeScript-5.5-3178C6?style=flat-square&logo=typescript" alt="TypeScript" />
  <img src="https://img.shields.io/badge/TailwindCSS-3.4-38B2AC?style=flat-square&logo=tailwind-css" alt="TailwindCSS" />
  <img src="https://img.shields.io/badge/Leaflet-1.9-199900?style=flat-square&logo=leaflet" alt="Leaflet" />
  <img src="https://img.shields.io/badge/XGBoost-2.0-FF6F00?style=flat-square" alt="XGBoost" />
  <img src="https://img.shields.io/badge/Redis-7.2-red?style=flat-square&logo=redis" alt="Redis" />
  <img src="https://img.shields.io/badge/Celery-5.4-green?style=flat-square&logo=celery" alt="Celery" />
  <img src="https://img.shields.io/badge/Docker-Enabled-2496ED?style=flat-square&logo=docker" alt="Docker" />
  <img src="https://img.shields.io/badge/License-MIT-blue.svg?style=flat-square" alt="License" />
</p>

---

## Overview

**Aero-Flare** is a real-time, automated wildfire detection, satellite triage, and spread-forecasting platform engineered for high-risk peatland and forested regions across Indonesia (Kalimantan, Sumatra, Sulawesi, Papua, and Jawa-Bali).

The system continuously pulls Near-Real-Time (NRT) thermal anomaly vectors from **NASA FIRMS** (MODIS & VIIRS) via a scheduled **Celery Beat** cron job. For each hotspot, it dispatches background tasks to retrieve corresponding optical satellite tiles via **NASA GIBS**, execute multimodal AI computer-vision triage using Vision-Language Models (**Qwen2-VL**), and forecast multi-horizon fire spread with **XGBoost**. API responses and aggregated metrics are cached in a high-performance **Redis** layer for sub-millisecond response times, and alert dispatchers send instantaneous notifications via Telegram and Webhooks to emergency response teams.

---

## Key Features

- **🛰️ Autonomous Satellite Ingestion**: Scheduled telemetry ingestion from NASA FIRMS with multi-sensor deduplication (SNPP, NOAA-20, NOAA-21, Aqua, Terra).
- **👁️ Multimodal Visual Triage (VLM)**: Automated visual verification of smoke plumes, cloud cover, and active flames using Vision-Language Models with rule-based fallback.
- **📈 ML Spread Radar & Forecasting**: Gradient-boosted machine learning model predicting fire spread direction and 6h / 12h / 24h expansion radiuses based on wind speed, humidity, and terrain metrics.
- **🗺️ Interactive Tactical Command Dashboard**: High-contrast, modern SaaS command center powered by Next.js 14 and Leaflet, featuring OpenStreetMap cartography, Indonesian regional presets, and real-time incident inspection.
- **⚡ Real-time Distributed Cache & Queue (Redis & Celery)**: Asynchronous background worker ingestion/triage pipeline powered by Celery. Dynamic caching with Redis supports sub-millisecond API response times. Auto-fallback to an async in-memory queue/cache is active if Redis is offline.
- **📢 Automated Incident Alerting**: Real-time notification dispatch via Telegram and structured webhooks for rapid emergency response.

---

## System Architecture

```
                       ┌─────────────────────────┐
                       │ NASA FIRMS / GIBS Feeds │
                       └────────────┬────────────┘
                                    │ (Celery Beat Scheduled Trigger)
                                    ▼
                       ┌─────────────────────────┐
                       │   Celery Ingest Task    │
                       └────────────┬────────────┘
                                    │
                                    ├───► [Redis Message Broker]
                                    │          │
                                    ▼          ▼
                       ┌─────────────────────────┐
                       │  Celery Worker Pool     │
                       │ (Parallel Event Triage) │
                       └────────────┬────────────┘
                                    │
                  ┌─────────────────┴─────────────────┐
                  ▼                                   ▼
       ┌─────────────────────┐             ┌─────────────────────┐
       │   NASA GIBS Tile    │             │   Weather & Terrain  │
       │ Cloudflare R2 Store │             │   Feature Pipeline  │
       └──────────┬──────────┘             └──────────┬──────────┘
                  │                                   │
                  ▼                                   ▼
       ┌─────────────────────┐             ┌─────────────────────┐
       │  Multimodal Triage  │             │   XGBoost Spread    │
       │ (Qwen2-VL / Rules)  │             │ Prediction (6/12/24h│
       └──────────┬──────────┘             └──────────┬──────────┘
                  │                                   │
                  └─────────────────┬─────────────────┘
                                    │ (Write & Invalidate Cache)
                                    ▼
                       ┌─────────────────────────┐
                       │ PostgreSQL / Supabase DB│◄────┐
                       └────────────┬────────────┘     │
                                    │                  │ (Reads & Caching)
                                    ▼                  ▼
                       ┌─────────────────────────┐   ┌─────────────────┐
                       │    FastAPI API Server   │◄─►│   Redis Cache   │
                       └────────────┬────────────┘   └─────────────────┘
                                    │
            ┌───────────────────────┴───────────────────────┐
            ▼                                               ▼
┌─────────────────────────┐                     ┌─────────────────────────┐
│ Next.js 14 Command HUD  │                     │  Emergency Dispatcher   │
│ (Leaflet Map & Explorer)│                     │ (Telegram & Webhooks)   │
└─────────────────────────┘                     └─────────────────────────┘
```

---

## Repository Structure

```
aero-flare/
├── backend/                  # FastAPI Application & Services
│   ├── alembic/              # Database migration scripts
│   ├── app/
│   │   ├── api/v1/           # REST API Route handlers (with caching & async queue triggers)
│   │   ├── core/             # Configuration, DB session, cache.py (Redis), queue.py (task dispatcher)
│   │   ├── models/           # SQLAlchemy ORM database models
│   │   ├── schemas/          # Pydantic validation schemas
│   │   ├── services/         # Ingestion, VLM triage, alerts, ML pipelines
│   │   └── workers/          # Celery background workers (App, tasks, worker entrypoint)
│   ├── ml/                   # Machine learning models & prediction engine
│   ├── scripts/              # Utility scripts (ingest_firms.py, test_redis.py verification)
│   └── tests/                # Unit and integration test suites
│
├── frontend/                 # Next.js 14 Operations Command Center
│   ├── src/
│   │   ├── app/              # App router pages (Dashboard, Incidents Explorer)
│   │   ├── components/       # Tactical Map, HUD panels, charts, UI controls
│   │   ├── hooks/            # SWR telemetry streaming hooks
│   │   └── lib/              # Map constants, API clients, formatters
│   └── tests/                # Playwright E2E test suites
│
├── docker-compose.yml        # Multi-container local development stack (includes redis & worker)
└── Dockerfile                # Production container specifications
```

---

## Tech Stack & Infrastructure

| Layer | Technologies | Role |
|---|---|---|
| **Frontend** | Next.js 14, React 18, Tailwind CSS, Leaflet, SWR, Recharts | Tactical Geospatial Operations HUD |
| **Backend** | FastAPI, Python 3.10+, SQLAlchemy, Alembic, Pydantic v2 | High-throughput Async REST API |
| **Caching & Message Broker** | Redis | Sub-millisecond distributed cache and Celery broker |
| **Task Queue & Scheduler** | Celery, Celery Beat | Background ingestion, triage, and spread task dispatching |
| **Machine Learning** | XGBoost, Scikit-Learn, Ollama (Qwen2-VL) | Multimodal Triage & Fire Spread Prediction |
| **Database** | PostgreSQL / Supabase | Relational Hotspot & Telemetry Store |
| **Object Storage** | Cloudflare R2 | Satellite Tile Cache |
| **Earth Observation** | NASA FIRMS API, NASA GIBS WMTS, OpenStreetMap | Satellite Sensor Imagery & Cartography |

---

## Getting Started

### Prerequisites

- [Docker](https://www.docker.com/) & [Docker Compose](https://docs.docker.com/compose/)
- [Node.js](https://nodejs.org/) 18+ (for local frontend development)
- [Python](https://www.python.org/) 3.10+ (for local backend development)

### Quickstart with Docker Compose

1. **Clone the repository:**
   ```bash
   git clone https://github.com/raihanghifariw/aero-flare.git
   cd aero-flare/aero-flare
   ```

2. **Configure environment variables:**
   ```bash
   cp .env.example .env
   # Populate your NASA FIRMS API key, Telegram Bot token, Database credentials, and Redis config in .env
   ```

3. **Configure Redis & Celery Environment Variables (Optional):**
   ```env
   REDIS_URL=redis://localhost:6379/0
   CACHE_ENABLED=true
   QUEUE_ENABLED=true
   CELERY_BROKER_URL=redis://localhost:6379/0
   CELERY_RESULT_BACKEND=redis://localhost:6379/0
   ```
   *Note: If Redis is unavailable or disabled, the application will automatically fall back to an async in-memory queue (`asyncio.Queue`) and in-memory cache dictionary.*

4. **Launch the stack:**
   ```bash
   docker compose up --build
   ```
   *This starts Next.js frontend, FastAPI backend, Redis cache/broker, Celery worker pool (concurrency=4), and Ollama services simultaneously.*

5. **Access the applications:**
   - **Dashboard**: [http://localhost:3000](http://localhost:3000)
   - **Backend API**: [http://localhost:8000](http://localhost:8000)
   - **Interactive API Docs (Swagger)**: [http://localhost:8000/docs](http://localhost:8000/docs)

### Local Development with Redis & Celery (Without Docker)

For running services individually on your host system:

1. **Start Redis Server:**
   ```bash
   # On macOS
   brew services start redis
   # On Linux / Windows WSL
   redis-server
   ```

2. **Run Celery Worker:**
   ```bash
   cd backend
   celery -A app.workers.celery_app.celery_app worker --loglevel=info --concurrency=4
   ```

3. **Run Celery Beat (Scheduled ingestion triggers every 30m):**
   ```bash
   cd backend
   celery -A app.workers.celery_app.celery_app beat --loglevel=info
   ```

4. **Verify Redis Connectivity & Fallback Handling:**
   Run the verification script to test both the cache and queue connections to Redis:
   ```bash
   cd backend
   python scripts/test_redis.py
   ```

---

## API Specifications

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/v1/health` | Service health status and database connectivity |
| `GET` | `/api/v1/events` | Paginated fire events with status, date, and FRP filters |
| `GET` | `/api/v1/events/{id}` | Detailed incident telemetry by ID |
| `GET` | `/api/v1/triage/{event_id}` | Multimodal AI triage assessment and classification |
| `GET` | `/api/v1/predictions/{event_id}` | XGBoost fire spread forecast (6h, 12h, 24h radiuses) |
| `GET` | `/api/v1/stats` | Aggregate operational statistics (active fires, ingestion health) |

---

## Quality Assurance & Testing

```bash
# Run Backend Unit & Integration Tests (Pytest)
cd backend
pytest tests/unit/ -v

# Run specific tests for Caching & Task Queuing
pytest tests/unit/test_cache.py -v
pytest tests/unit/test_queue.py -v
pytest tests/unit/test_celery_tasks.py -v

# Run Frontend End-to-End Tests (Playwright)
cd frontend
npm run test:e2e
```

---

## License

This project is licensed under the [MIT License](LICENSE).
