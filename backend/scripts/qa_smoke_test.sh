#!/usr/bin/env bash
# =============================================================================
# Aero-Flare QA Smoke Test
# Usage: bash scripts/qa_smoke_test.sh <API_BASE_URL> <API_KEY>
#
# Run against any environment (local, staging, production):
#   bash scripts/qa_smoke_test.sh http://localhost:8000 my-secret-key
#   bash scripts/qa_smoke_test.sh https://aero-flare-api.up.railway.app $PROD_API_KEY
#
# Exit code 0 = all checks passed. Non-zero = one or more failures.
# =============================================================================
set -euo pipefail

API_BASE="${1:-http://localhost:8000}"
API_KEY="${2:-test-key}"
PASS=0
FAIL=0

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

ok()   { echo -e "${GREEN}✅ PASS${NC}: $1"; ((PASS++)); }
fail() { echo -e "${RED}❌ FAIL${NC}: $1"; ((FAIL++)); }
info() { echo -e "${YELLOW}ℹ  INFO${NC}: $1"; }

echo ""
echo "================================================="
echo " Aero-Flare QA Smoke Test"
echo " Target : $API_BASE"
echo " API Key: ${API_KEY:0:4}****"
echo "================================================="
echo ""

# ─── 1. Health check (no auth required) ─────────────────────────────────────
info "1. Health check"
HTTP=$(curl -s -o /dev/null -w "%{http_code}" \
  --connect-timeout 10 --max-time 15 \
  "$API_BASE/api/v1/health")
if [ "$HTTP" = "200" ]; then
  ok "GET /health → 200"
elif [ "$HTTP" = "503" ]; then
  info "GET /health → 503 (degraded — DB or Ollama issue, but endpoint reachable)"
  ((PASS++))
else
  fail "GET /health → $HTTP (expected 200 or 503)"
fi

# ─── 2. Auth gate — no key should return 403 ─────────────────────────────────
info "2. Auth gate"
HTTP=$(curl -s -o /dev/null -w "%{http_code}" \
  --connect-timeout 10 --max-time 15 \
  "$API_BASE/api/v1/events")
if [ "$HTTP" = "403" ]; then
  ok "GET /events (no key) → 403"
else
  fail "GET /events (no key) → $HTTP (expected 403)"
fi

# ─── 3. Events list — valid key ──────────────────────────────────────────────
info "3. Events list"
BODY=$(curl -s --connect-timeout 10 --max-time 15 \
  -H "X-API-Key: $API_KEY" \
  "$API_BASE/api/v1/events")
HTTP=$(curl -s -o /dev/null -w "%{http_code}" \
  -H "X-API-Key: $API_KEY" \
  "$API_BASE/api/v1/events")
if [ "$HTTP" = "200" ]; then
  ok "GET /events (with key) → 200"
  # Verify response shape
  HAS_DATA=$(echo "$BODY" | python3 -c "import sys,json; d=json.load(sys.stdin); print('yes' if 'data' in d and 'total' in d else 'no')" 2>/dev/null || echo "no")
  if [ "$HAS_DATA" = "yes" ]; then
    ok "Response contains 'data' and 'total' fields"
  else
    fail "Response missing 'data' or 'total' field"
  fi
else
  fail "GET /events (with key) → $HTTP (expected 200)"
fi

# ─── 4. Pagination params validated ─────────────────────────────────────────
info "4. Input validation"
HTTP=$(curl -s -o /dev/null -w "%{http_code}" \
  -H "X-API-Key: $API_KEY" \
  "$API_BASE/api/v1/events?limit=99999")
if [ "$HTTP" = "422" ]; then
  ok "GET /events?limit=99999 → 422 (validation enforced)"
else
  fail "GET /events?limit=99999 → $HTTP (expected 422)"
fi

# ─── 5. UUID validation on path param ────────────────────────────────────────
HTTP=$(curl -s -o /dev/null -w "%{http_code}" \
  -H "X-API-Key: $API_KEY" \
  "$API_BASE/api/v1/events/not-a-uuid")
if [ "$HTTP" = "422" ]; then
  ok "GET /events/not-a-uuid → 422 (UUID validation)"
else
  fail "GET /events/not-a-uuid → $HTTP (expected 422)"
fi

# ─── 6. 404 + trace_id in error body ─────────────────────────────────────────
info "5. 404 + trace_id"
FAKE_UUID="00000000-0000-0000-0000-000000000000"
HTTP=$(curl -s -o /dev/null -w "%{http_code}" \
  -H "X-API-Key: $API_KEY" \
  "$API_BASE/api/v1/events/$FAKE_UUID")
if [ "$HTTP" = "404" ]; then
  ok "GET /events/$FAKE_UUID → 404"
else
  fail "GET /events/$FAKE_UUID → $HTTP (expected 404)"
fi

ERROR_BODY=$(curl -s \
  -H "X-API-Key: $API_KEY" \
  "$API_BASE/api/v1/events/$FAKE_UUID")
HAS_TRACE=$(echo "$ERROR_BODY" | python3 -c \
  "import sys,json; d=json.load(sys.stdin); det=d.get('detail',{}); print('yes' if 'trace_id' in str(det) else 'no')" \
  2>/dev/null || echo "no")
if [ "$HAS_TRACE" = "yes" ]; then
  ok "404 error body includes trace_id"
else
  fail "404 error body missing trace_id"
fi

# ─── 7. OpenAPI docs accessible ──────────────────────────────────────────────
info "6. OpenAPI docs"
HTTP=$(curl -s -o /dev/null -w "%{http_code}" \
  --connect-timeout 10 --max-time 15 \
  "$API_BASE/docs")
if [ "$HTTP" = "200" ]; then
  ok "GET /docs → 200 (FR-20 OpenAPI docs accessible)"
else
  fail "GET /docs → $HTTP (expected 200)"
fi

HTTP=$(curl -s -o /dev/null -w "%{http_code}" \
  --connect-timeout 10 --max-time 15 \
  "$API_BASE/openapi.json")
if [ "$HTTP" = "200" ]; then
  ok "GET /openapi.json → 200"
else
  fail "GET /openapi.json → $HTTP (expected 200)"
fi

# ─── 8. Stats endpoint ───────────────────────────────────────────────────────
info "7. Stats"
HTTP=$(curl -s -o /dev/null -w "%{http_code}" \
  -H "X-API-Key: $API_KEY" \
  "$API_BASE/api/v1/stats/summary")
if [ "$HTTP" = "200" ]; then
  ok "GET /stats/summary → 200"
else
  fail "GET /stats/summary → $HTTP (expected 200)"
fi

# ─── Summary ─────────────────────────────────────────────────────────────────
echo ""
echo "================================================="
echo " Results: ${PASS} passed, ${FAIL} failed"
echo "================================================="

if [ "$FAIL" -gt 0 ]; then
  echo -e "${RED}SMOKE TEST FAILED — $FAIL check(s) did not pass${NC}"
  exit 1
else
  echo -e "${GREEN}✅ All smoke tests passed${NC}"
  exit 0
fi
