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
echo -e "${BOLD}Section 3 — 認証テスト (AUTH_DISABLED mode)${NC}"
sep
echo -e "  ${CYAN}※ AUTH_DISABLED=true のためトークンなしで保護エンドポイントにアクセス可能${NC}"
echo ""

# 3-1. GET /profile (no token) → 200, userId must be "test-user-1"
run_test "GET /profile (no token, AUTH_DISABLED=true) returns 200" \
  GET "$API_URL/profile"

if echo "$LAST_BODY" | jq -e '.userId == "test-user-1"' >/dev/null 2>&1; then
  ok "  userId == \"test-user-1\" (mock user injected) ✓"
else
  ACTUAL_UID=$(echo "$LAST_BODY" | jq -r '.userId // "?"')
  fail "  Expected userId=test-user-1, got: $ACTUAL_UID"
fi

# 3-2. Bearer ダミートークン付きでも 200 (AUTH_DISABLED はトークンを無視)
run_test "GET /profile with Bearer dummy-token returns 200" \
  GET "$API_URL/profile" \
  --header "Authorization: Bearer dummy-local-token-ignored"

# 3-3. POST /posts （書き込みエンドポイント）をトークンなしで → 201
run_test "POST /posts (no token, AUTH_DISABLED=true) returns 201" \
  POST "$API_URL/posts" \
  --data '{"content":"[test] auth-check: no-token create"}' \
  --expect 201

AUTH_CHECK_POST_ID=$(echo "$LAST_BODY" | jq -r '.postId // .post_id // ""' 2>/dev/null)
if [[ -n "$AUTH_CHECK_POST_ID" && "$AUTH_CHECK_POST_ID" != "null" ]]; then
  CREATED_POST_IDS+=("$AUTH_CHECK_POST_ID")
  # 3-4. 作成された投稿の userId が mock user か確認
  if echo "$LAST_BODY" | jq -e '.userId == "test-user-1"' >/dev/null 2>&1; then
    ok "  Post created with userId == \"test-user-1\" ✓"
  else
    warn "  userId in created post: $(echo \"$LAST_BODY\" | jq -r '.userId // \"?\"')"
  fi
else
  warn "  Could not extract postId from auth test post"
fi

# ════════════════════════════════════════════════════════════
sep
echo -e "${BOLD}Section 4 — React SPA (localhost:3001)${NC}"
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
echo -e "${BOLD}Section 5 — Static site /sns/ (localhost:8090)${NC}"
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
echo -e "${BOLD}Section 6 — Post CRUD + タグ絞り込み (AUTH_DISABLED=true)${NC}"
sep

# 6-1. 投稿作成
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

# 6-2. 投稿取得
if [[ -n "${TEXT_POST_ID:-}" && "$TEXT_POST_ID" != "null" ]]; then
  run_test "GET /posts/:id returns 200" \
    GET "$API_URL/posts/$TEXT_POST_ID"
else
  skip "GET /posts/:id — post creation failed"
fi

# 6-3. 投稿更新
if [[ -n "${TEXT_POST_ID:-}" && "$TEXT_POST_ID" != "null" ]]; then
  run_test "PUT /posts/:id returns 200" \
    PUT "$API_URL/posts/$TEXT_POST_ID" \
    --data '{"content":"[test] updated by local E2E ✅"}' \
    --expect 200
else
  skip "PUT /posts/:id — post creation failed"
fi

# 6-4. 一覧取得・件数確認
run_test "GET /posts (list) returns 200" \
  GET "$API_URL/posts"

if echo "$LAST_BODY" | jq -e '.items | length >= 1' >/dev/null 2>&1; then
  POST_COUNT=$(echo "$LAST_BODY" | jq '.items | length')
  ok "  $POST_COUNT post(s) in list"
else
  fail "  .items is empty after creating a post"
fi

# 6-5. タグ付き投稿作成 (複数タグ)
run_test "POST /posts with tags=[e2e,local] returns 201" \
  POST "$API_URL/posts" \
  --data '{"content":"[test] multi-tag post","tags":["e2e","local"]}' \
  --expect 201

TAGGED_POST_ID=$(echo "$LAST_BODY" | jq -r '.postId // .post_id // ""' 2>/dev/null)
[[ -n "$TAGGED_POST_ID" && "$TAGGED_POST_ID" != "null" ]] && CREATED_POST_IDS+=("$TAGGED_POST_ID")

# ── タグフィルター ──────────────────────────────────────────
echo ""
echo -e "  ${CYAN}■ タグ絞り込みテスト (GET /posts?tag=...)${NC}"

