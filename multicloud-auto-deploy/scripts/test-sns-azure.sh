#!/usr/bin/env bash
# ==============================================================
# test-sns-azure.sh — End-to-End test suite for Azure simple-sns
# ==============================================================
#
# Tests the full simple-sns stack on Azure staging:
#   - Azure Front Door CDN + frontend-web Function App (SSR/FastAPI)
#   - API Function App (FastAPI) backed by Cosmos DB
#   - Azure AD protected endpoints
#   - Image upload (Blob Storage SAS URL generation)
#   - Post CRUD with images
#
# Usage:
#   # Public-only tests (no auth token required):
#   ./scripts/test-sns-azure.sh
#
#   # Full authenticated tests:
#   ./scripts/test-sns-azure.sh --token <azure-ad-access-token>
#
#   # Override default Front Door / API URLs:
#   ./scripts/test-sns-azure.sh \
#     --fd   https://mcad-staging-d45ihd-dseygrc9c3a3htgj.z01.azurefd.net \
#     --api  https://multicloud-auto-deploy-staging-func-d8a2guhfere0etcq.japaneast-01.azurewebsites.net \
#     --token <token> --verbose
#
# How to get an Azure AD access token for testing:
#   1. Open https://mcad-staging-d45ihd-dseygrc9c3a3htgj.z01.azurefd.net/sns/ in a browser
#   2. Log in with your Azure AD account
#   3. Open DevTools → Application → Cookies
#   4. Copy the value of the `access_token` cookie
#   5. Pass it as --token <value>
#
# Exit codes:
#   0 — All executed tests passed
#   1 — One or more tests failed
#   2 — Missing required dependency (curl, jq)
#
# ==============================================================

set -euo pipefail

# ── defaults ──────────────────────────────────────────────────
FD_URL="${FD_URL:-https://mcad-staging-d45ihd-dseygrc9c3a3htgj.z01.azurefd.net}"
FW_URL="${FW_URL:-https://multicloud-auto-deploy-staging-frontend-web.azurewebsites.net}"
API_URL="${API_URL:-https://multicloud-auto-deploy-staging-func-d8a2guhfere0etcq.japaneast-01.azurewebsites.net}"
TOKEN=""
VERBOSE=false
SKIP_CLEANUP=false

# ── colours ───────────────────────────────────────────────────
RED='\033[0;31m'; GREEN='\033[0;32m'
YELLOW='\033[1;33m'; BLUE='\033[0;34m'; CYAN='\033[0;36m'
BOLD='\033[1m'; NC='\033[0m'

# ── counters ──────────────────────────────────────────────────
PASS=0; FAIL=0; SKIP=0

# ── helpers ───────────────────────────────────────────────────
log()  { echo -e "${BLUE}[INFO]${NC}  $*"; }
ok()   { echo -e "${GREEN}[PASS]${NC}  $*"; PASS=$((PASS + 1)); }
fail() { echo -e "${RED}[FAIL]${NC}  $*"; FAIL=$((FAIL + 1)); }
warn() { echo -e "${YELLOW}[WARN]${NC}  $*"; }
skip() { echo -e "${CYAN}[SKIP]${NC}  $*"; SKIP=$((SKIP + 1)); }
sep()  { echo -e "${YELLOW}────────────────────────────────────────${NC}"; }

die() { echo -e "${RED}ERROR: $*${NC}" >&2; exit 2; }

usage() {
  cat <<EOF
Usage: $0 [OPTIONS]

Options:
  -f, --fd    <url>    Front Door base URL  (default: $FD_URL)
  -w, --fw    <url>    Frontend-web Function App direct URL (default: $FW_URL)
  -a, --api   <url>    API Function App base URL (default: $API_URL)
  -t, --token <token>  Azure AD access token (required for auth tests)
  -v, --verbose        Print full response bodies
  -s, --skip-cleanup   Do not delete posts created during the test run
  -h, --help           Show this help

Examples:
  $0 --token eyJ0eXAi...
  $0 --fd https://my-fd.azurefd.net --token eyJ...
EOF
}

# ── arg parsing ───────────────────────────────────────────────
while [[ $# -gt 0 ]]; do
  case $1 in
    -f|--fd)    FD_URL="$2";  shift 2 ;;
    -w|--fw)    FW_URL="$2";  shift 2 ;;
    -a|--api)   API_URL="$2"; shift 2 ;;
    -t|--token) TOKEN="$2";   shift 2 ;;
    -v|--verbose) VERBOSE=true; shift ;;
    -s|--skip-cleanup) SKIP_CLEANUP=true; shift ;;
    -h|--help)  usage; exit 0 ;;
    *) echo -e "${RED}Unknown option: $1${NC}"; usage; exit 1 ;;
  esac
done

FD_URL="${FD_URL%/}"
FW_URL="${FW_URL%/}"
API_URL="${API_URL%/}"

# ── dependency check ──────────────────────────────────────────
command -v curl >/dev/null 2>&1 || die "curl is required but not installed"
command -v jq   >/dev/null 2>&1 || die "jq is required but not installed"

