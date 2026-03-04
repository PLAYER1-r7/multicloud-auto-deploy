#!/usr/bin/env bash
# ============================================================
# test-sns-gcp.sh — End-to-End test suite for GCP simple-sns
# ============================================================
#
# Tests the full simple-sns stack on GCP staging:
#   - Cloud CDN (Global Load Balancer + GCS backend) + React SPA (/sns/)
#   - API Cloud Run (FastAPI) backed by Firestore
#   - Firebase-protected endpoints
#   - Image upload (GCS presigned URL generation)
#   - Post CRUD with images
#
# Usage:
#   # Public-only tests (no auth token required):
#   ./scripts/test-sns-gcp.sh
#
#   # Full authenticated tests:
#   ./scripts/test-sns-gcp.sh --token <firebase-id-token>
#
#   # Override default CDN IP / API URL:
#   ./scripts/test-sns-gcp.sh \
#     --cdn  https://www.gcp.ashnova.jp \
#     --api  https://multicloud-auto-deploy-staging-api-son5b3ml7a-an.a.run.app \
#     --token <token> --verbose
#
# How to get a Firebase ID token for testing:
#   1. Open https://www.gcp.ashnova.jp/sns/ in a browser
#   2. Log in with your Google account (Firebase popup)
#   3. Open DevTools → Application → Local Storage → select the page origin
#   4. Copy the value of the `id_token` key
#   5. Pass it as --token <value>
#
# Alternatively, using gcloud CLI:
#   TOKEN=$(gcloud auth print-identity-token)
#   ./scripts/test-sns-gcp.sh --token "$TOKEN"
#
# Exit codes:
#   0 — All executed tests passed
#   1 — One or more tests failed
#   2 — Missing required dependency (curl, jq)
#
# ============================================================

set -euo pipefail

# ── defaults ────────────────────────────────────────────────
# (URLs resolved after arg parsing; see "resolve URLs" section below)
_ENV_=staging
_READ_ONLY_=false
_WRITE_=false
_CDN_URL_EXPLICIT=false
_API_URL_EXPLICIT=false
TOKEN=""
VERBOSE=false
SKIP_CLEANUP=false
AUTO_TOKEN=false

# ── colours ─────────────────────────────────────────────────
RED='\033[0;31m'; GREEN='\033[0;32m'
YELLOW='\033[1;33m'; BLUE='\033[0;34m'; CYAN='\033[0;36m'
BOLD='\033[1m'; NC='\033[0m'

# ── counters ────────────────────────────────────────────────
PASS=0; FAIL=0; SKIP=0

# ── helpers ─────────────────────────────────────────────────
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
  -c, --cdn   <url>    Cloud CDN (LB) base URL  (default: https://www.gcp.ashnova.jp)
  -a, --api   <url>    Cloud Run API base URL   (default: https://multicloud-auto-deploy-staging-api-son5b3ml7a-an.a.run.app)
  -t, --token <token>  Firebase ID token (required for auth tests)
      --auto-token     Auto-acquire token via gcloud auth print-identity-token
  -v, --verbose        Print full response bodies
  -s, --skip-cleanup   Do not delete posts created during the test run
  -h, --help           Show this help

Examples:
  # Staging with manual token:
  $0 --token \$(gcloud auth print-identity-token)
  # Staging with auto token:
  $0 --auto-token
  # Production read-only:
  $0 --env production
  # Production full test:
  $0 --env production --write --auto-token
  $0 --cdn https://www.gcp.ashnova.jp --api https://multicloud-auto-deploy-production-api-son5b3ml7a-an.a.run.app --token eyJ...
EOF
}

# ── arg parsing ─────────────────────────────────────────────
while [[ $# -gt 0 ]]; do
  case $1 in
    -c|--cdn)   CDN_URL="$2";  _CDN_URL_EXPLICIT=true; shift 2 ;;
    -a|--api)   API_URL="$2";  _API_URL_EXPLICIT=true; shift 2 ;;
    -e|--env)
      case "$2" in
        production|prod) _ENV_=production; _READ_ONLY_=true ;;
        staging|stag)    _ENV_=staging ;;
        *) die "Unknown env: '$2'. Use staging or production." ;;
      esac
      shift 2 ;;
    -r|--read-only)    _READ_ONLY_=true;  SKIP_CLEANUP=true; shift ;;
    --write)           _WRITE_=true;      shift ;;
    -t|--token) TOKEN="$2";    shift 2 ;;
    --auto-token)      AUTO_TOKEN=true;   shift ;;
    -v|--verbose) VERBOSE=true; shift ;;
    -s|--skip-cleanup) SKIP_CLEANUP=true; shift ;;
    -h|--help)  usage; exit 0 ;;
    *) echo -e "${RED}Unknown option: $1${NC}"; usage; exit 1 ;;
  esac
