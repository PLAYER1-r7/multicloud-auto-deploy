#!/usr/bin/env bash
# ============================================================
# test-sns-local.sh — End-to-End test suite for local simple-sns
# ============================================================
#
# Docker Compose でローカル起動した simple-sns スタックをテストします。
#
# 対象サービス:
#   - API        (FastAPI + DynamoDB Local + MinIO) → localhost:8000
#   - React SPA  (nginx, /sns/)                    → localhost:3001
#   - static_site (nginx proxy, /sns/)             → localhost:8090
#
# 事前準備:
#   docker compose up -d --build
#   # 全サービス起動後（約30秒）に実行してください
#
# Usage:
#   ./scripts/test-sns-local.sh              # 標準テスト
#   ./scripts/test-sns-local.sh --verbose    # レスポンスボディを表示
#   ./scripts/test-sns-local.sh --skip-cleanup  # テスト投稿を削除しない
#
# Exit codes:
#   0 — All executed tests passed
#   1 — One or more tests failed
#   2 — Missing required dependency
#
# ============================================================

set -euo pipefail

# ── defaults ────────────────────────────────────────────────
API_URL="${API_URL:-http://localhost:8000}"
SPA_URL="${SPA_URL:-http://localhost:3001}"
STATIC_URL="${STATIC_URL:-http://localhost:8090}"
MINIO_URL="${MINIO_URL:-http://localhost:9000}"
VERBOSE=false
SKIP_CLEANUP=false

# ── colours ─────────────────────────────────────────────────
RED='\033[0;31m'; GREEN='\033[0;32m'
YELLOW='\033[1;33m'; BLUE='\033[0;34m'; CYAN='\033[0;36m'
BOLD='\033[1m'; NC='\033[0m'

# ── counters ────────────────────────────────────────────────
PASS=0; FAIL=0; SKIP=0

# ── helpers ─────────────────────────────────────────────────
ok()   { echo -e "${GREEN}[PASS]${NC}  $*"; PASS=$((PASS + 1)); }
fail() { echo -e "${RED}[FAIL]${NC}  $*"; FAIL=$((FAIL + 1)); }
warn() { echo -e "${YELLOW}[WARN]${NC}  $*"; }
skip() { echo -e "${CYAN}[SKIP]${NC}  $*"; SKIP=$((SKIP + 1)); }
sep()  { echo -e "${YELLOW}────────────────────────────────────────${NC}"; }
die()  { echo -e "${RED}ERROR: $*${NC}" >&2; exit 2; }

usage() {
  cat <<EOF
Usage: $0 [OPTIONS]

Options:
  --api   <url>        API base URL       (default: $API_URL)
  --spa   <url>        React SPA URL      (default: $SPA_URL)
  --static <url>       Static site URL    (default: $STATIC_URL)
  --minio <url>        MinIO URL          (default: $MINIO_URL)
  -v, --verbose        Print full response bodies
  -s, --skip-cleanup   Do not delete posts created during the test run
  -h, --help           Show this help
EOF
}

# ── arg parsing ─────────────────────────────────────────────
while [[ $# -gt 0 ]]; do
  case $1 in
    --api)    API_URL="$2";    shift 2 ;;
    --spa)    SPA_URL="$2";    shift 2 ;;
    --static) STATIC_URL="$2"; shift 2 ;;
    --minio)  MINIO_URL="$2";  shift 2 ;;
    -v|--verbose)      VERBOSE=true;       shift ;;
    -s|--skip-cleanup) SKIP_CLEANUP=true;  shift ;;
    -h|--help) usage; exit 0 ;;
    *) echo -e "${RED}Unknown option: $1${NC}"; usage; exit 1 ;;
  esac
done

API_URL="${API_URL%/}"
SPA_URL="${SPA_URL%/}"
STATIC_URL="${STATIC_URL%/}"
MINIO_URL="${MINIO_URL%/}"