# ── test runner ───────────────────────────────────────────────
LAST_STATUS=0
LAST_BODY=""
CREATED_POST_IDS=()

run_test() {
  local label="$1"; shift
  local method="$1"; shift
  local url="$1";    shift

  local expect=200
  local data=""
  local extra_headers=()

  while [[ $# -gt 0 ]]; do
    case $1 in
      --expect) expect="$2"; shift 2 ;;
      --data)   data="$2";   shift 2 ;;
      --header) extra_headers+=("-H" "$2"); shift 2 ;;
      *) shift ;;
    esac
  done

  local curl_args=(-s -o /tmp/azure_sns_test_body -w "%{http_code}" -X "$method"
                   --max-time 25 --compressed)
  [[ -n "$data" ]] && curl_args+=(-H "Content-Type: application/json" -d "$data")
  for h in "${extra_headers[@]}"; do curl_args+=("$h"); done
  curl_args+=("$url")

  local status
  status=$(curl "${curl_args[@]}" 2>/dev/null || echo "000")
  LAST_STATUS="$status"
  LAST_BODY=$(cat /tmp/azure_sns_test_body 2>/dev/null || echo "")

  if [[ "$status" == "$expect" ]]; then
    ok "$label  [HTTP $status]"
    [[ "$VERBOSE" == true ]] && echo "$LAST_BODY" | jq . 2>/dev/null || true
    return 0
  else
    fail "$label  [expected HTTP $expect, got HTTP $status]"
    [[ -n "$LAST_BODY" ]] && echo "  Response: $(echo "$LAST_BODY" | head -c 300)"
    return 1
  fi
}

# ── banner ────────────────────────────────────────────────────
echo ""
echo -e "${BOLD}============================================================${NC}"
echo -e "${BOLD}  Azure Simple-SNS — End-to-End Test Suite${NC}"
echo -e "${BOLD}============================================================${NC}"
echo -e "  Front Door  : ${CYAN}$FD_URL${NC}"
echo -e "  Frontend-web: ${CYAN}$FW_URL${NC}"
echo -e "  API Function: ${CYAN}$API_URL${NC}"
echo -e "  Auth token  : $([ -n "$TOKEN" ] && echo "${CYAN}provided${NC}" || echo "${YELLOW}not provided (auth tests will be skipped)${NC}")"
echo ""

# ════════════════════════════════════════════════════════════
sep
echo -e "${BOLD}Section 1 — Frontend-web Function App (direct)${NC}"
sep

run_test "Frontend-web /sns/health returns 200" \
  GET "$FW_URL/sns/health"

if echo "$LAST_BODY" | jq -e '.status == "ok"' >/dev/null 2>&1; then
  ok "  .status == \"ok\" (FastAPI running)"
else
  fail "  Unexpected /sns/health response: $(echo "$LAST_BODY" | head -c 200)"
fi

run_test "Frontend-web /sns/ returns 200 (HTML)" \
  GET "$FW_URL/sns/"

SNS_CT=$(curl -s --max-time 20 -D - "$FW_URL/sns/" -o /dev/null 2>/dev/null \
  | grep -i '^content-type:' | head -1 | tr -d '\r\n' || echo "")
if echo "$SNS_CT" | grep -qi 'text/html'; then
  ok "  SNS page Content-Type is text/html  [$SNS_CT]"
else
  fail "  SNS page unexpected Content-Type: $SNS_CT"
fi

run_test "Frontend-web /sns/login page returns 200 (HTML)" \
  GET "$FW_URL/sns/login"

run_test "Frontend-web /sns/static/app.css returns 200" \
  GET "$FW_URL/sns/static/app.css"

# ════════════════════════════════════════════════════════════
sep
echo -e "${BOLD}Section 2 — API Function App (direct)${NC}"
sep

run_test "API /api/health returns 200" \
  GET "$API_URL/api/health"

if echo "$LAST_BODY" | jq -e '.status == "ok"' >/dev/null 2>&1; then
  ok "  .provider=$(echo "$LAST_BODY" | jq -r '.provider // "unknown"')"
else
  fail "  Unexpected /api/health response"
fi

run_test "API GET /api/posts returns 200 (unauthenticated)" \
  GET "$API_URL/api/posts"

if echo "$LAST_BODY" | jq -e '.items' >/dev/null 2>&1; then
  POST_COUNT=$(echo "$LAST_BODY" | jq '.items | length')
  ok "  .items array present (${POST_COUNT} posts)"
else
  fail "  .items missing in /api/posts response"
fi

# ════════════════════════════════════════════════════════════
sep
echo -e "${BOLD}Section 3 — Front Door CDN routing${NC}"
sep

run_test "Front Door /sns/health via CDN returns 200" \
  GET "$FD_URL/sns/health"

run_test "Front Door /sns/ returns 200 (HTML)" \
  GET "$FD_URL/sns/"

run_test "Front Door /sns/login returns 200 (HTML)" \
  GET "$FD_URL/sns/login"

