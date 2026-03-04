#!/usr/bin/env bash
# ==============================================================
# test-sns-azure.sh — End-to-End test suite for Azure simple-sns
# ==============================================================
#
# Tests the full simple-sns stack on Azure staging:
#   - Azure Front Door CDN + React SPA (static files served from Blob Storage, /sns/)
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
#   3. Open DevTools → Application → Local Storage → select the page origin
#   4. Copy the value of the `id_token` key
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
# (URLs resolved after arg parsing; see "resolve URLs" section below)
_ENV_=staging
_READ_ONLY_=false
_WRITE_=false
_FD_URL_EXPLICIT=false
_API_URL_EXPLICIT=false
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
  -f, --fd    <url>        Front Door base URL  (overrides --env default)
  -a, --api   <url>        Function App base URL (overrides --env default)
  -e, --env   <env>        Target environment: staging|production  (default: staging)
                           production URLs: www.azure.ashnova.jp + prod Function App
                           --env production implies --read-only
  -r, --read-only          Skip all write tests (Sections 5-6); safe for production
      --write              Allow write tests even when --env production is set
  -t, --token <token>      Azure AD access token (required for auth tests)
  -v, --verbose            Print full response bodies
  -s, --skip-cleanup       Do not delete posts created during the test run
  -h, --help               Show this help

Examples:
  # Staging (default):
  $0 --token eyJ0eXAi...
  # Production - read-only smoke test:
  $0 --env production
  # Production - full authenticated test (write tests enabled):
  $0 --env production --write --token eyJ0eXAi...
  # Custom URL override:
  $0 --fd https://my-fd.azurefd.net --token eyJ...
EOF
}

# ── arg parsing ───────────────────────────────────────────────
while [[ $# -gt 0 ]]; do
  case $1 in
    -f|--fd)    FD_URL="$2";  _FD_URL_EXPLICIT=true;  shift 2 ;;
    -a|--api)   API_URL="$2"; _API_URL_EXPLICIT=true; shift 2 ;;
    -e|--env)
      case "$2" in
        production|prod) _ENV_=production; _READ_ONLY_=true ;;
        staging|stag)    _ENV_=staging ;;
        *) die "Unknown env: '$2'. Use staging or production." ;;
      esac
      shift 2 ;;
    -r|--read-only)    _READ_ONLY_=true;  SKIP_CLEANUP=true; shift ;;
    --write)           _WRITE_=true;      shift ;;
    -t|--token) TOKEN="$2";   shift 2 ;;
    -v|--verbose) VERBOSE=true; shift ;;
    -s|--skip-cleanup) SKIP_CLEANUP=true; shift ;;
    -h|--help)  usage; exit 0 ;;
    *) echo -e "${RED}Unknown option: $1${NC}"; usage; exit 1 ;;
  esac
done

# ── resolve URLs and read-only flag ──────────────────────────
READ_ONLY=$_READ_ONLY_
[[ $_WRITE_ == true ]] && READ_ONLY=false

if [[ $_ENV_ == production ]]; then
  [[ $_FD_URL_EXPLICIT  == false ]] && FD_URL="${FD_URL:-https://www.azure.ashnova.jp}"
  [[ $_API_URL_EXPLICIT == false ]] && API_URL="${API_URL:-https://multicloud-auto-deploy-production-func-cfdne7ecbngnh0d0.japaneast-01.azurewebsites.net/api}"
else
  FD_URL="${FD_URL:-https://mcadwebd45ihd.z11.web.core.windows.net}"
  # Azure Functions default routePrefix is "api", so /health is at /api/health
  API_URL="${API_URL:-https://multicloud-auto-deploy-staging-func-d8a2guhfere0etcq.japaneast-01.azurewebsites.net}"
fi
[[ $READ_ONLY == true ]] && SKIP_CLEANUP=true

FD_URL="${FD_URL%/}"
API_URL="${API_URL%/}"

