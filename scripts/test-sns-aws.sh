#!/usr/bin/env bash
# ============================================================
# test-sns-aws.sh — End-to-End test suite for AWS simple-sns
# ============================================================
#
# Tests the full simple-sns stack on AWS staging:
#   - CloudFront CDN + React SPA (static files, /sns/)
#   - API Lambda (FastAPI) via API Gateway
#   - Cognito-protected endpoints
#   - Image upload (presigned URL generation)
#   - Post CRUD with images
#
# Usage:
#   # Public-only tests (no auth token required):
#   ./scripts/test-sns-aws.sh
#
#   # Full authenticated tests:
#   ./scripts/test-sns-aws.sh --token <cognito-access-token>
#
#   # Override default CloudFront / API URLs:
#   ./scripts/test-sns-aws.sh \
#     --cf   https://d1tf3uumcm4bo1.cloudfront.net \
#     --api  https://z42qmqdqac.execute-api.ap-northeast-1.amazonaws.com \
#     --token <token> --verbose
#
# How to get a Cognito access token for testing:
#   1. Open https://d1tf3uumcm4bo1.cloudfront.net/sns/ in a browser
#   2. Log in with your Cognito account
#   3. Open DevTools → Application → Local Storage → select the page origin
#   4. Copy the value of the `access_token` key
#   5. Pass it as --token <value>
#
# Alternatively, using the Cognito CLI flow:
#   aws cognito-idp initiate-auth \
#     --auth-flow USER_PASSWORD_AUTH \
#     --client-id 1k41lqkds4oah55ns8iod30dv2 \
#     --auth-parameters USERNAME=<email>,PASSWORD=<pw> \
#     --region ap-northeast-1 \
#     --query 'AuthenticationResult.AccessToken' --output text
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
_CF_URL_EXPLICIT=false
_API_URL_EXPLICIT=false
TOKEN=""
VERBOSE=false
SKIP_CLEANUP=false
# Auto token acquisition
USERNAME=""
PASSWORD=""
COGNITO_CLIENT_ID=""
COGNITO_REGION="ap-northeast-1"
# staging default (production client ID should be passed via --client-id)
_STAGING_COGNITO_CLIENT_ID="1k41lqkds4oah55ns8iod30dv2"

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
  -c, --cf    <url>        CloudFront base URL  (overrides --env default)
  -a, --api   <url>        API Gateway base URL (overrides --env default)
  -e, --env   <env>        Target environment: staging|production  (default: staging)
                           production URLs: www.aws.ashnova.jp + prod API Gateway
                           --env production implies --read-only
  -r, --read-only          Skip all write tests (Sections 4-7); safe for production
      --write              Allow write tests even when --env production is set
  -t, --token <token>      Cognito access token (required for auth tests)
  -u, --username <email>   Cognito username for auto token acquisition
  -p, --password <pw>      Cognito password for auto token acquisition
      --client-id <id>     Cognito App Client ID (default: staging client)
      --cognito-region <r> AWS region for Cognito (default: ap-northeast-1)
  -v, --verbose            Print full response bodies
  -s, --skip-cleanup       Do not delete posts created during the test run
  -h, --help               Show this help

Examples:
  # Staging (default):
  $0 --token eyJraWQ...
  # Staging with auto token acquisition:
  $0 --username user@example.com --password 'P@ss123'
  # Production - read-only smoke test (no writes):
  $0 --env production
  # Production - full authenticated test (write tests enabled):
  $0 --env production --write --username user@example.com --password 'P@ss123' --client-id <prod-client-id>
  # Custom URL override:
  $0 --cf https://my-cf.cloudfront.net --api https://my-api.execute-api.amazonaws.com --token eyJ...
EOF
}

# ── arg parsing ─────────────────────────────────────────────
while [[ $# -gt 0 ]]; do
  case $1 in
    -c|--cf)    CF_URL="$2";  _CF_URL_EXPLICIT=true;  shift 2 ;;
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
    -t|--token)        TOKEN="$2";        shift 2 ;;
    -u|--username)     USERNAME="$2";     shift 2 ;;
    -p|--password)     PASSWORD="$2";     shift 2 ;;
    --client-id)       COGNITO_CLIENT_ID="$2"; shift 2 ;;
    --cognito-region)  COGNITO_REGION="$2"; shift 2 ;;
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
  [[ $_CF_URL_EXPLICIT  == false ]] && CF_URL="${CF_URL:-https://www.aws.ashnova.jp}"
  [[ $_API_URL_EXPLICIT == false ]] && API_URL="${API_URL:-https://qkzypr32af.execute-api.ap-northeast-1.amazonaws.com}"
