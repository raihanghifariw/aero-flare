# Aero-Flare Project Memory & Comprehensive Knowledge Base

> **Last Updated**: 2026-08-27  
> **Status**: Production Ready (CI/CD 100% Passing, Vercel & Railway Operational)

---

## 1. System Architecture Summary

```
                       ┌─────────────────────────┐
                       │ NASA FIRMS VIIRS API    │
                       └───────────┬─────────────┘
                                   │ (Every 3 hours)
                                   ▼
┌──────────────────┐    ┌─────────────────────────┐    ┌──────────────────────────┐
│ Next.js Frontend │<──>│ FastAPI Backend         │<──>│ Supabase PostgreSQL DB   │
│ (Vercel)         │    │ (Railway)               │    │ (ap-southeast-1)         │
└──────────────────┘    └───────────┬─────────────┘    └──────────────────────────┘
                                    │
                                    ├──> Ollama VLM (qwen2-vl / llava)
                                    ├──> Rule-Based Fallback Engine
                                    ├──> XGBoost Spread Predictor (4 targets)
                                    └──> Cloudflare R2 Tile Storage
```

---

## 2. Technical Stack & Hosted Services

| Component | Technology | Host / Location | URL / Reference |
| :--- | :--- | :--- | :--- |
| **Frontend** | Next.js 14 (App Router), TypeScript, TailwindCSS | Vercel | `https://aero-flare.vercel.app` |
| **Backend API** | FastAPI, Structlog, SQLAlchemy AsyncIO, Alembic | Railway | `https://aero-flare-production.up.railway.app` |
| **Database** | PostgreSQL 15 | Supabase | `ap-southeast-1` (Singapore) |
| **Tile Storage** | S3-Compatible Storage | Cloudflare R2 | Bucket `aero-flare-tiles` |
| **VLM Triage** | Qwen2-VL:7B / LLaVA:13B | Cloudflare Tunnel / Ollama | `https://ollama.ghifariworks.me` |
| **ML Model** | XGBoost Multi-Target Regressor | Python 3.11 / `ml/models` | `xgboost_spread_v1.0.0.ubj` |

---

## 3. Critical Fixes Log & ADR Summary

### ADR-015: RecommendedAction Literal Alignment
- **Problem**: `RecommendedAction` schema mismatch between Pydantic, TypeScript, VLM prompt, and tests caused 16 unit test failures and Pydantic validation crashes.
- **Resolution**: Aligned `RecommendedAction` across Python (`backend/app/schemas/triage_report.py`), TypeScript (`frontend/src/types/triage-report.ts`), and Prompt templates:
  - Allowed values: `"MONITOR"`, `"INVESTIGATE"`, `"DISPATCH"`, `"DISPATCH_LOCAL"`, `"DISPATCH_REGIONAL"`, `"EVACUATE"`.

### ADR-016: FIRMS Ingestion & Tile Fetcher Export
- **Problem**: `ingest_firms.py` threw `ImportError: cannot import name 'fetch_and_upload_tile'` from `gibs_tile_fetcher.py`.
- **Resolution**: Exported `fetch_and_upload_tile(event)` in `app/services/ingestion/gibs_tile_fetcher.py` and handled `datetime` / `timezone` imports cleanly.

### ADR-017: GitHub Actions CI/CD Syntax & Caching
- **Problem**:
  - `secrets` object evaluated directly inside job-level `if:` statements caused invalid workflow errors.
  - `actions/setup-python@v5` failed without `cache-dependency-path: 'backend/requirements.txt'`.
  - Multiline bash strings in Telegram alert cURL calls triggered bash syntax errors.
  - Railway CLI was missing from runner `$PATH`.
  - Vercel CLI double-nested working directory (`frontend/frontend`).
  - XGBoost model file (`.ubj`) was gitignored, causing `ModelNotFoundError` in fresh CI runners.
- **Resolution**:
  - Moved secret checks to step `env.SECRET_NAME != ''`.
  - Added `cache-dependency-path: 'backend/requirements.txt'`.
  - Converted Telegram cURL commands to single-line strings.
  - Added `export PATH="$HOME/.railway/bin:$PATH"` before Railway CLI calls.
  - Executed Vercel CLI from root (`npx vercel --token=${{ secrets.VERCEL_TOKEN }} --prod --yes`).
  - Added model training step `python ml/train.py --version 1.0.0` in `test-backend` job.

---

## 4. Key Verification & CLI Commands

```bash
# Run backend pytest suite with 80%+ coverage check
pytest

# Run Python code quality linter
ruff check .
ruff check --fix .

# Train/generate XGBoost spread prediction model
python ml/train.py --version 1.0.0

# Run manual FIRMS ingestion pipeline locally
python backend/scripts/ingest_firms.py

# Lint & build Next.js frontend
cd frontend
npm run lint
npm run build
```

---

## 5. Workflow Files Summary (`.github/workflows/`)

- **`ci.yml`**: Full CI/CD pipeline (backend ruff/pytest + model generation, frontend lint/build, Vercel & Railway deployment).
- **`firms_ingest.yml`**: Cron job running every 3 hours (`0 */3 * * *`) for FIRMS ingestion + triage + spread prediction.
- **`ollama_health.yml`**: Cron job running every 30 minutes (`*/30 * * * *`) to check VLM reachability.
- **`alert_retry.yml`**: Cron job running every 30 minutes to retry failed alerts.
- **`data_retention.yml`**: Weekly cron job (Sunday midnight UTC) to prune tiles older than 180 days.
