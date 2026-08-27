# Aero-Flare — Production Architecture

**Version:** 1.0.0 | **Last updated:** 2025-07-24

---

## System Overview

Aero-Flare is a real-time wildfire intelligence platform for Indonesia. It ingests NASA FIRMS hotspot data every 3 hours, triages each event with a Vision Language Model (VLM), predicts fire spread with XGBoost, and delivers alerts via Telegram and webhooks — all on **$0/month** free-tier infrastructure.

---

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                        DATA SOURCES (external)                      │
│                                                                     │
│   NASA FIRMS API          NASA GIBS WMTS         Open-Meteo API    │
│  (VIIRS hotspots)        (satellite tiles)       (wind/humidity)   │
│   1,000 req/day            No auth, free           No auth, free   │
└────────┬──────────────────────────┬────────────────────┬────────────┘
         │                          │                    │
         │ every 3h                 │                    │
         ▼                          │                    │
┌─────────────────┐                 │                    │
│  GitHub Actions │                 │                    │
│  firms_ingest   │                 │                    │
│  .yml (cron)    │                 │                    │
└────────┬────────┘                 │                    │
         │ POST /api/v1/            │                    │
         │ ingestion/trigger        │                    │
         │ X-API-Key: ***           │                    │
         ▼                          ▼                    ▼
