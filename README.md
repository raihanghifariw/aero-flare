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
  <img src="https://img.shields.io/badge/Docker-Enabled-2496ED?style=flat-square&logo=docker" alt="Docker" />
  <img src="https://img.shields.io/badge/License-MIT-blue.svg?style=flat-square" alt="License" />
</p>

---

## Overview

**Aero-Flare** is a real-time, automated wildfire detection, satellite triage, and spread-forecasting platform engineered for high-risk peatland and forested regions across Indonesia (Kalimantan, Sumatra, Sulawesi, Papua, and Jawa-Bali).

The system continuously pulls Near-Real-Time (NRT) thermal anomaly vectors from **NASA FIRMS** (MODIS & VIIRS), extracts corresponding optical satellite tiles via **NASA GIBS**, executes multimodal AI computer-vision triage using Vision-Language Models (**Qwen2-VL**), forecasts multi-horizon fire spread with **XGBoost**, and delivers instantaneous dispatch alerts via Telegram and Webhooks to emergency response teams.

---

## Key Features

- **🛰️ Autonomous Satellite Ingestion**: Scheduled telemetry ingestion from NASA FIRMS with multi-sensor deduplication (SNPP, NOAA-20, NOAA-21, Aqua, Terra).
- **👁️ Multimodal Visual Triage (VLM)**: Automated visual verification of smoke plumes, cloud cover, and active flames using Vision-Language Models with rule-based fallback.
- **📈 ML Spread Radar & Forecasting**: Gradient-boosted machine learning model predicting fire spread direction and 6h / 12h / 24h expansion radiuses based on wind speed, humidity, and terrain metrics.
- **🗺️ Interactive Tactical Command Dashboard**: High-contrast, modern SaaS command center powered by Next.js 14 and Leaflet, featuring OpenStreetMap cartography, Indonesian regional presets, and real-time incident inspection.
- **⚡ Automated Incident Alerting**: Real-time notification dispatch via Telegram and structured webhooks for rapid emergency response.

---

## System Architecture

```
                       ┌─────────────────────────┐
                       │ NASA FIRMS / GIBS Feeds │
                       └────────────┬────────────┘
                                    │ (Near-Real-Time Hotspots)
                                    ▼
                       ┌─────────────────────────┐
                       │ Ingestion & Deduplication│
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
                                    │
                                    ▼
                       ┌─────────────────────────┐
                       │ PostgreSQL / Supabase DB │
                       └────────────┬────────────┘
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
│   │   ├── api/v1/           # REST API Route handlers (Events, Triage, Predictions)
│   │   ├── core/             # Configuration, database session, security
│   │   ├── models/           # SQLAlchemy ORM database models
│   │   ├── schemas/          # Pydantic validation schemas
│   │   └── services/         # Ingestion, VLM triage, alerts, ML pipelines
│   ├── ml/                   # Machine learning models & prediction engine
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
├── docker-compose.yml        # Multi-container local deployment stack
└── Dockerfile                # Production container specifications
```

---

## Tech Stack & Infrastructure

| Layer | Technologies | Role |
|---|---|---|
| **Frontend** | Next.js 14, React 18, Tailwind CSS, Leaflet, SWR, Recharts | Tactical Geospatial Operations HUD |
| **Backend** | FastAPI, Python 3.10+, SQLAlchemy, Alembic, Pydantic v2 | High-throughput Async REST API |
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
   # Populate your NASA FIRMS API key, Telegram Bot token, and Database credentials in .env
   ```

3. **Launch the stack:**
   ```bash
   docker compose up --build
   ```

4. **Access the applications:**
   - **Dashboard**: [http://localhost:3000](http://localhost:3000)
   - **Backend API**: [http://localhost:8000](http://localhost:8000)
   - **Interactive API Docs (Swagger)**: [http://localhost:8000/docs](http://localhost:8000/docs)

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

# Run Frontend End-to-End Tests (Playwright)
cd frontend
npm run test:e2e
```

---

## License

This project is licensed under the [MIT License](LICENSE).
