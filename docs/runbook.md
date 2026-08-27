# Aero-Flare Operations Runbook

**System:** Aero-Flare v1.0.0 — Wildfire Intelligence Dashboard
**Backend:** Railway.app | **Frontend:** Vercel | **DB:** Supabase | **Tiles:** Cloudflare R2

---

## Quick Reference

| Service | URL | Auth |
|---------|-----|------|
| Dashboard | https://aero-flare.vercel.app | Public |
| API | https://aero-flare-api.up.railway.app | X-API-Key header |
| API Docs | https://aero-flare-api.up.railway.app/docs | Public |
| Health | https://aero-flare-api.up.railway.app/api/v1/health | Public |
| Supabase | https://app.supabase.com → project ap-southeast-1 | Dashboard login |
| Railway | https://railway.app/dashboard | Dashboard login |

---

## Scenario 1 — FIRMS API Not Returning Data

**Symptoms:**
- `pipeline.yml` step "Run FIRMS ingestion" exits 0 but creates 0 new events
- `fire_events` table count unchanged after pipeline run

**Debug:**
```bash
# Test FIRMS API directly
curl -s "https://firms.modaps.eosdis.nasa.gov/api/country/csv/$FIRMS_API_KEY/VIIRS_SNPP_NRT/IDN/1" \
  | head -5

# Check for quota exhaustion (API returns HTML error page instead of CSV)
curl -s "https://firms.modaps.eosdis.nasa.gov/api/country/csv/$FIRMS_API_KEY/VIIRS_SNPP_NRT/IDN/1" \
  | python3 -c "import sys; data=sys.stdin.read(); print('CSV' if 'latitude' in data else 'ERROR:'+data[:200])"
```

**Fix:**
1. If quota exceeded: wait 24h (free tier: 1,000 requests/day) or register a new API key at https://firms.modaps.eosdis.nasa.gov/api/area/
2. If API is down: check https://status.earthdata.nasa.gov
3. Set new key: Railway → backend service → Variables → `FIRMS_API_KEY`

---

## Scenario 2 — GIBS Tile Download Fails

**Symptoms:**
- Events created but `tile_url` is NULL in `fire_events` table
- `gibs_tile_unavailable` warning in Railway logs
- TriageModal shows "No satellite tile available"

**Debug:**
```bash
# Test a GIBS tile URL directly (no auth required)
curl -I "https://gibs.earthdata.nasa.gov/wmts/epsg4326/best/VIIRS_SNPP_CorrectedReflectance_TrueColor/default/2025-07-23/250m/6/0/0.jpg"
# Expected: HTTP 200. If 404: date or tile coordinates wrong. If 503: GIBS outage.
```

**Fix:**
- If GIBS is down: check https://earthdata.nasa.gov/eosdis/system-availability — triage still proceeds, just without tile.
- If tile is always 404: fire event is outside GIBS coverage area (e.g. very old date).
- Tiles are **optional** — triage continues using rule-based fallback if VLM also fails.

---

## Scenario 3 — VLM Triage Not Running

**Symptoms:**
- Events stuck in `PENDING` status
- No rows in `triage_reports` after pipeline run
- `ollama_unreachable` warning in Railway logs

**Debug:**
```bash
# Check Ollama tunnel from GitHub Actions env
curl -s "$OLLAMA_BASE_URL/api/tags" | jq '.models[].name'

# Check Railway logs
# Railway dashboard → backend service → Logs → search "ollama"
```

**Fix:**
1. Restart cloudflared tunnel on your local machine:
   ```bash
   cloudflared tunnel run aero-flare-ollama
   ```
2. Update `OLLAMA_BASE_URL` in Railway env vars if tunnel URL changed.
3. Verify Ollama is serving the correct model:
   ```bash
   ollama list  # should show qwen2-vl:7b
   ollama pull qwen2-vl:7b  # if missing
   ```
4. Rule-based fallback will have covered triage in the interim — events are still triaged.

---

## Scenario 4 — VLM Returns Invalid JSON

**Symptoms:**
- `vlm_response_schema_error` or `vlm_response_no_json` in Railway logs
- Events triaged with `triage_source = RULE_BASED_FALLBACK` unexpectedly
- Telegram alert says "rule-based fallback"

**Debug:**
```bash
# Check Railway logs for raw VLM output
# Railway → backend → Logs → search "vlm_response"
```

