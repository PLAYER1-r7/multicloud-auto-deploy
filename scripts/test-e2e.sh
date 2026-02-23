#!/usr/bin/env bash
# ================================================================
# test-e2e.sh — Multi-Cloud End-to-End Test Suite (v2)
# ================================================================
#
# Runs a lightweight E2E health + CRUD smoke test against all
# three cloud staging environments and prints a consolidated
# pass/fail table.
#
# Public endpoints are tested without a token.
# Authenticated endpoints (POST/PUT/DELETE) require tokens.
#
# Usage:
#   # Public endpoints only:
#   ./scripts/test-e2e.sh
#
#   # Full authenticated run:
#   ./scripts/test-e2e.sh \
#     --aws-token   <cognito-access-token> \
#     --azure-token <azure-ad-id-token> \
#     --gcp-token   <firebase-id-token>
#
#   # URL overrides:
#   AWS_API_URL=https://... ./scripts/test-e2e.sh
#
# How to get tokens:
#   AWS (Cognito):
#     aws cognito-idp initiate-auth \
#       --auth-flow USER_PASSWORD_AUTH \
#       --client-id 1k41lqkds4oah55ns8iod30dv2 \
#       --auth-parameters USERNAME=user@example.com,PASSWORD=pw \
#       --region ap-northeast-1 \
#       --query 'AuthenticationResult.AccessToken' --output text
#   GCP (Firebase):
#     gcloud auth print-identity-token
#   Azure (Azure AD):
#     Copy id_token from browser DevTools Application > Local Storage
#
# Exit codes:
#   0 — All tests passed
#   1 — One or more tests failed
#   2 — Missing required dependency
# ================================================================

set -euo pipefail

RED='\033[0;31m'; GREEN='\033[0;32m'
YELLOW='\033[1;33m'; BLUE='\033[0;34m'; CYAN='\033[0;36m'
BOLD='\033[1m'; NC='\033[0m'

AWS_API_URL="${AWS_API_URL:-}"
AZURE_API_URL="${AZURE_API_URL:-}"
GCP_API_URL="${GCP_API_URL:-}"
AWS_TOKEN=""
AZURE_TOKEN=""
GCP_TOKEN=""
VERBOSE=false
_ENV_=staging
_READ_ONLY_=false
_WRITE_=false
READ_ONLY=false

command -v curl >/dev/null 2>&1 || { echo -e "${RED}ERROR${NC}: curl required" >&2; exit 2; }
command -v jq   >/dev/null 2>&1 || { echo -e "${RED}ERROR${NC}: jq required"   >&2; exit 2; }

usage() {
  cat <<EOF
Usage: $0 [OPTIONS]
  -e, --env   <env>       Target environment: staging|production  (default: staging)
                          --env production uses custom domain URLs and implies --read-only
  -r, --read-only         Skip all write tests (POST/PUT/DELETE/presigned-urls)
      --write             Allow write tests even when --env production is set
  --aws-token   <token>   Cognito access token
  --azure-token <token>   Azure AD ID token
  --gcp-token   <token>   Firebase ID token
  -v, --verbose           Print response bodies on failure
  -h, --help              Show this help

Examples:
  # Staging (default):
  $0 --aws-token eyJ...
  # Production - read-only smoke test:
  $0 --env production
  # Production - full test with writes:
  $0 --env production --write --aws-token eyJ... --gcp-token \$(gcloud auth print-identity-token)
EOF
}

while [[ $# -gt 0 ]]; do
  case $1 in
    -e|--env)
      case "$2" in
        production|prod) _ENV_=production; _READ_ONLY_=true ;;
        staging|stag)    _ENV_=staging ;;
        *) echo -e "${RED}Unknown env: $2${NC}"; exit 1 ;;
      esac
      shift 2 ;;
    -r|--read-only) _READ_ONLY_=true; shift ;;
    --write)        _WRITE_=true;     shift ;;
    --aws-token)   AWS_TOKEN="$2";   shift 2 ;;
    --azure-token) AZURE_TOKEN="$2"; shift 2 ;;
    --gcp-token)   GCP_TOKEN="$2";   shift 2 ;;
    -v|--verbose)  VERBOSE=true;     shift   ;;
    -h|--help)     usage; exit 0 ;;
    *) echo -e "${RED}Unknown option: $1${NC}"; usage; exit 1 ;;
  esac
done

# Resolve read-only flag
READ_ONLY=$_READ_ONLY_
[[ $_WRITE_ == true ]] && READ_ONLY=false