┌────────────────────────────────────────────────────────────────────┐
│                   FastAPI Backend (Railway.app)                     │
│                                                                     │
│  ┌──────────────┐  ┌───────────────┐  ┌──────────────────────────┐ │
│  │  Ingestion   │  │ VLM Triage    │  │   Spread Prediction      │ │
│  │  Service     │  │ Service       │  │   Service                │ │
│  │              │  │               │  │                          │ │
│  │ firms_parser │  │ vlm_client    │  │ feature_builder          │ │
│  │ event_writer │  │ + tenacity    │  │ → Open-Meteo weather     │ │
│  │ gibs_fetcher │  │ retry (3×)    │  │ model_loader             │ │
│  │ → R2 upload  │  │               │  │ → XGBoost inference      │ │
│  └──────────────┘  │ fallback:     │  └──────────────────────────┘ │
│                    │ rule_based_   │                                │
│                    │ triage.py     │  ┌──────────────────────────┐  │
│                    └───────────────┘  │   Alert Service          │  │
│                                       │                          │  │
│                    ┌───────────────┐  │ dedup (alerted_at col)   │  │
│                    │  REST API     │  │ alert_formatter          │  │
│                    │  /api/v1/*    │  │ telegram_service         │  │
│                    │  slowapi      │  │ webhook_service          │  │
│                    │  rate limits  │  └──────────────────────────┘  │
│                    │  verify_api_  │                                │
│                    │  key dep      │                                │
│                    └───────────────┘                               │
└──────────────┬──────────────────────────────┬──────────────────────┘
               │                              │
               │ SQL (asyncpg)                │ boto3 S3 API
               ▼                              ▼
┌──────────────────────┐         ┌────────────────────────┐
│   Supabase           │         │   Cloudflare R2        │
│   PostgreSQL         │         │   aero-flare-tiles     │
│   (ap-southeast-1)   │         │   (private bucket)     │
│                      │         │                        │
│   fire_events        │         │   tiles/YYYY-MM-DD/    │
│   triage_reports     │         │   {event_id}.jpg       │
│   predictions        │         │                        │
│   webhook_reg.       │         │   Access: presigned    │
│   event_audit_log    │         │   URLs only (1h TTL)   │
│                      │         └────────────────────────┘
│   RLS enabled        │
│   service_role only  │
└──────────────────────┘

               Telegram Bot
               (fire alerts)
               ▲
               │
┌──────────────┴───────────────────────────────────────────────────┐
│                   Alert Delivery                                   │
│                                                                    │
│   CONFIRMED_FIRE or PROBABLE_FIRE event                           │
│   → format_alert_message()                                        │
│   → check alerted_at IS NULL (dedup — no Redis needed)            │
│   → send to Telegram channel + registered webhooks               │
│   → set fire_events.alerted_at = NOW()                            │
└───────────────────────────────────────────────────────────────────┘

┌───────────────────────────────────────────────────────────────────┐
│              Ollama VLM (local machine)                            │
│              qwen2-vl:7b + llava:13b (fallback)                   │
│                    │                                               │
│              Cloudflare Tunnel                                     │
│              (named tunnel, persistent URL)                        │
│                    │                                               │
│              OLLAMA_BASE_URL env var on Railway                   │
└───────────────────────────────────────────────────────────────────┘

┌───────────────────────────────────────────────────────────────────┐
│              Next.js Dashboard (Vercel)                            │
│                                                                    │
│   Browser (SWR polling every 5 min)                               │
│        ↓                                                           │
│   /api/proxy/* (Next.js server route)   ← BACKEND_API_KEY         │
│        ↓  adds X-API-Key server-side     never in browser         │
│   Railway backend /api/v1/*                                        │
│                                                                    │
│   Components:                                                      │
│   • FireMap (Leaflet, SSR disabled)                               │
│   • FireMarker (danger level colors)                              │
│   • SpreadOverlay (sector polygon)                                │
│   • TriageModal (bottom sheet / drawer)                           │
│   • EventSidebar (filters + pagination)                           │
│   • SpreadRadiusChart (Recharts)                                  │
└───────────────────────────────────────────────────────────────────┘

┌───────────────────────────────────────────────────────────────────┐
│              Observability (Grafana Cloud)                         │
│                                                                    │
│   OpenTelemetry SDK → OTLP exporter → Grafana Cloud Traces        │
│   structlog JSON → stdout → Railway log drain → Grafana Loki      │
│   Prometheus /metrics → Grafana Cloud Metrics                     │
│   14-day retention, free tier                                      │
└───────────────────────────────────────────────────────────────────┘
```

---

## Data Flow: Event Detected → Alert Sent

```
1. GitHub Actions cron (every 3h)
   └─► POST /api/v1/ingestion/trigger

2. fetch_firms_data()
   └─► FIRMS API → IDN VIIRS CSV → parse_firms_csv() → dedup → upsert fire_events

3. fetch_gibs_tile(lat, lon, date)
   └─► NASA GIBS WMTS → tile PNG → upload to R2 → update fire_events.tile_url

4. run_triage(event)
   ├─► call_vlm(image_path, prompt, "qwen2-vl:7b") [tenacity 3× retry]
   ├─► on failure: call_vlm(image_path, prompt, "llava:13b") [fallback model]
   ├─► on all VLM failure: rule_based_triage(event) [deterministic]
   └─► save TriageReport to DB

5. run_prediction(event, triage)  [if CONFIRMED_FIRE or PROBABLE_FIRE]
   ├─► fetch_weather_features(lat, lon) → Open-Meteo
   ├─► build_feature_vector(event, triage, weather)
   ├─► model.predict(features) → 4 outputs
   └─► save Prediction to DB

6. run_alert(event, triage, prediction)
   ├─► is_already_alerted(event) → skip if alerted_at IS NOT NULL
   ├─► format_alert_message(event, triage, prediction, location_name)
   ├─► send_telegram(message)
   ├─► dispatch_webhooks(payload)
   └─► update fire_events.alerted_at = NOW()
```

---

## Security Architecture

```
Internet ──► CloudFlare (DDoS, HTTPS) ──► Railway (Backend)
                                               │
                                    verify_api_key (FastAPI dep)
                                    slowapi rate limits
                                    CORS: vercel.app only
                                               │
                                         Supabase (RLS)
                                    service_role only access
```

- API key: min 32-char URL-safe random token
- Frontend proxy: `BACKEND_API_KEY` never in browser bundle
- R2 tiles: presigned URLs with 1-hour TTL
- Ollama: only reachable via Cloudflare Tunnel (not direct internet)
- Logs: `scrub_secrets` structlog processor removes all secret values

---

## Free Tier Budget

| Service | Cost | Usage |
|---------|------|-------|
| Railway.app | $5/month credit | ~$2/month at idle |
| Vercel | $0 | Hobby plan |
| Supabase | $0 | 500MB DB |
| Cloudflare R2 | $0 | 10GB tiles |
| Grafana Cloud | $0 | 14-day retention |
| NASA FIRMS | $0 | 1,000 req/day |
| NASA GIBS | $0 | Unlimited |
| Open-Meteo | $0 | Unlimited |
| **Total** | **~$2–5/month** | |

*Note: Railway free tier changed to $5/month credit in 2024. Monitor usage dashboard monthly.*