# ── dependency check ────────────────────────────────────────
command -v curl    >/dev/null 2>&1 || die "curl is required"
command -v jq      >/dev/null 2>&1 || die "jq is required"
command -v python3 >/dev/null 2>&1 || die "python3 is required"

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

  local curl_args=(-s -o /tmp/local_sns_test_body -w "%{http_code}"
                   -X "$method" --max-time 15)
  [[ -n "$data" ]] && curl_args+=(-H "Content-Type: application/json" -d "$data")
  for h in "${extra_headers[@]}"; do curl_args+=("$h"); done
  curl_args+=("$url")

  local status
  status=$(curl "${curl_args[@]}" 2>/dev/null || echo "000")
  LAST_STATUS="$status"
  LAST_BODY=$(cat /tmp/local_sns_test_body 2>/dev/null || echo "")

  if [[ "$status" == "$expect" ]]; then
    ok "$label  [HTTP $status]"
    [[ "$VERBOSE" == true ]] && echo "$LAST_BODY" | jq . 2>/dev/null || true
  else
    fail "$label  [expected HTTP $expect, got HTTP $status]"
    [[ -n "$LAST_BODY" ]] && echo "  Response: $(echo "$LAST_BODY" | head -c 300)"
  fi
}

# ── banner ───────────────────────────────────────────────────
echo ""
echo -e "${BOLD}============================================================${NC}"
echo -e "${BOLD}  Local simple-sns — End-to-End Test Suite${NC}"
echo -e "${BOLD}============================================================${NC}"
echo -e "  API (FastAPI)  : ${CYAN}$API_URL${NC}"
echo -e "  React SPA      : ${CYAN}$SPA_URL${NC}"
echo -e "  Static site    : ${CYAN}$STATIC_URL${NC}"
echo -e "  MinIO          : ${CYAN}$MINIO_URL${NC}"
echo ""
# ════════════════════════════════════════════════════════════
sep
echo -e "${BOLD}Section 1 — Docker Compose サービス起動確認${NC}"
sep

for svc_url in "$API_URL/health" "$SPA_URL/" "$STATIC_URL/"; do
  if curl -s --max-time 5 "$svc_url" -o /dev/null 2>/dev/null; then
    ok "  $svc_url → 到達可能"
  else
    fail "  $svc_url → 接続不可  (docker compose up -d 済みか確認してください)"
  fi
done

if curl -s --max-time 5 "$MINIO_URL/minio/health/live" -o /dev/null 2>/dev/null; then
  ok "  MinIO $MINIO_URL → 到達可能"
else
  warn "  MinIO $MINIO_URL → 接続不可 (画像アップロードテストはスキップされます)"
fi

# ════════════════════════════════════════════════════════════
sep
echo -e "${BOLD}Section 2 — API ヘルスチェック (FastAPI)${NC}"
sep

run_test "GET /health returns 200" \
  GET "$API_URL/health"

if echo "$LAST_BODY" | jq -e '.status == "ok"' >/dev/null 2>&1; then
  ok "  .status == \"ok\""
  PROVIDER=$(echo "$LAST_BODY" | jq -r '.provider // "unknown"')
  echo -e "  provider = $PROVIDER"
else
  fail "  .status != \"ok\" in /health response"
fi

run_test "GET /docs (Swagger UI) returns 200" \
  GET "$API_URL/docs"

run_test "GET /posts returns 200 (unauthenticated, AUTH_DISABLED=true)" \
  GET "$API_URL/posts"

if echo "$LAST_BODY" | jq -e '.items' >/dev/null 2>&1; then
  COUNT=$(echo "$LAST_BODY" | jq '.items | length')
  ok "  .items array present ($COUNT posts)"
else
  fail "  .items missing in /posts response"
fi


# ════════════════════════════════════════════════════════════
sep
echo -e "${BOLD}Section 3 — React SPA (localhost:3001)${NC}"
sep

run_test "SPA GET / returns 200" \
  GET "$SPA_URL/"

# Content-Type 確認
SPA_CT=$(curl -s --max-time 10 -D - "$SPA_URL/" -o /dev/null 2>/dev/null \
  | grep -i '^content-type:' | head -1 | tr -d '\r\n' || echo "")
if echo "$SPA_CT" | grep -qi 'text/html'; then
  ok "  Content-Type is text/html  [$SPA_CT]"
else
  fail "  Unexpected Content-Type: $SPA_CT"
fi

# React SPA root element 確認
SPA_BODY=$(curl -s --max-time 10 "$SPA_URL/" 2>/dev/null || echo "")
if echo "$SPA_BODY" | grep -q '<div id="root"'; then
  ok "  React SPA root element (<div id=\"root\">) found"