# Resolve URLs based on environment
if [[ $_ENV_ == production ]]; then
  AWS_API_URL="${AWS_API_URL:-https://qkzypr32af.execute-api.ap-northeast-1.amazonaws.com}"
  AZURE_API_URL="${AZURE_API_URL:-https://multicloud-auto-deploy-production-func-cfdne7ecbngnh0d0.japaneast-01.azurewebsites.net/api}"
  GCP_API_URL="${GCP_API_URL:-https://multicloud-auto-deploy-production-api-son5b3ml7a-an.a.run.app}"
else
  AWS_API_URL="${AWS_API_URL:-https://z42qmqdqac.execute-api.ap-northeast-1.amazonaws.com}"
  AZURE_API_URL="${AZURE_API_URL:-https://multicloud-auto-deploy-staging-func-d8a2guhfere0etcq.japaneast-01.azurewebsites.net}"
  GCP_API_URL="${GCP_API_URL:-https://multicloud-auto-deploy-staging-api-son5b3ml7a-an.a.run.app}"
fi

declare -A RESULTS
PASS=0; FAIL=0; SKIP=0

rec_pass() { RESULTS["$1:$2"]="pass"; PASS=$((PASS + 1)); }
rec_fail() { RESULTS["$1:$2"]="fail"; FAIL=$((FAIL + 1)); }
rec_skip() { RESULTS["$1:$2"]="skip"; SKIP=$((SKIP + 1)); }

HTTP_STATUS=0
HTTP_BODY=""

http_req() {
  local method="$1" url="$2" token="${3:-}" data="${4:-}"
  local tmpfile
  tmpfile=$(mktemp /tmp/e2e_body_XXXXXX)
  local curl_args=(-s -o "$tmpfile" -w "%{http_code}" -X "$method" --max-time 25 --compressed)
  [[ -n "$token" ]] && curl_args+=(-H "Authorization: Bearer $token")
  [[ -n "$data"  ]] && curl_args+=(-H "Content-Type: application/json" -d "$data")
  curl_args+=("$url")
  HTTP_STATUS=$(curl "${curl_args[@]}" 2>/dev/null || echo "000")
  HTTP_BODY=$(cat "$tmpfile" 2>/dev/null || echo "")
  rm -f "$tmpfile"
}