**Fix:**
1. Check if model was updated/changed: `ollama list`
2. Test the prompt manually:
   ```bash
   curl -s http://localhost:11434/api/generate \
     -d '{"model":"qwen2-vl:7b","prompt":"Respond with JSON only: {\"test\":true}"}' | jq .response
   ```
3. If model consistently produces non-JSON: review `prompts/triage_prompt.md` — add stricter JSON-only instruction.
4. tenacity retries 3× automatically before falling back — check if all 3 attempts failed.

---

## Scenario 5 — XGBoost Prediction Fails

**Symptoms:**
- `prediction_skipped` warning in Railway logs
- No rows in `predictions` table for `CONFIRMED_FIRE` events
- SpreadRadiusChart shows "No prediction data"

**Debug:**
```bash
# Check model file exists in Railway deployment
# Railway → backend → Console (if available) or check Dockerfile COPY step

# Check Open-Meteo weather API
curl -s "https://api.open-meteo.com/v1/forecast?latitude=-2.345&longitude=112.456&current=wind_speed_10m" | jq .
```

**Fix:**
1. If model file missing: verify `ml/models/xgboost_spread_v1.0.0.ubj` is committed and not in `.gitignore`.
2. If Open-Meteo is down: predictions will fail gracefully — fire alert still sent, just without spread data.
3. Retrain model: `python ml/train.py --version 1.0.1`

---

## Scenario 6 — Telegram Alert Not Delivered

**Symptoms:**
- Events at `ALERTED_FAILED` status
- `telegram_send_failed` error in Railway logs
- No message in Telegram fire alert channel

**Debug:**
```bash
# Test Telegram bot directly
curl -s "https://api.telegram.org/bot$TELEGRAM_BOT_TOKEN/getMe" | jq .

# Test sending a message
curl -s -X POST "https://api.telegram.org/bot$TELEGRAM_BOT_TOKEN/sendMessage" \
  -d "chat_id=$TELEGRAM_CHANNEL_ID" \
  -d "text=Test from runbook"
```

**Fix:**
1. If `getMe` fails: token expired — regenerate via @BotFather.
2. If `sendMessage` fails with 400: bot was removed from channel — re-add as admin.
3. If bot is fine but no alerts: check `fire_events.alerted_at` — if NULL, alert hasn't run yet. Check `alert_retry.yml` workflow.
4. Retry failed alerts: `alert_retry.yml` runs every 3 hours automatically.

---

## Scenario 7 — Dashboard Shows No Data

**Symptoms:**
- Map is empty (no fire markers)
- EventSidebar shows "No fire events detected"
- Browser DevTools Network tab shows `/api/proxy/events` returning `{"data":[],"total":0}`

**Debug:**
```bash
# Check if events exist in DB
curl -s "https://aero-flare-api.up.railway.app/api/v1/events" \
  -H "X-API-Key: $API_KEY" | jq '.total'

# Check pipeline last run
# GitHub Actions → firms_ingest.yml → last execution
```

**Fix:**
1. If `total = 0`: pipeline hasn't run or no fires detected in Indonesia today. Trigger manually:
   ```bash
   # GitHub Actions → firms_ingest.yml → Run workflow (workflow_dispatch)
   ```
2. If `total > 0` but dashboard empty: likely a Vercel proxy env var issue.
   - Vercel dashboard → Project → Settings → Environment Variables
   - Confirm `BACKEND_API_URL` and `BACKEND_API_KEY` are set (server-side, no `NEXT_PUBLIC_` prefix)
3. If proxy returns 403: `BACKEND_API_KEY` in Vercel doesn't match `API_KEY` in Railway.

---

## Free Tier Quota Thresholds

| Service | Limit | Alert At |
|---------|-------|----------|
| Railway | $5/month credit | 80% used |
| Supabase | 500MB DB, 2GB storage | 400MB / 1.6GB |
| Cloudflare R2 | 10GB storage, 10M reads/month | 8GB / 8M |
| Grafana Cloud | 14-day retention, 50GB logs | N/A (retention managed) |
| FIRMS API | 1,000 req/day | 800/day |

Check Railway usage: Railway dashboard → Project → Usage tab.

---

## Runbook Maintenance

Update this document when:
- A new failure mode is discovered in production
- A service changes its free tier limits
- A new tool or integration is added

*Last updated: 2025-07-24 | Maintained by: Debug Agent*