# 6-6. alpha タグ付き投稿を作成
run_test "POST /posts with tag e2e-alpha returns 201" \
  POST "$API_URL/posts" \
  --data '{"content":"[test] alpha-tag post","tags":["e2e-alpha"]}' \
  --expect 201

ALPHA_POST_ID=$(echo "$LAST_BODY" | jq -r '.postId // .post_id // ""' 2>/dev/null)
[[ -n "$ALPHA_POST_ID" && "$ALPHA_POST_ID" != "null" ]] && CREATED_POST_IDS+=("$ALPHA_POST_ID")

# 6-7. beta タグ付き投稿を作成
run_test "POST /posts with tag e2e-beta returns 201" \
  POST "$API_URL/posts" \
  --data '{"content":"[test] beta-tag post","tags":["e2e-beta"]}' \
  --expect 201

BETA_POST_ID=$(echo "$LAST_BODY" | jq -r '.postId // .post_id // ""' 2>/dev/null)
[[ -n "$BETA_POST_ID" && "$BETA_POST_ID" != "null" ]] && CREATED_POST_IDS+=("$BETA_POST_ID")

# 6-8. ?tag=e2e-alpha → alpha 投稿のみ返る
run_test "GET /posts?tag=e2e-alpha returns 200" \
  GET "$API_URL/posts?tag=e2e-alpha"

if echo "$LAST_BODY" | jq -e '.items | length >= 1' >/dev/null 2>&1; then
  ALPHA_COUNT=$(echo "$LAST_BODY" | jq '.items | length')
  ALL_ALPHA=$(echo "$LAST_BODY" | jq '[.items[].tags // [] | contains(["e2e-alpha"])] | all')
  if [[ "$ALL_ALPHA" == "true" ]]; then
    ok "  $ALPHA_COUNT post(s) returned, all have tag e2e-alpha ✓"
  else
    fail "  Some posts missing tag e2e-alpha"
    [[ "$VERBOSE" == true ]] && echo "$LAST_BODY" | jq '[.items[].tags]'
  fi
else
  fail "  No posts returned for tag=e2e-alpha"
fi

# 6-9. ?tag=e2e-beta → beta 投稿のみ返る
run_test "GET /posts?tag=e2e-beta returns 200" \
  GET "$API_URL/posts?tag=e2e-beta"

if echo "$LAST_BODY" | jq -e '.items | length >= 1' >/dev/null 2>&1; then
  BETA_COUNT=$(echo "$LAST_BODY" | jq '.items | length')
  ALL_BETA=$(echo "$LAST_BODY" | jq '[.items[].tags // [] | contains(["e2e-beta"])] | all')
  if [[ "$ALL_BETA" == "true" ]]; then
    ok "  $BETA_COUNT post(s) returned, all have tag e2e-beta ✓"
  else
    fail "  Some posts missing tag e2e-beta"
  fi
else
  fail "  No posts returned for tag=e2e-beta"
fi

# 6-10. 存在しないタグ → 0件
run_test "GET /posts?tag=nonexistent-zzz9 returns 200" \
  GET "$API_URL/posts?tag=nonexistent-zzz9-e2e-tag"

if echo "$LAST_BODY" | jq -e '.items | length == 0' >/dev/null 2>&1; then
  ok "  0 posts returned for nonexistent tag ✓"
else
  NCOUNT=$(echo "$LAST_BODY" | jq '.items | length // "?"' 2>/dev/null)
  warn "  Expected 0 posts for nonexistent tag, got $NCOUNT"
fi

# 6-11. プロフィール取得
echo ""
run_test "GET /profile returns 200" \
  GET "$API_URL/profile"


# ════════════════════════════════════════════════════════════
sep
echo -e "${BOLD}Section 7 — 画像アップロード (MinIO 実機)${NC}"
sep

MINIO_LIVE=$(curl -s --max-time 5 "$MINIO_URL/minio/health/live" -o /dev/null -w "%{http_code}" 2>/dev/null || echo "000")
if [[ "$MINIO_LIVE" != "200" ]]; then
  skip "MinIO not reachable — skipping all upload tests"
  SKIP=$((SKIP + 8))
else
  # テスト用の最小 PNG を生成 (1×1 px, RGB)
  python3 -c "
import struct, zlib, sys
def chunk(t, d):
    raw = t + d
    return struct.pack('>I', len(d)) + raw + struct.pack('>I', zlib.crc32(raw) & 0xffffffff)
