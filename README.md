# Aero-Flare 🔥

**Early Wildfire Detection Triage via Satellite Imagery**

Aero-Flare is an automated wildfire detection and triage system for Indonesia. It pulls NASA FIRMS thermal anomaly data every 3 hours, analyzes satellite tiles with a local VLM (Qwen2-VL), predicts fire spread using XGBoost, and dispatches real-time alerts via Telegram.

---

## Architecture

```
GitHub Actions (cron 3h)
        │
        ▼
NASA FIRMS API → Ingestion → GIBS Tile (Cloudflare R2)
        │
        ▼
VLM Triage (Ollama: Qwen2-VL) ──[fail]──► Rule-Based Fallback (FRP > 50MW)
        │
        ▼
XGBoost Spread Prediction (wind, NDVI, humidity)
        │
        ▼
Alert: Telegram + Webhooks
        │
        ▼
Next.js Dashboard (Vercel) — Leaflet map, triage modal, spread overlay
```

---

## Free-Tier Stack

| Component | Service | Limit |
|-----------|---------|-------|
| Database | Supabase (PostgreSQL) | 500MB free |
| Tile Storage | Cloudflare R2 | 10GB free, no egress fees |
| Backend | Railway.app | $5 free credits/month |
| Frontend | Vercel | 100GB bandwidth free |
| Pipeline | GitHub Actions | 2,000 min/month free |
| Observability | Grafana Cloud | 14-day retention free |
| Satellite Data | NASA GIBS WMTS | Free, no auth |
| Fire Data | NASA FIRMS API | Free with registration |

---

## Quick Start

```bash
# 1. Clone
git clone https://github.com/your-org/aero-flare.git
cd aero-flare

# 2. Configure environment
cp .env.example .env
# Edit .env with your keys (see .env.example for all required vars)

# 3. Start local stack
docker-compose up --build

# 4. Pull VLM model (separate terminal)
docker exec -it aeroflare_ollama_1 ollama pull qwen2-vl:7b

# 5. Run database migrations
docker exec -it aeroflare_backend_1 alembic upgrade head

# 6. Test the API
curl http://localhost:8000/api/v1/health
```

---

## Project Structure

```
aero-flare/
├── plan/           # Architecture & spec documents
├── task/           # Agent execution checklists (8 phases)
├── backend/        # FastAPI + SQLAlchemy + XGBoost
├── frontend/       # Next.js 14 + Leaflet dashboard
├── ml/             # XGBoost training scripts & models
├── prompts/        # VLM system prompts (versioned)
├── data/           # Raw FIRMS CSV (gitignored)
├── .github/
│   └── workflows/  # CI, pipeline cron, alert retry, data retention
└── docker-compose.yml
```

---

## Agent Execution Order

See [`task/README.md`](task/README.md) for the complete 8-phase build sequence.

| Phase | Agent | Task |
|-------|-------|------|
| 0 | Setup | Scaffold, Docker, CI |
| 1 | Backend | FastAPI, ORM, migrations |
| 2 | VLM + ML | Triage engine, XGBoost |
| 3 | GHA + Alerts | Pipeline cron, Telegram |
| 4 | Frontend | Leaflet dashboard |
| 5 | Security | Hardening, Trivy |
| 6 | QA | Tests, coverage |
| 7 | Deploy | Railway, Vercel, R2 |
| 8 | Debug | Monitoring, runbook |

---

## Production URLs

> Fill these in after first deployment (Phase 7)

```
Dashboard:  https://aero-flare.vercel.app
API:        https://aero-flare-api.up.railway.app
API Docs:   https://aero-flare-api.up.railway.app/docs
Health:     https://aero-flare-api.up.railway.app/api/v1/health
```

---

## Key Documentation

| Document | Description |
|----------|-------------|
| [`docs/architecture.md`](docs/architecture.md) | Full system architecture diagram + data flow |
| [`docs/runbook.md`](docs/runbook.md) | Operations runbook — 7 failure scenarios + fixes |
| [`docs/release/v1.0.0_qa_report.md`](docs/release/v1.0.0_qa_report.md) | QA release report |
| [`docs/sql/audit_trigger_setup.sql`](docs/sql/audit_trigger_setup.sql) | PostgreSQL audit triggers (run after migrations) |
| [`docs/sql/rls_setup.sql`](docs/sql/rls_setup.sql) | Supabase RLS policies (run before first deploy) |
| [`docs/sql/false_positive_monitoring.sql`](docs/sql/false_positive_monitoring.sql) | Weekly FP rate monitoring query |
| [`docs/security/hardening_notes.md`](docs/security/hardening_notes.md) | Security verification steps |
| [`CONTRIBUTING.md`](CONTRIBUTING.md) | Local dev setup, test commands, PR process |

---

## Running Tests

```bash
# Backend — unit + integration (must pass before deploy)
pytest backend/tests/ -v --cov=backend/app  # requires ≥ 80% coverage

# Frontend E2E
cd frontend && npx playwright test

# QA smoke test (requires running backend)
bash backend/scripts/qa_smoke_test.sh http://localhost:8000 $API_KEY
```

---

## Contributing

See [`CONTRIBUTING.md`](CONTRIBUTING.md) for local dev setup, test commands, and PR process.

---

*Version 1.0.0 | Architecture: v1.1.0 | Free-tier verified ✓*