else
  fail "  <div id=\"root\"> not found"
fi

# SPA deep-link fallback (React Router)
run_test "SPA GET /login returns 200 (SPA fallback)" \
  GET "$SPA_URL/login"
run_test "SPA GET /profile returns 200 (SPA fallback)" \
  GET "$SPA_URL/profile"

# ════════════════════════════════════════════════════════════
sep
echo -e "${BOLD}Section 4 — Static site /sns/ (localhost:8090)${NC}"
sep

run_test "Static site GET /sns/ returns 200" \
  GET "$STATIC_URL/sns/"

STATIC_BODY=$(curl -s --max-time 10 "$STATIC_URL/sns/" 2>/dev/null || echo "")
if echo "$STATIC_BODY" | grep -q '<div id="root"'; then
  ok "  <div id=\"root\"> found at /sns/"
else
  fail "  <div id=\"root\"> not found at /sns/"
fi

# API proxy 経由ルート確認（static_site nginx が /posts を API に転送）
run_test "Static site GET /health (nginx proxy) returns 200" \
  GET "$STATIC_URL/health"

run_test "Static site GET /posts (nginx proxy) returns 200" \
  GET "$STATIC_URL/posts"


# ════════════════════════════════════════════════════════════
sep
echo -e "${BOLD}Section 5 — Post CRUD (AUTH_DISABLED=true)${NC}"
sep

# 5-1. 投稿作成
run_test "POST /posts (text only) returns 201" \
  POST "$API_URL/posts" \
  --data '{"content":"[test] local E2E test post 🧪","isMarkdown":false}' \
  --expect 201

TEXT_POST_ID=$(echo "$LAST_BODY" | jq -r '.postId // .post_id // ""' 2>/dev/null)
if [[ -n "$TEXT_POST_ID" && "$TEXT_POST_ID" != "null" ]]; then
  ok "  Created post: $TEXT_POST_ID"
  CREATED_POST_IDS+=("$TEXT_POST_ID")
else
  warn "  Could not extract postId from response"
fi

# 5-2. 投稿取得
if [[ -n "${TEXT_POST_ID:-}" && "$TEXT_POST_ID" != "null" ]]; then
  run_test "GET /posts/:id returns 200" \
    GET "$API_URL/posts/$TEXT_POST_ID"
else
  skip "GET /posts/:id — post creation failed"
fi

# 5-3. 投稿更新
if [[ -n "${TEXT_POST_ID:-}" && "$TEXT_POST_ID" != "null" ]]; then
  run_test "PUT /posts/:id returns 200" \
    PUT "$API_URL/posts/$TEXT_POST_ID" \
    --data '{"content":"[test] updated by local E2E ✅"}' \
    --expect 200
else
  skip "PUT /posts/:id — post creation failed"
fi

# 5-4. 一覧取得・件数確認
run_test "GET /posts (list) returns 200" \
  GET "$API_URL/posts"

if echo "$LAST_BODY" | jq -e '.items | length >= 1' >/dev/null 2>&1; then
  POST_COUNT=$(echo "$LAST_BODY" | jq '.items | length')
  ok "  $POST_COUNT post(s) in list"
else
  fail "  .items is empty after creating a post"
fi

# 5-5. タグ付き投稿作成
run_test "POST /posts with tags returns 201" \
  POST "$API_URL/posts" \
  --data '{"content":"[test] tagged post","tags":["e2e","local"]}' \
  --expect 201

TAGGED_POST_ID=$(echo "$LAST_BODY" | jq -r '.postId // .post_id // ""' 2>/dev/null)
[[ -n "$TAGGED_POST_ID" && "$TAGGED_POST_ID" != "null" ]] && CREATED_POST_IDS+=("$TAGGED_POST_ID")

# 5-6. プロフィール取得
run_test "GET /profile returns 200" \
  GET "$API_URL/profile"


# ════════════════════════════════════════════════════════════
sep
echo -e "${BOLD}Section 6 — Image upload (MinIO presigned URL)${NC}"
sep