sig = b'\x89PNG\r\n\x1a\n'
ihdr = chunk(b'IHDR', struct.pack('>IIBBBBB', 1, 1, 8, 2, 0, 0, 0))
idat = chunk(b'IDAT', zlib.compress(b'\x00\xff\x7f\x00'))
iend = chunk(b'IEND', b'')
sys.stdout.buffer.write(sig + ihdr + idat + iend)
" > /tmp/test_tiny.png 2>/dev/null \
    && ok "Tiny PNG generated (/tmp/test_tiny.png, $(wc -c < /tmp/test_tiny.png) bytes)" \
    || { fail "Failed to generate test PNG"; }

  # ──────────────────────────────────────────────────────────
  echo ""
  echo -e "  ${CYAN}■ 1枚アップロード${NC}"

  # 7-1. presigned URL 取得 (count=1)
  run_test "POST /uploads/presigned-urls (count=1) returns 200" \
    POST "$API_URL/uploads/presigned-urls" \
    --data '{"count":1,"contentTypes":["image/png"]}' \
    --expect 200

  UPLOAD_URL_1=$(echo "$LAST_BODY" | jq -r '.urls[0].url // ""' 2>/dev/null)
  UPLOAD_KEY_1=$(echo "$LAST_BODY" | jq -r '.urls[0].key // ""' 2>/dev/null)

  # presigned URL が /storage/ 形式か確認
  if echo "$UPLOAD_URL_1" | grep -q '^/storage/'; then
    ok "  Presigned URL starts with /storage/  ✓"
  elif [[ -n "$UPLOAD_URL_1" ]]; then
    warn "  Presigned URL: ${UPLOAD_URL_1:0:80}"
  fi

  # 7-2. 1枚 PUT → MinIO (static_site:8090/storage/ proxy 経由)
  IMG1_POST_ID=""
  if [[ -n "$UPLOAD_URL_1" && "$UPLOAD_URL_1" != "null" ]]; then
    FULL_URL_1="${STATIC_URL}${UPLOAD_URL_1}"
    STS1=$(curl -s -o /dev/null -w "%{http_code}" \
      -X PUT "$FULL_URL_1" \
      -H "Content-Type: image/png" \
      --data-binary @/tmp/test_tiny.png \
      --max-time 15 2>/dev/null || echo "000")
    if [[ "$STS1" == "200" ]]; then
      ok "1枚 PUT → MinIO 成功  [HTTP 200]  key=$UPLOAD_KEY_1"
    else
      fail "1枚 PUT → MinIO 失敗  [HTTP $STS1]"
    fi

    # 7-3. 実際にアップロードした imageKey で投稿作成
    IMG1_DATA=$(python3 -c "import json; print(json.dumps({'content':'[test] 1-image post (real upload)','imageKeys':['$UPLOAD_KEY_1']}))")
    run_test "POST /posts with 1 real imageKey returns 201" \
      POST "$API_URL/posts" \
      --data "$IMG1_DATA" \
      --expect 201

    IMG1_POST_ID=$(echo "$LAST_BODY" | jq -r '.postId // .post_id // ""' 2>/dev/null)
    [[ -n "$IMG1_POST_ID" && "$IMG1_POST_ID" != "null" ]] && CREATED_POST_IDS+=("$IMG1_POST_ID")

    # imageUrls[0] が設定されているか確認
    if echo "$LAST_BODY" | jq -e '.imageUrls | length == 1' >/dev/null 2>&1; then
      IMG_URL_0=$(echo "$LAST_BODY" | jq -r '.imageUrls[0] // ""')
      ok "  imageUrls[0] = ${IMG_URL_0:0:80}"
    else
      fail "  imageUrls should have exactly 1 item"
    fi
  else
    skip "presigned URL 取得失敗 — 1枚アップロードをスキップ"
    SKIP=$((SKIP + 2))
  fi

  # ──────────────────────────────────────────────────────────
  echo ""
  echo -e "  ${CYAN}■ 16枚アップロード${NC}"

  # 7-4. presigned URL 取得 (count=16, 上限)
  TYPES_16=$(python3 -c "import json; print(json.dumps({'count':16,'contentTypes':['image/png']*16}))")
  run_test "POST /uploads/presigned-urls (count=16, max) returns 200" \
    POST "$API_URL/uploads/presigned-urls" \
    --data "$TYPES_16" \
    --expect 200

  UPLOAD_16_BODY="$LAST_BODY"
  URL16_COUNT=$(echo "$UPLOAD_16_BODY" | jq '.urls | length' 2>/dev/null || echo 0)
  if [[ "$URL16_COUNT" == "16" ]]; then
    ok "  Received $URL16_COUNT presigned URLs"
  else
    fail "  Expected 16 presigned URLs, got $URL16_COUNT"
  fi

  # 7-5. 16枚 PUT → MinIO (ループ)
  SIXTEEN_KEYS=()
  UPLOAD_FAIL_COUNT=0
  for i in $(seq 0 15); do
    U=$(echo "$UPLOAD_16_BODY" | jq -r ".urls[$i].url // \"\"" 2>/dev/null)
    K=$(echo "$UPLOAD_16_BODY" | jq -r ".urls[$i].key // \"\"" 2>/dev/null)
    [[ -z "$U" || "$U" == "null" ]] && { UPLOAD_FAIL_COUNT=$((UPLOAD_FAIL_COUNT + 1)); continue; }
    FULL="${STATIC_URL}${U}"
    S=$(curl -s -o /dev/null -w "%{http_code}" \
      -X PUT "$FULL" -H "Content-Type: image/png" \
      --data-binary @/tmp/test_tiny.png --max-time 15 2>/dev/null || echo "000")
    if [[ "$S" == "200" ]]; then
      SIXTEEN_KEYS+=("$K")
    else
      UPLOAD_FAIL_COUNT=$((UPLOAD_FAIL_COUNT + 1))
    fi
  done

  if [[ ${#SIXTEEN_KEYS[@]} -eq 16 ]]; then
    ok "16枚 PUT → MinIO 全成功  (${#SIXTEEN_KEYS[@]}/16)"
  elif [[ ${#SIXTEEN_KEYS[@]} -gt 0 ]]; then
    warn "16枚 PUT → 一部失敗  (成功: ${#SIXTEEN_KEYS[@]}/16, 失敗: $UPLOAD_FAIL_COUNT)"
  else
    fail "16枚 PUT → 全失敗  (fail=$UPLOAD_FAIL_COUNT)"
  fi

  # 7-6. 16枚 imageKeys 付き投稿作成
  if [[ ${#SIXTEEN_KEYS[@]} -eq 16 ]]; then
    KEYS_16_JSON=$(python3 -c "
import json, sys
keys = json.loads(sys.stdin.read())
print(json.dumps({'content': '[test] 16-image post (real upload)', 'imageKeys': keys}))
" <<< "$(printf '%s\n' "${SIXTEEN_KEYS[@]}" | jq -R . | jq -s .)")
    run_test "POST /posts with 16 real imageKeys returns 201" \
      POST "$API_URL/posts" \
      --data "$KEYS_16_JSON" \
      --expect 201

    IMG16_POST_ID=$(echo "$LAST_BODY" | jq -r '.postId // .post_id // ""' 2>/dev/null)
    [[ -n "$IMG16_POST_ID" && "$IMG16_POST_ID" != "null" ]] && CREATED_POST_IDS+=("$IMG16_POST_ID")

    if echo "$LAST_BODY" | jq -e '.imageUrls | length == 16' >/dev/null 2>&1; then
      ok "  imageUrls | length == 16 ✓"
    else
      ICOUNT=$(echo "$LAST_BODY" | jq '.imageUrls | length // 0' 2>/dev/null)
      fail "  imageUrls should have 16 items, got: $ICOUNT"
    fi
  else
    skip "アップロード成功数が 16 未満 — 16枚投稿テストをスキップ"
    SKIP=$((SKIP + 1))
  fi

  # ──────────────────────────────────────────────────────────
  echo ""
  echo -e "  ${CYAN}■ 上限・エラーチェック${NC}"

  # 7-7. count=17 → 422
  TYPES_17=$(python3 -c "import json; print(json.dumps({'count':17,'contentTypes':['image/png']*17}))")
  run_test "POST /uploads/presigned-urls (count=17, over limit) returns 422" \
    POST "$API_URL/uploads/presigned-urls" \
    --data "$TYPES_17" \
    --expect 422

  # 7-8. imageKeys 17件 → 422
  KEYS_17=$(python3 -c "
import json, uuid
keys = [f'images/test-user-1/{uuid.uuid4()}' for _ in range(17)]
print(json.dumps({'content': '[test] should fail', 'imageKeys': keys}))
")
  run_test "POST /posts with 17 imageKeys returns 422" \
    POST "$API_URL/posts" \
    --data "$KEYS_17" \
    --expect 422
fi


# ════════════════════════════════════════════════════════════
sep
echo -e "${BOLD}Section 8 — Cleanup (delete test posts)${NC}"
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