# ── dependency check ──────────────────────────────────────────
command -v curl    >/dev/null 2>&1 || die "curl is required but not installed"
command -v jq      >/dev/null 2>&1 || die "jq is required but not installed"
command -v python3 >/dev/null 2>&1 || die "python3 is required but not installed"

# ── shared test image (1x1 transparent PNG, 68 bytes) ───────
python3 -c "
import base64, sys
sys.stdout.buffer.write(base64.b64decode(
  'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=='
))
" > /tmp/test_upload_azure.png 2>/dev/null || true

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
                   --max-time 60 --compressed)
  [[ -n "$data" ]] && curl_args+=(-H "Content-Type: application/json" -d "$data")
  for h in "${extra_headers[@]}"; do curl_args+=("$h"); done
  curl_args+=("$url")

  local status
  status=$(curl "${curl_args[@]}" 2>/dev/null)
  local curl_rc=$?
  if [[ $curl_rc -ne 0 || ! "$status" =~ ^[0-9]{3}$ ]]; then
    status="000"
    LAST_BODY=""
  else
    LAST_BODY=$(cat /tmp/azure_sns_test_body 2>/dev/null || echo "")
  fi
  LAST_STATUS="$status"

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
echo -e "  API Function: ${CYAN}$API_URL${NC}"
echo -e "  Auth token  : $([ -n "$TOKEN" ] && echo "${CYAN}provided${NC}" || echo "${YELLOW}not provided (auth tests will be skipped)${NC}")"
echo ""

# ════════════════════════════════════════════════════════════
sep
echo -e "${BOLD}Section 1 — Front Door CDN + React SPA (static)${NC}"
sep

run_test "AFD GET /sns/ returns 200" \
  GET "$FD_URL/sns/"

# Verify Content-Type is text/html
SNS_CT=$(curl -s --max-time 25 -D - "$FD_URL/sns/" -o /dev/null 2>/dev/null \
  | grep -i '^content-type:' | head -1 | tr -d '\r\n' || echo "")
if echo "$SNS_CT" | grep -qi 'text/html'; then
  ok "  SNS page Content-Type is text/html  [$SNS_CT]"
else
  fail "  SNS page unexpected Content-Type: $SNS_CT"
fi

# Verify the page contains the React SPA root element
SNS_BODY=$(curl -s --max-time 25 --compressed "$FD_URL/sns/" 2>/dev/null || echo "")
if echo "$SNS_BODY" | grep -q '<div id="root"'; then
  ok "  React SPA root element (<div id=\"root\">) found"
else
  fail "  React SPA root element not found in /sns/ page"
fi

# Verify the SPA does not contain Python/Jinja2 SSR artifacts
if echo "$SNS_BODY" | grep -qi 'jinja\|fastapi\|uvicorn'; then
  fail "  /sns/ page still contains SSR artifacts (Jinja/FastAPI)"
else
  ok "  No SSR artifacts in React SPA page"
fi

# React SPA routing: deep links should also return 200 + HTML (SPA index)
run_test "AFD GET / returns 200 (landing page)" \
  GET "$FD_URL/"

# ════════════════════════════════════════════════════════════
sep
echo -e "${BOLD}Section 2 — API Function App (direct)${NC}"
sep

run_test "API /health returns 200" \
  GET "$API_URL/api/health"

if echo "$LAST_BODY" | jq -e '.status == "ok"' >/dev/null 2>&1; then
  ok "  .provider=$(echo "$LAST_BODY" | jq -r '.provider // "unknown"')"
else
  fail "  Unexpected /health response"
fi

run_test "API GET /posts returns 200 (unauthenticated)" \
  GET "$API_URL/posts"

if echo "$LAST_BODY" | jq -e '.items' >/dev/null 2>&1; then
  POST_COUNT=$(echo "$LAST_BODY" | jq '.items | length')
  ok "  .items array present (${POST_COUNT} posts)"
elif echo "$LAST_BODY" | jq -e '.posts' >/dev/null 2>&1; then
  POST_COUNT=$(echo "$LAST_BODY" | jq '.posts | length')
  ok "  .posts array present (${POST_COUNT} posts)"