else
  CF_URL="${CF_URL:-https://d1tf3uumcm4bo1.cloudfront.net}"
  API_URL="${API_URL:-https://z42qmqdqac.execute-api.ap-northeast-1.amazonaws.com}"
fi
[[ $READ_ONLY == true ]] && SKIP_CLEANUP=true

CF_URL="${CF_URL%/}"
API_URL="${API_URL%/}"

# ── dependency check ────────────────────────────────────────
command -v curl    >/dev/null 2>&1 || die "curl is required but not installed"
command -v jq      >/dev/null 2>&1 || die "jq is required but not installed"
command -v python3 >/dev/null 2>&1 || die "python3 is required but not installed"

# ── auto token acquisition (Cognito) ────────────────────────
if [[ -z "$TOKEN" && -n "$USERNAME" && -n "$PASSWORD" ]]; then
  [[ -z "$COGNITO_CLIENT_ID" ]] && \
    COGNITO_CLIENT_ID="$( [[ $_ENV_ == production ]] && echo "" || echo "$_STAGING_COGNITO_CLIENT_ID" )"
  if [[ -z "$COGNITO_CLIENT_ID" ]]; then
    die "--client-id is required for automatic token acquisition in production"
  fi
  log "Auto-acquiring Cognito token for $USERNAME ..."
  TOKEN=$(aws cognito-idp initiate-auth \
    --auth-flow USER_PASSWORD_AUTH \
    --client-id "$COGNITO_CLIENT_ID" \
    --auth-parameters "USERNAME=$USERNAME,PASSWORD=$PASSWORD" \
    --region "$COGNITO_REGION" \
    --query 'AuthenticationResult.AccessToken' \
    --output text 2>/dev/null || echo "")
  if [[ -n "$TOKEN" && "$TOKEN" != "None" ]]; then
    log "  ✓ Cognito token acquired (${TOKEN:0:20}...)"
  else
    warn "  Failed to acquire Cognito token — check --username/--password/--client-id"
    TOKEN=""
  fi
fi

# ── shared test image (1x1 transparent PNG, 68 bytes) ───────
python3 -c "
import base64, sys
sys.stdout.buffer.write(base64.b64decode(
  'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=='
))
" > /tmp/test_upload_aws.png 2>/dev/null || true

# ── test runner ─────────────────────────────────────────────
# run_test <label> <method> <url> [--header "K: V"] ... [--data '{...}'] [--expect <code>]
# Returns the response body. Sets LAST_STATUS and LAST_BODY globals.
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

  local curl_args=(-s -o /tmp/sns_test_body -w "%{http_code}" -X "$method"
                   --max-time 20 --compressed)
  # Do not force Accept: application/json globally — let the server decide
  [[ -n "$data" ]] && curl_args+=(-H "Content-Type: application/json" -d "$data")
  for h in "${extra_headers[@]}"; do curl_args+=("$h"); done
  curl_args+=("$url")

  local status
  status=$(curl "${curl_args[@]}" 2>/dev/null || echo "000")
  LAST_STATUS="$status"
  LAST_BODY=$(cat /tmp/sns_test_body 2>/dev/null || echo "")

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

auth_header() {
  [[ -n "$TOKEN" ]] && echo "Authorization: Bearer $TOKEN" || echo ""
}

# ── banner ───────────────────────────────────────────────────
echo ""
echo -e "${BOLD}============================================================${NC}"
echo -e "${BOLD}  AWS Simple-SNS — End-to-End Test Suite${NC}"
echo -e "${BOLD}============================================================${NC}"
echo -e "  CloudFront : ${CYAN}$CF_URL${NC}"
echo -e "  API Gateway: ${CYAN}$API_URL${NC}"
echo -e "  Auth token : $([ -n "$TOKEN" ] && echo "${CYAN}provided${NC}" || echo "${YELLOW}not provided (auth tests will be skipped)${NC}")"
echo ""

# ════════════════════════════════════════════════════════════
sep
echo -e "${BOLD}Section 1 — CloudFront / Frontend (public)${NC}"
sep

run_test "Landing page (/) returns 200" \
  GET "$CF_URL/"

run_test "SNS app (/sns/) returns 200" \
  GET "$CF_URL/sns/"