test_cloud_suite() {
  local cloud="$1" api_base="$2" token="${3:-}"
  local cloud_up
  cloud_up=$(echo "$cloud" | tr '[:lower:]' '[:upper:]')

  echo ""
  echo -e "${BOLD}${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
  echo -e "${BOLD}  Cloud: ${CYAN}$cloud_up${NC}  │  ${api_base}${NC}"
  echo -e "${BOLD}${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

  local created_ids=()

  # 1. Health check
  echo -e "\n  ${BLUE}[1]${NC} Health check"
  http_req GET "$api_base/health"
  if [[ "$HTTP_STATUS" == "200" ]]; then
    local st provider
    st=$(echo "$HTTP_BODY"       | jq -r '.status   // ""'       2>/dev/null)
    provider=$(echo "$HTTP_BODY" | jq -r '.provider // "unknown"' 2>/dev/null)
    if [[ "$st" == "ok" ]]; then
      echo -e "  ${GREEN}[PASS]${NC}  GET /health → 200  (provider=$provider)"; rec_pass "$cloud" "GET /health"
    else
      echo -e "  ${RED}[FAIL]${NC}  GET /health → status='$st' (expected 'ok')"; rec_fail "$cloud" "GET /health"
    fi
  else
    echo -e "  ${RED}[FAIL]${NC}  GET /health → $HTTP_STATUS"; rec_fail "$cloud" "GET /health"
    [[ "$VERBOSE" == true ]] && echo "$HTTP_BODY" | head -c 300
  fi

  # 2. List posts (public)
  echo -e "\n  ${BLUE}[2]${NC} List posts (public)"
  http_req GET "$api_base/posts"
  if [[ "$HTTP_STATUS" == "200" ]] && echo "$HTTP_BODY" | jq -e '.items' >/dev/null 2>&1; then
    local count
    count=$(echo "$HTTP_BODY" | jq '.items | length' 2>/dev/null || echo "?")
    echo -e "  ${GREEN}[PASS]${NC}  GET /posts → 200  (items=$count)"; rec_pass "$cloud" "GET /posts"
  else
    echo -e "  ${RED}[FAIL]${NC}  GET /posts → $HTTP_STATUS or missing .items"; rec_fail "$cloud" "GET /posts"
    [[ "$VERBOSE" == true ]] && echo "$HTTP_BODY" | head -c 300
  fi

  # 3. Auth guard
  echo -e "\n  ${BLUE}[3]${NC} Auth guard (unauthenticated POST)"
  http_req POST "$api_base/posts" "" '{"content":"auth guard test"}'
  if [[ "$HTTP_STATUS" == "401" || "$HTTP_STATUS" == "403" ]]; then
    echo -e "  ${GREEN}[PASS]${NC}  POST /posts (no token) → $HTTP_STATUS"; rec_pass "$cloud" "auth guard"
  else
    echo -e "  ${RED}[FAIL]${NC}  POST /posts (no token) → $HTTP_STATUS (expected 401/403)"; rec_fail "$cloud" "auth guard"
  fi

  # 4-6. Authenticated CRUD
  if [[ $READ_ONLY == true ]]; then
    echo -e "\n  ${CYAN}[SKIP]${NC}  Read-only mode: skipping write tests (POST/PUT/DELETE/presigned-urls)"
    for lbl in "POST /posts" "GET /posts/:id" "PUT /posts/:id" "DELETE /posts/:id" "presigned-urls"; do
      rec_skip "$cloud" "$lbl"
    done
    return
  fi

  if [[ -z "$token" ]]; then
    echo -e "\n  ${CYAN}[SKIP]${NC}  Sections 4-6: no token provided"
    for lbl in "POST /posts" "GET /posts/:id" "PUT /posts/:id" "DELETE /posts/:id" "presigned-urls"; do
      rec_skip "$cloud" "$lbl"
    done
    return
  fi

  # 4. Create post
  echo -e "\n  ${BLUE}[4]${NC} CRUD (authenticated)"
  local ts
  ts=$(date +%s)
  http_req POST "$api_base/posts" "$token" \
    "{\"content\":\"[E2E] $cloud_up smoke test $ts\",\"isMarkdown\":false}"
  if [[ "$HTTP_STATUS" == "201" ]]; then
    local pid
    pid=$(echo "$HTTP_BODY" | jq -r '.postId // .post_id // ""' 2>/dev/null)
    if [[ -n "$pid" && "$pid" != "null" ]]; then
      echo -e "  ${GREEN}[PASS]${NC}  POST /posts → 201  (postId=$pid)"; rec_pass "$cloud" "POST /posts"
      created_ids+=("$pid")
    else
      echo -e "  ${RED}[FAIL]${NC}  POST /posts → 201 but no postId"; rec_fail "$cloud" "POST /posts"
      pid=""
    fi
  else
    echo -e "  ${RED}[FAIL]${NC}  POST /posts → $HTTP_STATUS (expected 201)"; rec_fail "$cloud" "POST /posts"
    [[ "$VERBOSE" == true ]] && echo "$HTTP_BODY" | head -c 300
    for lbl in "GET /posts/:id" "PUT /posts/:id" "DELETE /posts/:id" "presigned-urls"; do rec_skip "$cloud" "$lbl"; done
    return
  fi

  # 5. Get by ID
  http_req GET "$api_base/posts/$pid" "$token"
  if [[ "$HTTP_STATUS" == "200" ]]; then
    echo -e "  ${GREEN}[PASS]${NC}  GET /posts/$pid → 200"; rec_pass "$cloud" "GET /posts/:id"
  else
    echo -e "  ${RED}[FAIL]${NC}  GET /posts/$pid → $HTTP_STATUS"; rec_fail "$cloud" "GET /posts/:id"
  fi

  # 6. Update
  http_req PUT "$api_base/posts/$pid" "$token" \
    "{\"content\":\"[E2E] $cloud_up updated $ts\"}"
  if [[ "$HTTP_STATUS" == "200" ]]; then
    echo -e "  ${GREEN}[PASS]${NC}  PUT /posts/$pid → 200"; rec_pass "$cloud" "PUT /posts/:id"
  else
    echo -e "  ${RED}[FAIL]${NC}  PUT /posts/$pid → $HTTP_STATUS"; rec_fail "$cloud" "PUT /posts/:id"
  fi

  # 7. Presigned URL
  echo -e "\n  ${BLUE}[5]${NC} Presigned URL"
  http_req POST "$api_base/uploads/presigned-urls" "$token" \
    '{"count":1,"contentTypes":["image/jpeg"]}'
  if [[ "$HTTP_STATUS" == "200" ]] && echo "$HTTP_BODY" | jq -e '.urls[0].url' >/dev/null 2>&1; then
    echo -e "  ${GREEN}[PASS]${NC}  POST /uploads/presigned-urls → 200"; rec_pass "$cloud" "presigned-urls"
  else
    echo -e "  ${RED}[FAIL]${NC}  POST /uploads/presigned-urls → $HTTP_STATUS"; rec_fail "$cloud" "presigned-urls"
    [[ "$VERBOSE" == true ]] && echo "$HTTP_BODY" | head -c 300
  fi

  # 8. Delete
  echo -e "\n  ${BLUE}[6]${NC} Cleanup"
  for del_id in "${created_ids[@]}"; do
    http_req DELETE "$api_base/posts/$del_id" "$token"
    if [[ "$HTTP_STATUS" == "200" || "$HTTP_STATUS" == "204" ]]; then
      echo -e "  ${GREEN}[PASS]${NC}  DELETE /posts/$del_id → $HTTP_STATUS"; rec_pass "$cloud" "DELETE /posts/:id"
    else
      echo -e "  ${RED}[FAIL]${NC}  DELETE /posts/$del_id → $HTTP_STATUS"; rec_fail "$cloud" "DELETE /posts/:id"
    fi
  done
}