else
  fail "  .items/.posts missing in /posts response"
fi

# imageUrls に直接Blob URL (SASなし) が含まれていないことを確認
DIRECT_BLOB_URLS=$(echo "$LAST_BODY" | jq -r '[.items // .posts // [] | .[] | .imageUrls // [] | .[] | select(startswith("https://") and (contains("blob.core.windows.net")) and (contains("?sv=") | not) and (contains("?se=") | not) and (contains("sig=") | not))] | length' 2>/dev/null || echo "0")
if [[ "$DIRECT_BLOB_URLS" == "0" ]]; then
  ok "  No direct Blob URLs (all image URLs have SAS token or no images) ✓"
else
  fail "  $DIRECT_BLOB_URLS direct Blob URL(s) without SAS found — 409 will occur on display!"
fi

# ════════════════════════════════════════════════════════════
sep
echo -e "${BOLD}Section 3 — Front Door CDN: SPA deep-link (URL Rewrite Rule Set)${NC}"
sep
echo -e "  ${CYAN}AFD ルーティング:"
echo -e "    /*       → Blob Storage (Rule Set: /sns/<deep-link> → /sns/index.html)"
echo -e "    /api/*   → 設定なし (API は Function App 直接アクセス)${NC}"
echo ""

# SPA deep-link: AFD Rule Set が /sns/login → /sns/index.html に書き換える
run_test "AFD GET /sns/login returns 200 (SPA URL Rewrite)" \
  GET "$FD_URL/sns/login"

SPA_LOGIN_BODY=$(curl -s --max-time 15 --compressed "$FD_URL/sns/login" 2>/dev/null || echo "")
if echo "$SPA_LOGIN_BODY" | grep -q '<div id="root"'; then
  ok "  /sns/login serves React SPA (<div id=\"root\"> found) ✓"
else
  fail "  /sns/login did not return React SPA HTML"
  [[ -n "$SPA_LOGIN_BODY" ]] && echo "  Response (first 200ch): ${SPA_LOGIN_BODY:0:200}"
fi

run_test "AFD GET /sns/profile returns 200 (SPA URL Rewrite)" \
  GET "$FD_URL/sns/profile"

run_test "AFD GET /sns/feed returns 200 (SPA URL Rewrite)" \
  GET "$FD_URL/sns/feed"

# 静的アセットは書き換えされず直接配信される（Rule Set exclude /sns/assets/）
ASSET_STATUS=$(curl -s --max-time 15 -o /dev/null -w "%{http_code}" \
  "$FD_URL/sns/assets/" 2>/dev/null || echo "000")
if [[ "$ASSET_STATUS" != "404" || "$ASSET_STATUS" == "200" || "$ASSET_STATUS" == "403" ]]; then
  ok "  /sns/assets/ is NOT rewritten (assets exclude rule active: HTTP $ASSET_STATUS) ✓"
else
  warn "  /sns/assets/ returned HTTP $ASSET_STATUS"
fi

# /api/* は AFD ルートなし → Blob Storage 404 が返る (設計通り)
AFD_API_STATUS=$(curl -s --max-time 15 -o /dev/null -w "%{http_code}" "$FD_URL/api/health" 2>/dev/null || echo "000")
if [[ "$AFD_API_STATUS" != "200" ]]; then
  ok "  AFD /api/health → HTTP $AFD_API_STATUS (AFD に /api/* ルートなし — 設計通り) ✓"
else
  warn "  AFD /api/health returned 200 — 予期しない /api/* ルートが有効の可能性あり"
fi

# ════════════════════════════════════════════════════════════
sep
echo -e "${BOLD}Section 4 — Auth guard (unauthenticated = 401)${NC}"
sep

run_test "POST /posts without token returns 401" \
  POST "$API_URL/posts" \
  --data '{"content":"azure auth guard test"}' \
  --expect 401

run_test "POST /uploads/presigned-urls without token returns 401" \
  POST "$API_URL/uploads/presigned-urls" \
  --data '{"count":1,"contentTypes":["image/jpeg"]}' \
  --expect 401