# Check Content-Type header via GET (HEAD request returns application/json from API GW)
SNS_CT=$(curl -s --max-time 15 -D - "$CF_URL/sns/" -o /dev/null 2>/dev/null \
         | grep -i '^content-type:' | head -1 | tr -d '\r\n')
if echo "$SNS_CT" | grep -qi 'text/html'; then
  ok "  SNS page Content-Type is text/html  [$SNS_CT]"
  PASS=$((PASS + 1))
else
  fail "  SNS page unexpected Content-Type: $SNS_CT"
  FAIL=$((FAIL + 1))
fi

# ════════════════════════════════════════════════════════════
sep
echo -e "${BOLD}Section 2 — API Health (public)${NC}"
sep

run_test "GET /health returns 200" \
  GET "$API_URL/health"

# Verify JSON structure
if echo "$LAST_BODY" | jq -e '.status == "ok"' >/dev/null 2>&1; then
  ok "  .status == \"ok\""
  PASS=$((PASS + 1))
else
  fail "  .status != \"ok\" in health response"
  FAIL=$((FAIL + 1))
fi

run_test "GET /posts returns 200 (unauthenticated)" \
  GET "$API_URL/posts"

# ════════════════════════════════════════════════════════════
sep
echo -e "${BOLD}Section 3 — Auth guard (unauthenticated should return 401)${NC}"
sep

run_test "POST /posts without token returns 401" \
  POST "$API_URL/posts" \
  --data '{"content":"auth guard test"}' \
  --expect 401

run_test "POST /uploads/presigned-urls without token returns 401" \
  POST "$API_URL/uploads/presigned-urls" \
  --data '{"count":1,"contentTypes":["image/jpeg"]}' \
  --expect 401

# ════════════════════════════════════════════════════════════
sep
echo -e "${BOLD}Section 4 — Authenticated endpoints${NC}"
sep

if [[ $READ_ONLY == true ]]; then
  warn "Read-only mode: skipping Sections 4-7 (write tests)."
  warn "Re-run with --write to enable: $0 --env production --write --token <token>"
  skip "Section 4 - Authenticated endpoints"
  skip "Section 5 - Image upload / presigned URLs"
  skip "Section 6 - Post with imageKeys validation"
  skip "Section 7 - Cleanup"
elif [[ -z "$TOKEN" ]]; then
  warn "No --token provided; skipping Sections 4, 5, 6."
  warn "Re-run with: $0 --token <cognito-access-token>"
  SKIP=$((SKIP + 6))