done

# ── resolve URLs and read-only flag ─────────────────────────
READ_ONLY=$_READ_ONLY_
[[ $_WRITE_ == true ]] && READ_ONLY=false

if [[ $_ENV_ == production ]]; then
  [[ $_CDN_URL_EXPLICIT == false ]] && CDN_URL="${CDN_URL:-https://www.gcp.ashnova.jp}"
  [[ $_API_URL_EXPLICIT == false ]] && API_URL="${API_URL:-https://multicloud-auto-deploy-production-api-son5b3ml7a-an.a.run.app}"
else
  # GCP staging: Cloud Function serves both frontend (Cloud Storage) and API
  CDN_URL="${CDN_URL:-https://multicloud-auto-deploy-staging-api-son5b3ml7a-an.a.run.app}"
  API_URL="${API_URL:-https://multicloud-auto-deploy-staging-api-son5b3ml7a-an.a.run.app}"
fi
[[ $READ_ONLY == true ]] && SKIP_CLEANUP=true

CDN_URL="${CDN_URL%/}"
API_URL="${API_URL%/}"

# ── dependency check ────────────────────────────────────────
command -v curl    >/dev/null 2>&1 || die "curl is required but not installed"
command -v jq      >/dev/null 2>&1 || die "jq is required but not installed"
command -v python3 >/dev/null 2>&1 || die "python3 is required but not installed"

# ── auto token acquisition (gcloud) ──────────────────────────
if [[ -z "$TOKEN" && "$AUTO_TOKEN" == true ]]; then
  if command -v gcloud >/dev/null 2>&1; then
    log "Auto-acquiring GCP identity token via gcloud ..."
    TOKEN=$(gcloud auth print-identity-token 2>/dev/null || echo "")
    if [[ -n "$TOKEN" && "$TOKEN" != "None" ]]; then
      log "  ✓ gcloud identity token acquired (${TOKEN:0:20}...)"
    else
      warn "  gcloud auth print-identity-token failed — run: gcloud auth login"
      TOKEN=""
    fi
  else
    warn "  gcloud not found — install Google Cloud SDK for --auto-token support"
  fi
fi

# ── shared test image (1x1 transparent PNG, 68 bytes) ───────
python3 -c "
import base64, sys
sys.stdout.buffer.write(base64.b64decode(
  'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=='
))
" > /tmp/test_upload_gcp.png 2>/dev/null || true

# ── test runner ─────────────────────────────────────────────
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

  local curl_args=(-s -o /tmp/gcp_sns_test_body -w "%{http_code}" -X "$method"
                   --max-time 25 --compressed)
  [[ -n "$data" ]] && curl_args+=(-H "Content-Type: application/json" -d "$data")
  for h in "${extra_headers[@]}"; do curl_args+=("$h"); done
  curl_args+=("$url")

  local status
  status=$(curl "${curl_args[@]}" 2>/dev/null || echo "000")
  LAST_STATUS="$status"
  LAST_BODY=$(cat /tmp/gcp_sns_test_body 2>/dev/null || echo "")

  if [[ "$status" == "$expect" ]]; then
    echo -e "${GREEN}[PASS]${NC}  $label  [HTTP $status]"
    PASS=$((PASS + 1))
    [[ "$VERBOSE" == true ]] && echo "$LAST_BODY" | jq . 2>/dev/null || true
    return 0
  else
    echo -e "${RED}[FAIL]${NC}  $label  [expected HTTP $expect, got HTTP $status]"
    FAIL=$((FAIL + 1))
    [[ -n "$LAST_BODY" ]] && echo "  Response: $(echo "$LAST_BODY" | head -c 300)"
    return 1
  fi
}