MINIO_LIVE=$(curl -s --max-time 5 "$MINIO_URL/minio/health/live" -o /dev/null -w "%{http_code}" 2>/dev/null || echo "000")
if [[ "$MINIO_LIVE" != "200" ]]; then
  skip "MinIO not reachable — skipping upload tests"
  SKIP=$((SKIP + 4))
else
  # 6-1. presigned URL 取得
  run_test "POST /uploads/presigned-urls (count=2) returns 200" \
    POST "$API_URL/uploads/presigned-urls" \
    --data '{"count":2,"contentTypes":["image/jpeg","image/png"]}' \
    --expect 200

  URL_COUNT=$(echo "$LAST_BODY" | jq '.urls | length' 2>/dev/null || echo 0)
  if [[ "$URL_COUNT" == "2" ]]; then
    ok "  Received $URL_COUNT presigned URLs"
  else
    fail "  Expected 2 presigned URLs, got $URL_COUNT"
  fi

  # 6-2. URL が MinIO エンドポイントを指しているか確認
  FIRST_URL=$(echo "$LAST_BODY" | jq -r '.urls[0].url // ""' 2>/dev/null)
  if echo "$FIRST_URL" | grep -qE "^http://localhost:9000|^http://minio:9000"; then
    ok "  Presigned URL points to local MinIO"
  elif [[ -n "$FIRST_URL" ]]; then
    warn "  Presigned URL: ${FIRST_URL:0:80}"
  fi

  # 6-3. 上限チェック (count=16)
  TYPES_16=$(python3 -c "import json; print(json.dumps({'count':16,'contentTypes':['image/jpeg']*16}))")
  run_test "POST /uploads/presigned-urls (count=16, max) returns 200" \
    POST "$API_URL/uploads/presigned-urls" \
    --data "$TYPES_16" \
    --expect 200

  # 6-4. 超過チェック (count=17 → 422)
  TYPES_17=$(python3 -c "import json; print(json.dumps({'count':17,'contentTypes':['image/jpeg']*17}))")
  run_test "POST /uploads/presigned-urls (count=17, over limit) returns 422" \
    POST "$API_URL/uploads/presigned-urls" \
    --data "$TYPES_17" \
    --expect 422

  # 6-5. imageKeys 付き投稿作成 (16件 OK)
  KEYS_2=$(python3 -c "
import json, uuid
keys = [f'testuser/{uuid.uuid4()}.jpg', f'testuser/{uuid.uuid4()}.jpg']
print(json.dumps({'content': '[test] post with imageKeys', 'imageKeys': keys}))
")
  run_test "POST /posts with imageKeys returns 201" \
    POST "$API_URL/posts" \
    --data "$KEYS_2" \
    --expect 201

  IMG_POST_ID=$(echo "$LAST_BODY" | jq -r '.postId // .post_id // ""' 2>/dev/null)
  [[ -n "$IMG_POST_ID" && "$IMG_POST_ID" != "null" ]] && CREATED_POST_IDS+=("$IMG_POST_ID")

  # 6-6. imageKeys 超過 (17件 → 422)
  KEYS_17=$(python3 -c "
import json, uuid
keys = [f'testuser/{uuid.uuid4()}.jpg' for _ in range(17)]
print(json.dumps({'content': '[test] should fail', 'imageKeys': keys}))
")
  run_test "POST /posts with 17 imageKeys returns 422" \
    POST "$API_URL/posts" \
    --data "$KEYS_17" \
    --expect 422
fi


# ════════════════════════════════════════════════════════════
sep
echo -e "${BOLD}Section 7 — Cleanup (delete test posts)${NC}"
sep

if [[ "$SKIP_CLEANUP" == false && ${#CREATED_POST_IDS[@]} -gt 0 ]]; then
  for pid in "${CREATED_POST_IDS[@]}"; do
    run_test "DELETE /posts/$pid" \
      DELETE "$API_URL/posts/$pid" \
      --expect 200
  done
else
  if [[ "$SKIP_CLEANUP" == true ]]; then
    warn "Cleanup skipped (--skip-cleanup). Created post IDs:"
    for pid in "${CREATED_POST_IDS[@]}"; do echo "  $pid"; done
  else
    warn "No test posts to clean up."
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
  echo "  docker compose logs api  でエラーを確認してください。"
  exit 1
fi