# ════════════════════════════════════════════════════════════
sep
echo -e "${BOLD}Section 5 — Authenticated endpoints${NC}"
sep

if [[ $READ_ONLY == true ]]; then
  warn "Read-only mode: skipping Sections 5-6 (write tests)."
  warn "Re-run with --write to enable: $0 --env production --write --token <token>"
  skip "Section 5 - Authenticated endpoints"
  skip "Section 6 - Cleanup"
elif [[ -z "$TOKEN" ]]; then
  warn "No --token provided; skipping Sections 5, 6."
  warn "Re-run with: $0 --token <azure-ad-access-token>"
  SKIP=$((SKIP + 7))
else
  AUTHH="Authorization: Bearer $TOKEN"

  # 5-1. Get profile
  run_test "GET /profile returns 200" \
    GET "$API_URL/profile" --header "$AUTHH"

  # 5-2. Create post (text only)
  run_test "POST /posts creates a new post" \
    POST "$API_URL/posts" \
    --header "$AUTHH" \
    --data "{\"content\":\"Azure E2E test post $(date +%s)\"}" \
    --expect 201

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
    run_test "GET /posts/$POST_ID returns 200" \
      GET "$API_URL/posts/$POST_ID" --header "$AUTHH"
  fi

  # 5-4. Generate presigned URL for image upload
  run_test "POST /uploads/presigned-urls returns 200" \
    POST "$API_URL/uploads/presigned-urls" \
    --header "$AUTHH" \
    --data '{"count":1,"contentTypes":["image/jpeg"]}'

  UPLOAD_URL_RAW=$(echo "$LAST_BODY" | jq -r '.urls[0].url // .[0].url // .[0].uploadUrl // ""' 2>/dev/null || echo "")
  UPLOAD_KEY_RAW=$(echo "$LAST_BODY" | jq -r '.urls[0].key // .urls[0].imageKey // ""' 2>/dev/null || echo "")
  if [[ -n "$UPLOAD_URL_RAW" && "$UPLOAD_URL_RAW" != "null" ]]; then
    ok "  Presigned upload URL generated (Blob Storage SAS)"
    if echo "$UPLOAD_URL_RAW" | grep -qE 'sig=|sv='; then
      ok "    Upload URL contains SAS token ✓"
    else
      warn "    Upload URL may lack SAS token: ${UPLOAD_URL_RAW:0:80}"
    fi
  else
    fail "  Presigned URL missing in response"
  fi

  # 5-4a. ★ Binary PUT: 実際にテスト画像を Azure Blob へアップロード
  UPLOAD_REAL_POST_ID=""
  if [[ -n "$UPLOAD_URL_RAW" && "$UPLOAD_URL_RAW" != "null" && -s /tmp/test_upload_azure.png ]]; then
    PUT_AZ_STATUS=$(curl -s -o /tmp/put_resp_azure.txt -w "%{http_code}" \
      -X PUT \
      -H "x-ms-blob-type: BlockBlob" \
      -H "Content-Type: image/jpeg" \
      --data-binary @/tmp/test_upload_azure.png \
      --max-time 20 \
      "$UPLOAD_URL_RAW" 2>/dev/null || echo "000")
    if [[ "$PUT_AZ_STATUS" == "201" || "$PUT_AZ_STATUS" == "200" ]]; then
      ok "  PUT test image → Azure Blob SAS URL: HTTP $PUT_AZ_STATUS ✓"
    else
      fail "  PUT test image → Azure Blob: HTTP $PUT_AZ_STATUS (expected 201)"
      [[ -s /tmp/put_resp_azure.txt ]] && echo "  Response: $(head -c 200 /tmp/put_resp_azure.txt)"
    fi

    # 4b. アップロードしたキーで投稿を作成し imageUrls がアクセス可能か検証
    if [[ -n "$UPLOAD_KEY_RAW" && "$UPLOAD_KEY_RAW" != "null" && ("$PUT_AZ_STATUS" == "201" || "$PUT_AZ_STATUS" == "200") ]]; then
      IMG_POST_REAL_DATA=$(python3 -c "import json; print(json.dumps({'content':'[test] Azure E2E real image upload', 'imageKeys':['$UPLOAD_KEY_RAW']}))")
      run_test "POST /posts with real uploaded imageKey returns 201" \
        POST "$API_URL/posts" \
        --header "$AUTHH" \
        --data "$IMG_POST_REAL_DATA" \
        --expect 201
      UPLOAD_REAL_POST_ID=$(echo "$LAST_BODY" | jq -r '.id // .postId // ""' 2>/dev/null)
      [[ -n "$UPLOAD_REAL_POST_ID" && "$UPLOAD_REAL_POST_ID" != "null" ]] && CREATED_POST_IDS+=("$UPLOAD_REAL_POST_ID")

      # GET /posts/:id → imageUrls が HTTP 200 で取得できるか確認 (SASあり read URL)
      if [[ -n "$UPLOAD_REAL_POST_ID" && "$UPLOAD_REAL_POST_ID" != "null" ]]; then
        run_test "GET /posts/$UPLOAD_REAL_POST_ID returns 200" \
          GET "$API_URL/posts/$UPLOAD_REAL_POST_ID" --header "$AUTHH"
        REAL_BLOB_URL=$(echo "$LAST_BODY" | jq -r '.imageUrls[0] // ""' 2>/dev/null)
        if [[ -n "$REAL_BLOB_URL" && "$REAL_BLOB_URL" != "null" ]]; then
          BLOB_HTTP=$(curl -s -o /dev/null -w "%{http_code}" --max-time 15 "$REAL_BLOB_URL" 2>/dev/null || echo "000")
          if [[ "$BLOB_HTTP" == "200" ]]; then
            ok "  GET imageUrl (Blob SAS read URL) → HTTP 200 ✓ (image displayable)"
          else
            fail "  GET imageUrl → HTTP $BLOB_HTTP (image not displayable!) URL: ${REAL_BLOB_URL:0:100}"
          fi
        else
          warn "  No imageUrls in response — skipping accessibility check"
        fi
      fi
    else
      warn "  key not in response or PUT failed — skipping real-upload post test"
    fi
  else
    warn "  No presigned URL or test PNG missing — skipping binary PUT test"
  fi

  # 5-5. Create post with imageKeys (React SPA format)
  KEYS_2=$(python3 -c "
import json, uuid
keys = [f'testuser/{uuid.uuid4()}.jpg', f'testuser/{uuid.uuid4()}.jpg']
print(json.dumps({'content': '[test] Azure E2E post with imageKeys', 'imageKeys': keys}))
")
  run_test "POST /posts with imageKeys returns 201" \
    POST "$API_URL/posts" \
    --header "$AUTHH" \
    --data "$KEYS_2" \
    --expect 201

  if echo "$LAST_BODY" | jq -e '.id // .postId' >/dev/null 2>&1; then
    IMG_POST_ID=$(echo "$LAST_BODY" | jq -r '.id // .postId // ""')
    [[ -n "$IMG_POST_ID" && "$IMG_POST_ID" != "null" ]] && CREATED_POST_IDS+=("$IMG_POST_ID")
    ok "  Post with imageKeys created: id=$IMG_POST_ID"

    # ── 5-5a. 作成レスポンスの imageUrls に SAS トークンが含まれているか検証 ──
    IMG_URLS=$(echo "$LAST_BODY" | jq -r '.imageUrls // [] | .[]' 2>/dev/null || echo "")
    IMG_URL_COUNT=$(echo "$LAST_BODY" | jq -r '.imageUrls // [] | length' 2>/dev/null || echo "0")
    if [[ "$IMG_URL_COUNT" -gt 0 ]]; then
      DIRECT=$(echo "$LAST_BODY" | jq -r '[.imageUrls // [] | .[] | select(startswith("https://") and (contains("blob.core.windows.net")) and (contains("?sv=") | not) and (contains("?se=") | not) and (contains("sig=") | not))] | length' 2>/dev/null || echo "0")
      SAS_COUNT=$(echo "$LAST_BODY" | jq -r '[.imageUrls // [] | .[] | select(contains("sig=") or contains("sv="))] | length' 2>/dev/null || echo "0")
      if [[ "$DIRECT" == "0" && "$SAS_COUNT" -gt 0 ]]; then
        ok "    create_post response: $SAS_COUNT/$IMG_URL_COUNT image URL(s) have SAS token ✓ (no direct Blob URLs)"
      elif [[ "$DIRECT" -gt 0 ]]; then
        fail "    create_post response: $DIRECT direct Blob URL(s) without SAS — 409 on display!"
        echo "$IMG_URLS" | head -3 | while read u; do echo "      URL: ${u:0:100}"; done
      else
        warn "    create_post response: $IMG_URL_COUNT URL(s) but SAS pattern not detected"
      fi
    else
      ok "    create_post response: no imageUrls (expected — imageKeys stored, not validated against Blob)"
    fi

    # ── 5-5b. GET /posts/:id でも SAS URL が返るか確認 ──
    if [[ -n "$IMG_POST_ID" && "$IMG_POST_ID" != "null" ]]; then
      run_test "GET /posts/$IMG_POST_ID (with imageKeys) returns 200" \
        GET "$API_URL/posts/$IMG_POST_ID" --header "$AUTHH"
      GET_IMG_URLS=$(echo "$LAST_BODY" | jq -r '.imageUrls // [] | length' 2>/dev/null || echo "0")
      if [[ "$GET_IMG_URLS" -gt 0 ]]; then
        DIRECT_GET=$(echo "$LAST_BODY" | jq -r '[.imageUrls // [] | .[] | select(startswith("https://") and (contains("blob.core.windows.net")) and (contains("?sv=") | not) and (contains("?se=") | not) and (contains("sig=") | not))] | length' 2>/dev/null || echo "0")
        SAS_GET=$(echo "$LAST_BODY" | jq -r '[.imageUrls // [] | .[] | select(contains("sig=") or contains("sv="))] | length' 2>/dev/null || echo "0")
        if [[ "$DIRECT_GET" == "0" && "$SAS_GET" -gt 0 ]]; then
          ok "    GET response: $SAS_GET/$GET_IMG_URLS image URL(s) have SAS token ✓"
        elif [[ "$DIRECT_GET" -gt 0 ]]; then
          fail "    GET response: $DIRECT_GET direct Blob URL(s) without SAS — 409 on display!"
        else
          warn "    GET response: $GET_IMG_URLS URL(s) but SAS pattern not detected"
        fi
      else
        ok "    GET response: imageUrls empty (dummy imageKeys stored but not validated against Blob)"
      fi
    fi
  fi

  # 5-6. List posts — should include ours
  run_test "GET /posts returns list with test posts" \
    GET "$API_URL/posts?limit=20" --header "$AUTHH"

  # imageUrls の SAS 検証 (一覧レスポンス)
  DIRECT_LIST=$(echo "$LAST_BODY" | jq -r '[.items // .posts // [] | .[] | .imageUrls // [] | .[] | select(startswith("https://") and (contains("blob.core.windows.net")) and (contains("?sv=") | not) and (contains("?se=") | not) and (contains("sig=") | not))] | length' 2>/dev/null || echo "0")
  if [[ "$DIRECT_LIST" == "0" ]]; then
    ok "  /posts list: no direct Blob URL without SAS ✓"
  else
    fail "  /posts list: $DIRECT_LIST direct Blob URL(s) without SAS found!"
  fi

  # ══════════════════════════════════════════════════════
  sep
  echo -e "${BOLD}Section 6 — Cleanup (delete test posts)${NC}"
  sep

  if [[ "$SKIP_CLEANUP" == "false" && ${#CREATED_POST_IDS[@]} -gt 0 ]]; then
    for pid in "${CREATED_POST_IDS[@]}"; do
      run_test "DELETE /posts/$pid returns 200" \
        DELETE "$API_URL/posts/$pid" \
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