# ── banner ───────────────────────────────────────────────────
echo ""
echo -e "${BOLD}============================================================${NC}"
echo -e "${BOLD}  GCP Simple-SNS — End-to-End Test Suite${NC}"
echo -e "${BOLD}============================================================${NC}"
echo -e "  Cloud CDN  : ${CYAN}$CDN_URL${NC}"
echo -e "  Cloud Run  : ${CYAN}$API_URL${NC}"
echo -e "  Auth token : $([ -n "$TOKEN" ] && echo "${CYAN}provided${NC}" || echo "${YELLOW}not provided (auth tests will be skipped)${NC}")"
echo ""

# ════════════════════════════════════════════════════════════
sep
echo -e "${BOLD}Section 1 — Cloud CDN + React SPA (static)${NC}"
sep

run_test "CDN GET /sns/ returns 200" \
  GET "$CDN_URL/sns/"

# Verify Content-Type is text/html
SNS_CT=$(curl -s --max-time 25 -D - "$CDN_URL/sns/" -o /dev/null 2>/dev/null \
  | grep -i '^content-type:' | head -1 | tr -d '\r\n' || echo "")
if echo "$SNS_CT" | grep -qi 'text/html'; then
  ok "  SNS page Content-Type is text/html  [$SNS_CT]"
else
  fail "  SNS page unexpected Content-Type: $SNS_CT"
fi

# Verify the React SPA root element is present
SNS_BODY=$(curl -s --max-time 25 --compressed "$CDN_URL/sns/" 2>/dev/null || echo "")
if echo "$SNS_BODY" | grep -q '<div id="root"'; then
  ok "  React SPA root element (<div id=\"root\">) found"
else
  fail "  React SPA root element not found in /sns/ page"
fi

# Verify no SSR/Python artifacts
if echo "$SNS_BODY" | grep -qi 'jinja\|fastapi\|uvicorn'; then
  fail "  /sns/ page contains unexpected SSR artifacts (Jinja/FastAPI)"
else
  ok "  No SSR artifacts in React SPA page"
fi

# Verify VITE_API_URL was injected correctly (no localhost in JS bundle)
if echo "$SNS_BODY" | grep -q "localhost"; then
  fail "  CDN sanity: page exposes 'localhost' — VITE_API_URL may not have been set at build time"
else
  ok "  CDN sanity: page does not expose 'localhost'"
fi

# Landing page
run_test "CDN GET / returns 200 (landing page)" \
  GET "$CDN_URL/"

# ════════════════════════════════════════════════════════════
sep
echo -e "${BOLD}Section 2 — API Health (Cloud Run, public)${NC}"
sep

run_test "GET /health returns 200" \
  GET "$API_URL/health"

if echo "$LAST_BODY" | jq -e '.status == "ok"' >/dev/null 2>&1; then
  ok "  .status == \"ok\""
  PROVIDER=$(echo "$LAST_BODY" | jq -r '.provider // "unknown"')
  log "  .provider = $PROVIDER"
else
  fail "  .status != \"ok\" in /health response"
fi

run_test "GET /posts returns 200 (unauthenticated)" \
  GET "$API_URL/posts"

if echo "$LAST_BODY" | jq -e '.items' >/dev/null 2>&1; then
  COUNT=$(echo "$LAST_BODY" | jq '.items | length')
  ok "  .items array present ($COUNT posts)"
else
  fail "  .items missing in /posts response"
fi

# ════════════════════════════════════════════════════════════
sep
echo -e "${BOLD}Section 3 — Auth guard (unauthenticated should return 401)${NC}"
sep

run_test "POST /posts without token returns 401" \
  POST "$API_URL/posts" \
  --data '{"content":"gcp auth guard test"}' \
  --expect 401

run_test "POST /uploads/presigned-urls without token returns 401" \
  POST "$API_URL/uploads/presigned-urls" \
  --data '{"count":1,"contentTypes":["image/jpeg"]}' \
  --expect 401

run_test "GET /profile without token returns 401" \
  GET "$API_URL/profile" \
  --expect 401

