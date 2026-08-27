# Aero-Flare Security Hardening — Implementation Notes

This document supplements `plan/security_agent.md` with concrete configuration
steps and verification commands for each security control.

---

## 1. API Key Generation

```bash
# Generate a cryptographically secure 32-byte URL-safe key
python -c "import secrets; print(secrets.token_urlsafe(32))"
# Example output: Kw4pT8nYqB3mZxLvR7sJhDfAeC2uWgXo (DO NOT USE THIS — generate your own)
```

Set in:
- Railway: Settings → Variables → `API_KEY`
- GitHub Actions: Settings → Secrets → `BACKEND_API_KEY`
- Vercel: Settings → Environment Variables → `BACKEND_API_KEY` (no NEXT_PUBLIC_ prefix)

---

## 2. Rate Limiting — Verification

After deploying, verify rate limits fire correctly:

```bash
# Should return 429 after 6 requests within a minute
for i in $(seq 1 7); do
  curl -s -o /dev/null -w "%{http_code}\n" \
    -X POST https://your-backend.railway.app/api/v1/webhooks/register \
    -H "X-API-Key: $API_KEY" \
    -H "Content-Type: application/json" \
    -d '{"url":"https://example.com/hook"}'
done
# Expected: 201 201 201 201 201 201 429
```

---

## 3. Input Validation — Verification

```bash
# Invalid UUID → should return 422
curl -s -o /dev/null -w "%{http_code}" \
  "https://your-backend/api/v1/events/not-a-uuid" \
  -H "X-API-Key: $API_KEY"
# Expected: 422

# limit out of range → should return 422
curl -s -o /dev/null -w "%{http_code}" \
  "https://your-backend/api/v1/events?limit=99999" \
  -H "X-API-Key: $API_KEY"
# Expected: 422
```

---

## 4. Log Scrubbing — Verification

```python
# In a Python shell with the app loaded:
import structlog
logger = structlog.get_logger()
# This should print ***REDACTED*** for api_key, not the real value
logger.info("test", api_key="my-real-secret")
```

---

## 5. Supabase RLS — Verification

Run `docs/sql/rls_setup.sql` in Supabase SQL Editor, then verify:

```sql
-- Connect with anon key (not service_role) and run:
SELECT * FROM fire_events LIMIT 1;
-- Expected: 0 rows (not an error) — RLS blocking anon access
```

---

## 6. Cloudflare R2 — Presigned URL Verification

```bash
# Generate a presigned URL (backend must be running):
curl -s "https://your-backend/api/v1/events/some-event-id" \
  -H "X-API-Key: $API_KEY" | jq '.tile_url'

# The returned URL is a presigned R2 URL with ?X-Amz-Expires=3600
# After 1 hour, the same URL should return 403:
sleep 3601 && curl -s -o /dev/null -w "%{http_code}" "<presigned-url>"
# Expected: 403
```

---

## 7. CORS — Verification

```bash
# From a browser console on a non-allowed origin, this should be blocked by CORS:
fetch('https://your-backend.railway.app/api/v1/events', {
  headers: { 'X-API-Key': '...' }
})
# Expected: CORS error in browser console
```

---

## 8. Ollama Cloudflare Tunnel — Setup

```bash
# Install cloudflared
wget https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64
chmod +x cloudflared-linux-amd64
sudo mv cloudflared-linux-amd64 /usr/local/bin/cloudflared

# One-time: authenticate and create a named tunnel
cloudflared login
cloudflared tunnel create aero-flare-ollama
cloudflared tunnel route dns aero-flare-ollama ollama.yourdomain.com

# Start tunnel (add to systemd for persistence)
cloudflared tunnel run aero-flare-ollama

# Set in Railway env: OLLAMA_BASE_URL=https://ollama.yourdomain.com
```

Verification:
```bash
# Unauthenticated request to Ollama without tunnel auth → should return 401 or be unreachable
curl -s https://ollama.yourdomain.com/api/tags
# If tunnel has access controls → expected: 401
```

---

## 9. GitHub Actions — BACKEND_API_KEY Auth Test

To verify the secret is wired correctly:

1. Temporarily change `BACKEND_API_KEY` in GitHub Actions secrets to a wrong value
2. Manually trigger `firms_ingest.yml` from the Actions tab
3. Confirm the ingestion step logs `403 Forbidden`
4. Restore the correct value and re-run — confirm success

---

## 10. Dependency Audit — Local Run

```bash
# Backend
pip install pip-audit
pip-audit -r backend/requirements.txt --severity high

# Frontend
cd frontend && npm audit --audit-level=moderate
```

Any findings should either be resolved by version bumps in `requirements.txt` /
`package.json`, or documented in `docs/security/unfixable_cves.md`.