run_test "Front Door /sns/static/app.css returns 200 (static file)" \
  GET "$FD_URL/sns/static/app.css"

# ════════════════════════════════════════════════════════════
sep
echo -e "${BOLD}Section 4 — Auth guard (unauthenticated = 401)${NC}"
sep

run_test "POST /api/posts without token returns 401" \
  POST "$API_URL/api/posts" \
  --data '{"content":"azure auth guard test"}' \
  --expect 401

run_test "POST /api/uploads/presigned-urls without token returns 401" \
  POST "$API_URL/api/uploads/presigned-urls" \
  --data '{"count":1,"contentTypes":["image/jpeg"]}' \
  --expect 401

# ════════════════════════════════════════════════════════════
sep
echo -e "${BOLD}Section 5 — Authenticated endpoints${NC}"
sep

if [[ -z "$TOKEN" ]]; then
  warn "No --token provided; skipping Sections 5, 6."
  warn "Re-run with: $0 --token <azure-ad-access-token>"
  SKIP=$((SKIP + 7))
else
  AUTHH="Authorization: Bearer $TOKEN"

  # 5-1. Get profile
  run_test "GET /api/profile returns 200" \
    GET "$API_URL/api/profile" --header "$AUTHH"

  # 5-2. Create post (text only)
  run_test "POST /api/posts creates a new post" \
    POST "$API_URL/api/posts" \
    --header "$AUTHH" \
    --data "{\"content\":\"Azure E2E test post $(date +%s)\"}"

  if echo "$LAST_BODY" | jq -e '.id' >/dev/null 2>&1; then
    POST_ID=$(echo "$LAST_BODY" | jq -r '.id')
    ok "  Post created: id=$POST_ID"
    CREATED_POST_IDS+=("$POST_ID")
  else
    fail "  No .id in post creation response"
    POST_ID=""
  fi

  # 5-3. Get post by ID
  if [[ -n "${POST_ID:-}" ]]; then
    run_test "GET /api/posts/$POST_ID returns 200" \
      GET "$API_URL/api/posts/$POST_ID" --header "$AUTHH"
  fi

  # 5-4. Generate presigned URL for image upload
  run_test "POST /api/uploads/presigned-urls returns 200" \
    POST "$API_URL/api/uploads/presigned-urls" \
    --header "$AUTHH" \
    --data '{"count":1,"contentTypes":["image/jpeg"]}'

  if echo "$LAST_BODY" | jq -e '.[0].uploadUrl' >/dev/null 2>&1; then
    ok "  Presigned upload URL generated (Blob Storage SAS)"
  else
    fail "  Presigned URL missing in response"
  fi

  # 5-5. Create post with image_url
  run_test "POST /api/posts with image_url creates post" \
    POST "$API_URL/api/posts" \
    --header "$AUTHH" \
    --data "{\"content\":\"Azure E2E test post with image $(date +%s)\",\"image_url\":\"https://mcadwebd45ihd.blob.core.windows.net/images/test.jpg\"}"

  if echo "$LAST_BODY" | jq -e '.id' >/dev/null 2>&1; then
    IMG_POST_ID=$(echo "$LAST_BODY" | jq -r '.id')
    ok "  Post with image_url created: id=$IMG_POST_ID"
    CREATED_POST_IDS+=("$IMG_POST_ID")
  fi

  # 5-6. List posts — should include ours
  run_test "GET /api/posts returns list with test posts" \
    GET "$API_URL/api/posts?limit=20" --header "$AUTHH"

  # ══════════════════════════════════════════════════════
  sep
  echo -e "${BOLD}Section 6 — Cleanup (delete test posts)${NC}"
  sep

  if [[ "$SKIP_CLEANUP" == "false" && ${#CREATED_POST_IDS[@]} -gt 0 ]]; then
    for pid in "${CREATED_POST_IDS[@]}"; do
      run_test "DELETE /api/posts/$pid returns 200" \
        DELETE "$API_URL/api/posts/$pid" \
        --header "$AUTHH" \
        --expect 200
    done
  else
    warn "Skipping cleanup (--skip-cleanup or no posts created)"
    SKIP=$((SKIP + ${#CREATED_POST_IDS[@]}))
  fi
fi

# ════════════════════════════════════════════════════════════
sep
echo ""
echo -e "${BOLD}============================================================${NC}"
echo -e "${BOLD}  Test Results${NC}"
echo -e "${BOLD}============================================================${NC}"
echo -e "  ${GREEN}PASS${NC}: $PASS"
echo -e "  ${RED}FAIL${NC}: $FAIL"
echo -e "  ${CYAN}SKIP${NC}: $SKIP"
total=$((PASS + FAIL + SKIP))
echo -e "  Total: $total"
echo ""

if [[ $FAIL -eq 0 ]]; then
  echo -e "${GREEN}${BOLD}  ✅ All tests passed!${NC}"
  echo ""
  exit 0
else
  echo -e "${RED}${BOLD}  ❌ $FAIL test(s) failed.${NC}"
  echo ""
  exit 1
fi