# ════════════════════════════════════════════════════════════
sep
echo -e "${BOLD}Section 4 — Authenticated endpoints${NC}"
sep

if [[ $READ_ONLY == true ]]; then
  warn "Read-only mode: skipping Sections 4-7 (write tests)."
  warn "Re-run with --write to enable: $0 --env production --write --token <token>"
  skip "Section 4 - Authenticated endpoints"
  skip "Section 5 - Image upload / GCS presigned URLs"
  skip "Section 6 - Post with imageKeys validation"
  skip "Section 7 - Cleanup"
elif [[ -z "$TOKEN" ]]; then
  warn "No --token provided; skipping Sections 4, 5, 6."
  warn "Re-run with: $0 --token \"\$(gcloud auth print-identity-token)\""
  SKIP=$((SKIP + 8))
else
  AUTHH="Authorization: Bearer $TOKEN"

  # 4-1. Get profile
  run_test "GET /profile returns 200" \
    GET "$API_URL/profile" --header "$AUTHH"

  if echo "$LAST_BODY" | jq -e '.userId // .user_id' >/dev/null 2>&1; then
    USER_ID=$(echo "$LAST_BODY" | jq -r '.userId // .user_id // ""')
    ok "  Profile found: userId=$USER_ID"
  fi

  # 4-2. Create post (text only)
  run_test "POST /posts (text) returns 201" \
    POST "$API_URL/posts" \
    --header "$AUTHH" \
    --data '{"content":"[test] GCP simple-sns E2E test post 🧪","isMarkdown":false}' \
    --expect 201
  TEXT_POST_ID=$(echo "$LAST_BODY" | jq -r '.postId // .post_id // ""' 2>/dev/null)
  if [[ -n "$TEXT_POST_ID" && "$TEXT_POST_ID" != "null" ]]; then
    ok "  Created text post: $TEXT_POST_ID"
    CREATED_POST_IDS+=("$TEXT_POST_ID")
  else
    warn "  Could not extract postId from response — cleanup may be incomplete"
  fi

  # 4-3. Get the created post
  if [[ -n "${TEXT_POST_ID:-}" && "$TEXT_POST_ID" != "null" ]]; then
    run_test "GET /posts/:id returns 200" \
      GET "$API_URL/posts/$TEXT_POST_ID" --header "$AUTHH"
  else
    skip "GET /posts/:id — post creation failed, skipping"
  fi

  # 4-4. Update the post
  if [[ -n "${TEXT_POST_ID:-}" && "$TEXT_POST_ID" != "null" ]]; then
    run_test "PUT /posts/:id returns 200" \
      PUT "$API_URL/posts/$TEXT_POST_ID" \
      --header "$AUTHH" \
      --data '{"content":"[test] updated by GCP E2E test ✅"}' \
      --expect 200
  else
    skip "PUT /posts/:id — post creation failed, skipping"
  fi

  # ════════════════════════════════════════════════════════
  sep
  echo -e "${BOLD}Section 5 — Image upload (GCS presigned URL)${NC}"
  sep

  # 5-1. Request presigned URLs
  run_test "POST /uploads/presigned-urls (count=2) returns 200" \
    POST "$API_URL/uploads/presigned-urls" \
    --header "$AUTHH" \
    --data '{"count":2,"contentTypes":["image/jpeg","image/png"]}' \
    --expect 200

  URL_COUNT=$(echo "$LAST_BODY" | jq '.urls | length' 2>/dev/null || echo 0)
  if [[ "$URL_COUNT" == "2" ]]; then
    ok "  Received $URL_COUNT presigned URLs"
  else
    fail "  Expected 2 presigned URLs, got $URL_COUNT"
  fi

  # 5-2. Validate presigned URL format + GCS signature
  FIRST_UPLOAD_URL=$(echo "$LAST_BODY" | jq -r '.urls[0].url // ""' 2>/dev/null)
  FIRST_UPLOAD_KEY=$(echo "$LAST_BODY" | jq -r '.urls[0].key // .urls[0].imageKey // ""' 2>/dev/null)
  if echo "$FIRST_UPLOAD_URL" | grep -q "^https://storage.googleapis.com"; then
    ok "  Presigned URL is a valid GCS HTTPS URL"
  elif [[ -n "$FIRST_UPLOAD_URL" ]]; then
    warn "  Presigned URL format unexpected: ${FIRST_UPLOAD_URL:0:80}..."
  fi
  if echo "$FIRST_UPLOAD_URL" | grep -qiE 'X-Goog-Signature=|x-goog-signature='; then
    ok "  Presigned URL contains X-Goog-Signature ✓"
  elif [[ -n "$FIRST_UPLOAD_URL" ]]; then
    warn "  X-Goog-Signature not found — GCS signed URL may be using service account key (check GCP config)"
  fi

  # 5-3. ★ Binary PUT: 実際にテスト画像を GCS へアップロード
  UPLOAD_POST_ID=""
  if [[ -n "$FIRST_UPLOAD_URL" && "$FIRST_UPLOAD_URL" != "null" && -s /tmp/test_upload_gcp.png ]]; then
    PUT_STATUS=$(curl -s -o /tmp/put_resp_gcp.txt -w "%{http_code}" \
      -X PUT \
      -H "Content-Type: image/jpeg" \
      --data-binary @/tmp/test_upload_gcp.png \
      --max-time 20 \
      "$FIRST_UPLOAD_URL" 2>/dev/null || echo "000")
    if [[ "$PUT_STATUS" == "200" ]]; then
      ok "  PUT test image → GCS presigned URL: HTTP 200 ✓"
    else
      fail "  PUT test image → GCS: HTTP $PUT_STATUS (expected 200)"
      [[ -s /tmp/put_resp_gcp.txt ]] && echo "  Response: $(head -c 200 /tmp/put_resp_gcp.txt)"
    fi

    # 5-4. ★ アップロードしたキーで投稿を作成し imageUrls が取得可能か検証
    if [[ -n "$FIRST_UPLOAD_KEY" && "$FIRST_UPLOAD_KEY" != "null" && "$PUT_STATUS" == "200" ]]; then
      IMG_POST_DATA=$(python3 -c "import json; print(json.dumps({'content':'[test] GCP E2E real image upload', 'imageKeys':['$FIRST_UPLOAD_KEY']}))")
      run_test "POST /posts with real uploaded imageKey returns 201" \
        POST "$API_URL/posts" \
        --header "$AUTHH" \
        --data "$IMG_POST_DATA" \
        --expect 201
      UPLOAD_POST_ID=$(echo "$LAST_BODY" | jq -r '.postId // .post_id // ""' 2>/dev/null)
      [[ -n "$UPLOAD_POST_ID" && "$UPLOAD_POST_ID" != "null" ]] && CREATED_POST_IDS+=("$UPLOAD_POST_ID")

      # GET /posts/:id → imageUrls が HTTP 200 で取得できるか確認
      if [[ -n "$UPLOAD_POST_ID" && "$UPLOAD_POST_ID" != "null" ]]; then
        run_test "GET /posts/$UPLOAD_POST_ID returns 200" \
          GET "$API_URL/posts/$UPLOAD_POST_ID" --header "$AUTHH"
        REAL_IMG_URL=$(echo "$LAST_BODY" | jq -r '.imageUrls[0] // ""' 2>/dev/null)
        if [[ -n "$REAL_IMG_URL" && "$REAL_IMG_URL" != "null" ]]; then
          IMG_HTTP=$(curl -s -o /dev/null -w "%{http_code}" --max-time 15 "$REAL_IMG_URL" 2>/dev/null || echo "000")
          if [[ "$IMG_HTTP" == "200" ]]; then
            ok "  GET imageUrl → HTTP 200 ✓ (image displayable)"
          else
            fail "  GET imageUrl → HTTP $IMG_HTTP (image not displayable!) URL: ${REAL_IMG_URL:0:80}"
          fi
        else
          warn "  No imageUrls in response — skipping image accessibility check"
        fi
      fi
    else
      warn "  key not in presigned-urls response or PUT failed — skipping real-upload post test"
    fi
  else
    warn "  No presigned URL or test PNG missing — skipping binary PUT test"
  fi

  # 5-5. Upper bound: 16 files (max allowed)
  TYPES_16=$(python3 -c "import json; print(json.dumps({'count':16,'contentTypes':['image/jpeg']*16}))")
  run_test "POST /uploads/presigned-urls (count=16, max) returns 200" \
    POST "$API_URL/uploads/presigned-urls" \
    --header "$AUTHH" \
    --data "$TYPES_16" \
    --expect 200

  # 5-6. Over limit: 17 files should return 422
  TYPES_17=$(python3 -c "import json; print(json.dumps({'count':17,'contentTypes':['image/jpeg']*17}))")
  run_test "POST /uploads/presigned-urls (count=17, over limit) returns 422" \
    POST "$API_URL/uploads/presigned-urls" \
    --header "$AUTHH" \
    --data "$TYPES_17" \
    --expect 422

  # ════════════════════════════════════════════════════════
  sep
  echo -e "${BOLD}Section 6 — Post with imageKeys validation${NC}"
  sep

  # 6-1. Create post with imageKeys (up to 16)
  KEYS_16=$(python3 -c "
import json, uuid
keys = [f'testuser/{uuid.uuid4()}.jpg' for _ in range(16)]
print(json.dumps({'content': '[test] GCP post with 16 imageKeys', 'imageKeys': keys}))
")
  run_test "POST /posts with 16 imageKeys returns 201" \
    POST "$API_URL/posts" \
    --header "$AUTHH" \
    --data "$KEYS_16" \
    --expect 201
  POST_WITH_IMAGES_ID=$(echo "$LAST_BODY" | jq -r '.postId // .post_id // ""' 2>/dev/null)
  [[ -n "$POST_WITH_IMAGES_ID" && "$POST_WITH_IMAGES_ID" != "null" ]] && \
    CREATED_POST_IDS+=("$POST_WITH_IMAGES_ID")

  # 6-2. Over limit: 17 imageKeys should return 422
  KEYS_17=$(python3 -c "
import json, uuid
keys = [f'testuser/{uuid.uuid4()}.jpg' for _ in range(17)]
print(json.dumps({'content': '[test] should fail validation', 'imageKeys': keys}))
")
  run_test "POST /posts with 17 imageKeys returns 422 (validation)" \
    POST "$API_URL/posts" \
    --header "$AUTHH" \
    --data "$KEYS_17" \
    --expect 422

  # ════════════════════════════════════════════════════════
  sep
  echo -e "${BOLD}Section 7 — Cleanup (delete test posts)${NC}"
  sep

  if [[ "$SKIP_CLEANUP" == false && ${#CREATED_POST_IDS[@]} -gt 0 ]]; then
    for pid in "${CREATED_POST_IDS[@]}"; do
      run_test "DELETE /posts/$pid" \
        DELETE "$API_URL/posts/$pid" \
        --header "$AUTHH" \
        --expect 200
    done
  else
    if [[ "$SKIP_CLEANUP" == true ]]; then
      warn "Cleanup skipped (--skip-cleanup). Created post IDs:"
      for pid in "${CREATED_POST_IDS[@]}"; do echo "  $pid"; done
    fi
  fi
fi

# ════════════════════════════════════════════════════════════
echo ""
echo -e "${BOLD}============================================================${NC}"
echo -e "${BOLD}  Results${NC}"
echo -e "${BOLD}============================================================${NC}"
printf "  ${GREEN}Passed${NC} : %d\n" "$PASS"
printf "  ${RED}Failed${NC} : %d\n" "$FAIL"
printf "  ${CYAN}Skipped${NC}: %d\n" "$SKIP"
TOTAL=$((PASS + FAIL))
if [[ $TOTAL -gt 0 ]]; then
  RATE=$(awk "BEGIN {printf \"%.0f\", ($PASS/$TOTAL)*100}")
  printf "  Pass rate: %s%%\n" "$RATE"
fi
echo ""

if [[ $FAIL -eq 0 ]]; then
  echo -e "${GREEN}${BOLD}  ✅ All tests passed!${NC}"
  exit 0
else
  echo -e "${RED}${BOLD}  ❌ $FAIL test(s) failed.${NC}"
  exit 1
fi
