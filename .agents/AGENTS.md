# Aero-Flare Project Rules & Memory Guidelines

## 1. Project Overview & Architecture
Aero-Flare is a real-time wildfire intelligence & triage system for Indonesia.
- **Frontend**: Next.js 14 (App Router, TypeScript, TailwindCSS, Leaflet/Mapbox). Hosted on Vercel (`https://aero-flare.vercel.app`).
- **Backend**: FastAPI (Python 3.11, Structlog, SQLAlchemy AsyncIO, Alembic). Hosted on Railway (`https://aero-flare-production.up.railway.app`).
- **Database**: Supabase PostgreSQL (Singapore `ap-southeast-1`).
- **Storage**: Cloudflare R2 (`aero-flare-tiles` bucket).
- **Inference & Triage**:
  - Primary VLM: Ollama (`qwen2-vl` / `llava`) on custom endpoint (`https://ollama.ghifariworks.me`).
  - Fallback Triage: Rule-based FRP threshold engine (`app/services/triage/rule_based_triage.py`).
  - Fire Spread Model: XGBoost Regressor (`ml/models/xgboost_spread_v1.0.0.ubj`).

## 2. Ingestion & NASA FIRMS API
- Script: `backend/scripts/ingest_firms.py`
- NASA FIRMS Endpoint: `https://firms.modaps.eosdis.nasa.gov/api/area/csv/{api_key}/VIIRS_SNPP_NRT/{INDONESIA_BBOX}/1`
- Indonesia Bounding Box: `95,-11,141,6`
- Helper module `app/services/ingestion/gibs_tile_fetcher.py` exports `fetch_and_upload_tile(event)` to capture GIBS WMTS satellite tiles (~50KB) and presign R2 URLs.

## 3. Schema & Type Alignment
- `RecommendedAction` must support: `"MONITOR"`, `"INVESTIGATE"`, `"DISPATCH"`, `"DISPATCH_LOCAL"`, `"DISPATCH_REGIONAL"`, `"EVACUATE"`.
- `Classification`: `"CONFIRMED_FIRE"`, `"PROBABLE_FIRE"`, `"FALSE_POSITIVE"`, `"INDUSTRIAL_SOURCE"`.
- `TriageSource`: `"VLM"` (DB/API) / `"RULE_BASED_FALLBACK"` (DB/API) or `"vlm"` / `"rule_based"` (Pydantic internal).

## 4. Testing & Linting Standards
- Linter: `ruff check .`
- Test Suite: `pytest` (137 tests passing, minimum 80% coverage requirement enforced in `pyproject.toml`).
- Model Training: `python ml/train.py --version 1.0.0` must run before `pytest` on fresh CI environments because `.ubj` model files are gitignored (`*.ubj`).

## 5. CI/CD & Deployment Workflows (`.github/workflows/`)
- `ci.yml`: Runs `ruff check .`, trains XGBoost model artifact, executes `pytest`, lints & builds frontend, deploys to Railway and Vercel.
- Railway Deployment: Automatic via Railway GitHub integration + CLI fallback (`export PATH="$HOME/.railway/bin:$PATH"`).
- Vercel Deployment: Official Vercel CLI from root (`npx vercel --token=${{ secrets.VERCEL_TOKEN }} --prod --yes`).
- Secret Check: Must use `if: env.SECRET_NAME != ''` on step level (never `secrets` at job level or `secrets` inside `if:`).
