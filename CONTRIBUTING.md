# Contributing to Aero-Flare

Thank you for contributing to Aero-Flare — an open-source early wildfire detection system for Indonesia.

---

## Table of Contents
1. [Local Development Setup](#local-development-setup)
2. [Running Tests](#running-tests)
3. [Code Style](#code-style)
4. [Pull Request Process](#pull-request-process)
5. [Agent Execution Order](#agent-execution-order)
6. [Architecture Overview](#architecture-overview)
7. [Free Tier Infra Constraints](#free-tier-infra-constraints)

---

## Local Development Setup

### Prerequisites
- Python 3.11+
- Node.js 20+
- Docker & Docker Compose
- [Ollama](https://ollama.com) (for local VLM triage)

### 1. Clone and configure
```bash
git clone https://github.com/your-org/aero-flare.git
cd aero-flare

# Copy env template and fill in values
cp .env.example .env
# Required minimum: API_KEY, DATABASE_URL (can use SQLite for dev)
```

### 2. Backend (FastAPI)
```bash
cd backend

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run migrations
alembic upgrade head

# Start backend
uvicorn app.main:app --reload --port 8000
# → API available at http://localhost:8000
# → Docs at http://localhost:8000/docs
```

### 3. Frontend (Next.js)
```bash
cd frontend

# Install dependencies
npm install

# Copy and configure env
cp .env.local.example .env.local
# Set BACKEND_API_URL=http://localhost:8000
# Set BACKEND_API_KEY=<same as API_KEY in backend .env>

# Start dev server
npm run dev
# → Dashboard at http://localhost:3000
```

### 4. Local VLM (optional — for triage testing)
```bash
# Install Ollama: https://ollama.com/download
ollama pull qwen2-vl:7b
ollama serve
# → Ollama running at http://localhost:11434
```

### 5. Full stack with Docker Compose
```bash
# From repo root
docker compose up
# Backend: http://localhost:8000
# Frontend: http://localhost:3000
```

---

## Running Tests

### Backend unit + integration tests
```bash
cd aero-flare  # repo root (pyproject.toml is here)

# Run all tests with coverage
pytest backend/tests/ -v

# Run only unit tests (fast, no DB)
pytest backend/tests/unit/ -v

# Run only integration tests
pytest backend/tests/integration/ -v

# Check coverage target (≥ 80%)
pytest backend/tests/ --cov=backend/app --cov-report=term-missing
```

### Frontend E2E tests (Playwright)
```bash
cd frontend

# Install Playwright browsers (first time only)
npx playwright install --with-deps chromium

# Run E2E tests (starts dev server automatically)
npx playwright test

# Run with UI mode (interactive)
npx playwright test --ui
```

### Type checking and linting
```bash
# Backend
mypy backend/app --strict
ruff check backend/app

# Frontend
cd frontend
npx tsc --noEmit
npx eslint src/
```

---

## Code Style

### Python (backend)
- Formatter: **Black** (line length 88) — run `black app/`
- Linter: **Ruff** — run `ruff check app/ --fix`
- Types: **mypy strict** — all public functions must be fully annotated
- See `plan/coding_standard.md` for full rules

### TypeScript (frontend)
- Formatter: **Prettier** — run `npx prettier --write src/`
- Linter: **ESLint** — run `npx eslint src/ --fix`
- `strict: true` in `tsconfig.json` — no `any` types
- See `plan/coding_standard.md` for full rules

### Pre-commit hooks
```bash
pip install pre-commit
pre-commit install
# Hooks run automatically on git commit
```

---

## Pull Request Process

1. **Branch naming:** `feature/description`, `fix/description`, `chore/description`
2. **Target branch:** `develop` (not `main` — main is protected and auto-deploys)
3. **Checklist before opening PR:**
   - [ ] All tests pass: `pytest backend/tests/ -v`
   - [ ] Type check passes: `mypy backend/app --strict`
   - [ ] Lint passes: `ruff check backend/app`
   - [ ] Frontend tests pass: `npx playwright test`
   - [ ] Frontend type check: `npx tsc --noEmit`
   - [ ] Coverage not below 80%
4. **PR description** must reference the task/FR it implements
5. **One reviewer** approval required before merge
6. CI pipeline (GitHub Actions) must pass before merge is enabled

---

## Agent Execution Order

For onboarding or rebuilding the system from scratch, agents must run in this order:

| Phase | Agent | Task file |
|-------|-------|-----------|
| 0 | Setup Agent | `task/00_setup_agent.md` |
| 1 | Backend Agent | `task/01_backend_agent.md` |
| 2 | VLM Agent | `task/02_vlm_agent.md` |
| 3 | ML Agent | `task/03_ml_agent.md` |
| 4 | n8n Agent | `task/04_n8n_agent.md` |
| 5 | Alert Agent | `task/05_alert_agent.md` |
| 6 | Frontend Agent | `task/06_frontend_agent.md` |
| 7 | Security Agent | `task/07_security_agent.md` |
| 8 | QA Agent | `task/08_qa_agent.md` |
| 9 | Deployment Agent | `task/09_deployment_agent.md` |
| 10 | Debug Agent | `task/10_debug_agent.md` |

Each agent task file contains the gate check that must pass before proceeding to the next phase.

---

## Architecture Overview

```
NASA FIRMS API ──► GitHub Actions ──► POST /api/v1/ingestion/trigger
                   (every 3h)              │
                                     FastAPI Backend (Railway)
                                           │
                          ┌────────────────┼────────────────┐
                          ▼                ▼                ▼
                    GIBS tile fetch   Ollama VLM       XGBoost
                    + R2 upload       (qwen2-vl)       spread model
                          │                │                │
                          └────────────────┼────────────────┘
                                     Supabase DB
                                           │
                                    Alert Service
                                           │
                              ┌────────────┴────────────┐
                              ▼                          ▼
                         Telegram                  Webhooks
                        fire alerts               (registered URLs)
                                           │
                              Next.js Dashboard (Vercel)
                              └─ Leaflet map + triage modal
                                 + spread prediction chart
```

See `docs/architecture.md` for the full annotated diagram.

---

## Free Tier Infra Constraints

All production infrastructure runs on **$0/month** free tiers:

| Service | Purpose | Free Limit |
|---------|---------|-----------|
| Railway.app | Backend hosting | $5/month credit |
| Vercel | Frontend hosting | Hobby plan (unlimited) |
| Supabase | PostgreSQL DB | 500MB, 2GB storage |
| Cloudflare R2 | Satellite tiles | 10GB storage, no egress fee |
| Grafana Cloud | Observability | 14-day retention |
| NASA FIRMS | Fire data API | 1,000 req/day |
| NASA GIBS | Satellite tiles | No limit, no auth |
| Open-Meteo | Weather data | No limit, no auth |

**Important:** Before adding any new service, check that it fits within free tier limits. Document any cost implications in `project_memory.md`.