# ── Run all clouds ────────────────────────────────────────────

echo ""
echo -e "${BOLD}╔══════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BOLD}║         Multi-Cloud E2E Test Suite  (v2)                    ║${NC}"
echo -e "${BOLD}║         $(date '+%Y-%m-%d %H:%M:%S')                                 ║${NC}"
echo -e "${BOLD}╚══════════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "  AWS   API: ${CYAN}$AWS_API_URL${NC}"
echo -e "  Azure API: ${CYAN}$AZURE_API_URL${NC}"
echo -e "  GCP   API: ${CYAN}$GCP_API_URL${NC}"

test_cloud_suite "aws"   "$AWS_API_URL"   "$AWS_TOKEN"
test_cloud_suite "azure" "$AZURE_API_URL" "$AZURE_TOKEN"
test_cloud_suite "gcp"   "$GCP_API_URL"   "$GCP_TOKEN"

# ── Summary table ─────────────────────────────────────────────

echo ""
echo -e "${BOLD}═══════════════════════════════════════════════════════════════${NC}"
echo -e "${BOLD}  Summary Table${NC}"
echo -e "${BOLD}═══════════════════════════════════════════════════════════════${NC}"
echo ""

LABELS=(
  "GET /health"
  "GET /posts"
  "auth guard"
  "POST /posts"
  "GET /posts/:id"
  "PUT /posts/:id"
  "DELETE /posts/:id"
  "presigned-urls"
)

printf "  %-22s  %-8s  %-8s  %-8s\n" "Test" "AWS" "Azure" "GCP"
echo "  ─────────────────────────────────────────────────────────"
for label in "${LABELS[@]}"; do
  printf "  %-22s" "$label"
  for cloud in aws azure gcp; do
    result="${RESULTS[$cloud:$label]:-skip}"
    case "$result" in
      pass) printf "  ${GREEN}%-8s${NC}" "PASS" ;;
      fail) printf "  ${RED}%-8s${NC}"   "FAIL" ;;
      skip) printf "  ${CYAN}%-8s${NC}"  "SKIP" ;;
    esac
  done
  echo ""
done

echo ""
echo -e "${BOLD}═══════════════════════════════════════════════════════════════${NC}"
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
  echo -e "${GREEN}${BOLD}  ✅ All executed tests passed!${NC}"
  exit 0
else
  echo -e "${RED}${BOLD}  ❌ $FAIL test(s) failed.${NC}"
  if [[ -z "$AWS_TOKEN" && -z "$AZURE_TOKEN" && -z "$GCP_TOKEN" ]]; then
    echo ""
    echo -e "  ${YELLOW}TIP:${NC} Re-run with auth tokens to test CRUD:"
    echo "    $0 \\"
    echo "      --aws-token   \"\$(aws cognito-idp initiate-auth --auth-flow USER_PASSWORD_AUTH --client-id 1k41lqkds4oah55ns8iod30dv2 --auth-parameters USERNAME=YOU@example.com,PASSWORD=PW --region ap-northeast-1 --query AuthenticationResult.AccessToken --output text)\" \\"
    echo "      --gcp-token   \"\$(gcloud auth print-identity-token)\" \\"
    echo "      --azure-token \"<paste id_token from browser DevTools>\""
  fi
  exit 1
fi