else
  AUTHH="Authorization: Bearer $TOKEN"

  # 4-1. Get profile
  run_test "GET /profile returns 200" \
    GET "$API_URL/profile" --header "$AUTHH"

  # 4-2. Create post (text only)
  run_test "POST /posts (text) returns 201" \
    POST "$API_URL/posts" \
    --header "$AUTHH" \
    --data '{"content":"[test] simple-sns E2E test post 🧪","isMarkdown":false}' \
    --expect 201
  TEXT_POST_ID=$(echo "$LAST_BODY" | jq -r '.postId // .post_id // ""' 2>/dev/null)
  if [[ -n "$TEXT_POST_ID" && "$TEXT_POST_ID" != "null" ]]; then
    ok "  Created text post: $TEXT_POST_ID"
    CREATED_POST_IDS+=("$TEXT_POST_ID")
  else
    warn "  Could not extract postId from response — cleanup may be incomplete"
  fi

  # 4-3. Get the created post
  if [[ -n "$TEXT_POST_ID" && "$TEXT_POST_ID" != "null" ]]; then
    run_test "GET /posts/:id returns 200" \
      GET "$API_URL/posts/$TEXT_POST_ID" --header "$AUTHH"
  else
    skip "GET /posts/:id — post creation failed, skipping"
    SKIP=$((SKIP + 1))
  fi

  # 4-4. Update the post
  if [[ -n "$TEXT_POST_ID" && "$TEXT_POST_ID" != "null" ]]; then
    run_test "PUT /posts/:id returns 200" \
      PUT "$API_URL/posts/$TEXT_POST_ID" \
      --header "$AUTHH" \
      --data '{"content":"[test] updated by E2E test ✅"}' \
      --expect 200
  else
    skip "PUT /posts/:id — post creation failed, skipping"
    SKIP=$((SKIP + 1))
  fi

  # ════════════════════════════════════════════════════════
  sep
  echo -e "${BOLD}Section 5 — Image upload (presigned URL)${NC}"
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
    PASS=$((PASS + 1))
  else
    fail "  Expected 2 presigned URLs, got $URL_COUNT"
    FAIL=$((FAIL + 1))
  fi

  # 5-2. Validate presigned URL format + AWS SigV4 signature
  FIRST_UPLOAD_URL=$(echo "$LAST_BODY" | jq -r '.urls[0].url // ""' 2>/dev/null)
  FIRST_UPLOAD_KEY=$(echo "$LAST_BODY" | jq -r '.urls[0].key // .urls[0].imageKey // ""' 2>/dev/null)
  if echo "$FIRST_UPLOAD_URL" | grep -qE '^https://.*s3'; then
    ok "  Presigned URL is a valid S3 HTTPS URL"
    PASS=$((PASS + 1))
  elif [[ -n "$FIRST_UPLOAD_URL" ]]; then
    warn "  Presigned URL format unexpected: ${FIRST_UPLOAD_URL:0:80}..."
  fi
  if echo "$FIRST_UPLOAD_URL" | grep -qiE 'X-Amz-Signature='; then
    ok "  Presigned URL contains X-Amz-Signature ✓"
  elif [[ -n "$FIRST_UPLOAD_URL" ]]; then
    fail "  X-Amz-Signature missing from presigned URL"
  fi

  # 5-3. ★ Binary PUT: 実際にテスト画像を S3 へアップロード
  UPLOAD_POST_ID=""
  if [[ -n "$FIRST_UPLOAD_URL" && -s /tmp/test_upload_aws.png ]]; then
    PUT_STATUS=$(curl -s -o /tmp/put_resp_aws.txt -w "%{http_code}" \
      -X PUT \
      -H "Content-Type: image/jpeg" \
      --data-binary @/tmp/test_upload_aws.png \
      --max-time 20 \
      "$FIRST_UPLOAD_URL" 2>/dev/null || echo "000")
    if [[ "$PUT_STATUS" == "200" ]]; then
      ok "  PUT test image → S3 presigned URL: HTTP 200 ✓"
    else
      fail "  PUT test image → S3: HTTP $PUT_STATUS (expected 200)"
      [[ -s /tmp/put_resp_aws.txt ]] && echo "  Response: $(head -c 200 /tmp/put_resp_aws.txt)"
    fi

    # 5-4. ★ アップロードしたキーで投稿を作成し imageUrls が取得可能か検証
    if [[ -n "$FIRST_UPLOAD_KEY" && "$FIRST_UPLOAD_KEY" != "null" && "$PUT_STATUS" == "200" ]]; then
      IMG_POST_DATA=$(python3 -c "import json; print(json.dumps({'content':'[test] AWS E2E real image upload', 'imageKeys':['$FIRST_UPLOAD_KEY']}))")
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
            ok "  GET imageUrl (presigned GET) → HTTP 200 ✓ (image displayable)"
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

  # 6-1. Create post with up to 16 imageKeys (upper limit)
  KEYS_16=$(python3 -c "
import json, uuid
keys = [f'testuser/{uuid.uuid4()}.jpg' for _ in range(16)]
print(json.dumps({'content': '[test] post with 16 imageKeys', 'imageKeys': keys}))
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
sep
echo -e "${BOLD}Section 8 — React SPA build-time env-var sanity check${NC}"
sep

# Verify that the React SPA does NOT embed "localhost" in its HTML
# (checks that VITE_API_URL was set correctly at build time)
SNS_BODY=$(curl -s --max-time 15 --compressed "$CF_URL/sns/" 2>/dev/null || echo "")
if echo "$SNS_BODY" | grep -q "localhost"; then
  fail "GET /sns/ env-var sanity: page exposes 'localhost' — env vars may be wrong"
  FAIL=$((FAIL + 1))
else
  ok "GET /sns/ env-var sanity: page does not expose 'localhost'"
  PASS=$((PASS + 1))
fi

# Warn if page seems to require login (public feed should NOT require login)
if echo "$SNS_BODY" | grep -qi 'sign.in' && ! echo "$SNS_BODY" | grep -qi 'profile'; then
  warn "  /sns/ page may be prompting login (AUTH_DISABLED or env var issue?)"
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
  echo "  See docs/AWS_SNS_FIX_REPORT.md for troubleshooting."
  exit 1
fi
