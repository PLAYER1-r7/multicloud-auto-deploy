#!/bin/bash
# ========================================
# Script Name: test-staging-sns.sh
# Description: Staging Verification for Simple SNS (Posts API + Frontend)
# Author: PLAYER1-r7
# Created: 2026-02-20
# Version: 1.0.0
# ========================================
#
# Usage:
#   # Auto-fill known staging endpoints by cloud
#   ./scripts/test-staging-sns.sh --cloud aws [--token JWT] [--verbose]
#   ./scripts/test-staging-sns.sh --cloud azure [--token JWT] [--verbose]
#   ./scripts/test-staging-sns.sh --cloud gcp [--token JWT] [--verbose]
#
#   # Custom endpoints
#   ./scripts/test-staging-sns.sh --api-url URL --frontend-url URL [--token JWT] [--verbose]
#
# Parameters:
#   --cloud [aws|azure|gcp]  - Cloud provider (auto-fills known staging URLs)
#   --api-url URL            - API base URL (overrides --cloud)
#   --frontend-url URL       - Frontend base URL (overrides --cloud)
#   --token JWT              - JWT token for auth-required endpoint tests
#   -v, --verbose            - Show full response body
#   -h, --help               - Show this message
#
# Test Cases (unauthenticated):
#   1. API health check
#   2. Posts list (GET /posts)
#   3. Posts list with limit query
#   4. Posts list with tag filter
#   5. Invalid post ID → 404
#   6. Unauthenticated create → 401/403
#   7. Unauthenticated upload → 401/403
#   8. Frontend /sns/ → 200
#
# Test Cases (requires --token):
#   9.  Create post
#   10. Get created post by ID
#   11. Update post
#   12. Upload presigned URL generation
#   13. Delete post
#
# Exit Codes:
#   0 - All tests passed
#   1 - One or more tests failed
#
# ========================================

set -euo pipefail

# ── カラー ──────────────────────────────────────────────────
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

# ── 既知のステージング URL ────────────────────────────────
declare -A AWS_URLS=(
  [api]="https://z42qmqdqac.execute-api.ap-northeast-1.amazonaws.com"
  [frontend]="https://d1tf3uumcm4bo1.cloudfront.net"
)
declare -A AZURE_URLS=(
  [api]="https://multicloud-auto-deploy-staging-func-d8a2guhfere0etcq.japaneast-01.azurewebsites.net/api/HttpTrigger"
  [frontend]="https://mcad-staging-d45ihd-dseygrc9c3a3htgj.z01.azurefd.net"
)
declare -A GCP_URLS=(
  [api]="https://multicloud-auto-deploy-staging-api-son5b3ml7a-an.a.run.app"
  [frontend]="http://34.117.111.182"
)

# ── デフォルト値 ──────────────────────────────────────────
API_URL=""
FRONTEND_URL=""
AUTH_TOKEN=""
VERBOSE=false
CLOUD=""
AUTH_DISABLED=false

# ── ヘルプ ────────────────────────────────────────────────
show_help() {
  cat << 'EOF'
使用方法:
  ./scripts/test-staging-sns.sh --cloud [aws|azure|gcp] [--token JWT] [--verbose]
  ./scripts/test-staging-sns.sh --api-url URL --frontend-url URL [--token JWT] [--verbose]

オプション:
  --cloud [aws|azure|gcp]  既知のステージング URL を自動セット
  --api-url URL            API ベース URL（--cloud を上書き）
  --frontend-url URL       フロントエンド URL（--cloud を上書き）
  --token JWT              認証付きテスト用 JWT トークン
  --auth-disabled          401/403 ガードチェックをスキップ（ローカル開発用）
  -v, --verbose            レスポンスボディを表示
  -h, --help               このヘルプを表示

例:
  ./scripts/test-staging-sns.sh --cloud aws
  ./scripts/test-staging-sns.sh --cloud aws --token "eyJ..."
  ./scripts/test-staging-sns.sh --api-url https://my-api.example.com --frontend-url https://my-cdn.example.com
EOF
}

# ── 引数パース ────────────────────────────────────────────
while [[ $# -gt 0 ]]; do
  case $1 in
    --cloud)
      CLOUD="$2"; shift 2 ;;
    --api-url)
      API_URL="$2"; shift 2 ;;
    --frontend-url)
      FRONTEND_URL="$2"; shift 2 ;;
    --token)
      AUTH_TOKEN="$2"; shift 2 ;;
    --auth-disabled)
      AUTH_DISABLED=true; shift ;;
    -v|--verbose)
      VERBOSE=true; shift ;;
    -h|--help)
      show_help; exit 0 ;;
    *)
      echo -e "${RED}エラー: 不明なオプション: $1${NC}"; show_help; exit 1 ;;
  esac
done

# ── URL の解決 ────────────────────────────────────────────
if [[ -n "$CLOUD" ]]; then
  case "$CLOUD" in
    aws)
      [[ -z "$API_URL" ]]      && API_URL="${AWS_URLS[api]}"
      [[ -z "$FRONTEND_URL" ]] && FRONTEND_URL="${AWS_URLS[frontend]}" ;;
    azure)
      [[ -z "$API_URL" ]]      && API_URL="${AZURE_URLS[api]}"
      [[ -z "$FRONTEND_URL" ]] && FRONTEND_URL="${AZURE_URLS[frontend]}" ;;
    gcp)
      [[ -z "$API_URL" ]]      && API_URL="${GCP_URLS[api]}"
      [[ -z "$FRONTEND_URL" ]] && FRONTEND_URL="${GCP_URLS[frontend]}" ;;
    *)
      echo -e "${RED}エラー: --cloud は aws / azure / gcp のいずれかを指定してください${NC}"
      exit 1 ;;
  esac
fi

if [[ -z "$API_URL" ]]; then
  echo -e "${RED}エラー: --cloud または --api-url が必要です${NC}"
  show_help; exit 1
fi

# 末尾スラッシュ除去
API_URL="${API_URL%/}"
FRONTEND_URL="${FRONTEND_URL%/}"

# ── カウンター ────────────────────────────────────────────
TESTS_PASSED=0
TESTS_FAILED=0
TESTS_SKIPPED=0

# ── ユーティリティ ────────────────────────────────────────
pass() { echo -e "${GREEN}✅ PASS${NC}"; TESTS_PASSED=$((TESTS_PASSED + 1)); }
fail() { echo -e "${RED}❌ FAIL${NC}"; TESTS_FAILED=$((TESTS_FAILED + 1)); }
skip() { echo -e "${YELLOW}⏭  SKIP${NC}"; TESTS_SKIPPED=$((TESTS_SKIPPED + 1)); }

# run_test <label> <method> <url> <data|--> <expected_status> [auth_header]
# Returns response body via REPLY global.
REPLY=""
run_test() {
  local label="$1"
  local method="$2"
  local url="$3"
  local data="$4"
  local expected="$5"
  local auth_header="${6:-}"

  printf "  %-55s" "$label"

  local args=(-s -w "\n%{http_code}" -X "$method" "$url" -H "Content-Type: application/json")
  [[ -n "$auth_header" ]] && args+=(-H "Authorization: Bearer $auth_header")
  [[ "$data" != "--" ]]   && args+=(-d "$data")

  local raw
  raw=$(curl "${args[@]}")
  local body status
  status=$(echo "$raw" | tail -n1)
  body=$(echo "$raw" | head -n -1)
  REPLY="$body"

  if [[ "$status" -eq "$expected" ]]; then
    pass
    if [[ "$VERBOSE" == true && -n "$body" ]]; then
      echo "     $(echo "$body" | python3 -m json.tool 2>/dev/null || echo "$body")"
    fi
    return 0
  else
    fail
    echo "     期待: $expected  実際: $status"
    [[ -n "$body" ]] && echo "     レスポンス: $body" | head -c 300
    echo
    return 1
  fi
}

section() { echo ""; echo -e "${CYAN}── $1 ──────────────────────────────────────${NC}"; }

# ══════════════════════════════════════════════════
echo -e "${BLUE}╔══════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║  Simple SNS Staging Verification         ║${NC}"
echo -e "${BLUE}╚══════════════════════════════════════════╝${NC}"
echo ""
echo "  API URL      : $API_URL"
echo "  Frontend URL : ${FRONTEND_URL:-（未指定）}"
  echo "  Auth Token   : $([ -n "$AUTH_TOKEN" ] && echo "provided" || echo "none — auth tests will be skipped")"
  echo "  Auth Disabled: $AUTH_DISABLED"
  echo "  Verbose      : $VERBOSE"
echo ""

# ══════════════════════════════════════════════════
section "1. API ヘルスチェック"
# ══════════════════════════════════════════════════

run_test "GET /health" GET "$API_URL/health" -- 200 || true
run_test "GET / (root)" GET "$API_URL/" -- 200 || true

# ══════════════════════════════════════════════════
section "2. Posts API — 認証不要"
# ══════════════════════════════════════════════════

run_test "GET /posts (一覧取得)" \
  GET "$API_URL/posts" -- 200 || true

run_test "GET /posts?limit=5 (件数制限)" \
  GET "$API_URL/posts?limit=5" -- 200 || true

run_test "GET /posts?limit=5&tag=test (タグフィルター)" \
  GET "$API_URL/posts?limit=5&tag=test" -- 200 || true

# 存在しない postId → 404
run_test "GET /posts/nonexistent-id-00000 → 404" \
  GET "$API_URL/posts/nonexistent-id-00000" -- 404 || true

# ══════════════════════════════════════════════════
section "3. Auth ガード — 401/403 チェック（トークンなし）"
# ══════════════════════════════════════════════════

if [[ "$AUTH_DISABLED" == true ]]; then
  echo ""
  echo -e "  ${YELLOW}--auth-disabled が指定されているため 401/403 ガードチェックをスキップ${NC}"
  TESTS_SKIPPED=$((TESTS_SKIPPED + 2))
else
  # POST /posts — 401 を期待、クラウドによっては 403
  run_test "POST /posts （トークンなし）→ 401" \
    POST "$API_URL/posts" '{"content":"no-auth test"}' 401 || \
    { TESTS_FAILED=$((TESTS_FAILED - 1)); run_test "POST /posts （トークンなし）→ 403" POST "$API_URL/posts" '{"content":"no-auth test"}' 403 || true; }

  # POST /uploads/presigned-urls — 401 を期待
  run_test "POST /uploads/presigned-urls （トークンなし）→ 401" \
    POST "$API_URL/uploads/presigned-urls" '{"count":1}' 401 || \
    { TESTS_FAILED=$((TESTS_FAILED - 1)); run_test "POST /uploads/presigned-urls （トークンなし）→ 403" POST "$API_URL/uploads/presigned-urls" '{"count":1}' 403 || true; }
fi

# ══════════════════════════════════════════════════
section "4. Posts API — 認証付き CRUD"
# ══════════════════════════════════════════════════

if [[ -z "$AUTH_TOKEN" ]]; then
  echo ""
  echo -e "  ${YELLOW}--token が未指定のため CRUD テストをスキップします${NC}"
  echo -e "  ${YELLOW}再実行: $0 --cloud ${CLOUD:-aws} --token \"<JWT>\"${NC}"
  TESTS_SKIPPED=$((TESTS_SKIPPED + 5))
else
  # 4-a. 投稿作成
  TIMESTAMP=$(date +%s)
  CREATE_BODY="{\"content\":\"[staging-test] Hello from CI at ${TIMESTAMP}\",\"tags\":[\"staging\",\"ci\"]}"

  run_test "POST /posts (投稿作成)" \
    POST "$API_URL/posts" "$CREATE_BODY" 201 "$AUTH_TOKEN" || true

  POST_ID=$(echo "$REPLY" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('postId', d.get('id','')))" 2>/dev/null || true)

  if [[ -z "$POST_ID" ]]; then
    echo -e "  ${RED}投稿 ID を取得できませんでした。後続の CRUD テストをスキップします。${NC}"
    TESTS_SKIPPED=$((TESTS_SKIPPED + 4))
  else
    echo "  作成された postId: $POST_ID"

    # 4-b. 1件取得
    run_test "GET /posts/$POST_ID (1件取得)" \
      GET "$API_URL/posts/$POST_ID" -- 200 "$AUTH_TOKEN" || true

    # 4-c. 更新
    UPDATE_BODY="{\"content\":\"[staging-test] Updated at ${TIMESTAMP} ✅\"}"
    run_test "PUT /posts/$POST_ID (更新)" \
      PUT "$API_URL/posts/$POST_ID" "$UPDATE_BODY" 200 "$AUTH_TOKEN" || true

    # 4-d. 更新後の内容確認
    run_test "GET /posts/$POST_ID (更新確認)" \
      GET "$API_URL/posts/$POST_ID" -- 200 "$AUTH_TOKEN" || true

    # 4-e. 削除
    run_test "DELETE /posts/$POST_ID (削除)" \
      DELETE "$API_URL/posts/$POST_ID" -- 200 "$AUTH_TOKEN" || true
  fi
fi

# ══════════════════════════════════════════════════
section "5. 画像アップロード URL 生成"
# ══════════════════════════════════════════════════

if [[ -z "$AUTH_TOKEN" ]]; then
  echo ""
  echo -e "  ${YELLOW}--token が未指定のためスキップ${NC}"
  TESTS_SKIPPED=$((TESTS_SKIPPED + 1))
else
  run_test "POST /uploads/presigned-urls (count=1)" \
    POST "$API_URL/uploads/presigned-urls" '{"count":1}' 200 "$AUTH_TOKEN" || true

  # 発行された URL が https/http で始まるか確認
  PRESIGNED_URL=$(echo "$REPLY" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['urls'][0]['url'])" 2>/dev/null || true)
  if [[ "$PRESIGNED_URL" =~ ^https?:// ]]; then
    echo -e "  ${GREEN}presigned URL 形式: OK${NC}  ($PRESIGNED_URL)" | head -c 120
    echo
  else
    echo -e "  ${RED}presigned URL の形式が不正です: '$PRESIGNED_URL'${NC}"
    TESTS_FAILED=$((TESTS_FAILED + 1))
  fi
fi

# ══════════════════════════════════════════════════
section "6. フロントエンド — /sns/ SPA"
# ══════════════════════════════════════════════════

if [[ -z "$FRONTEND_URL" ]]; then
  echo ""
  echo -e "  ${YELLOW}--frontend-url が未指定のためスキップ${NC}"
  TESTS_SKIPPED=$((TESTS_SKIPPED + 2))
else
  run_test "GET $FRONTEND_URL/sns/ → 200" \
    GET "$FRONTEND_URL/sns/" -- 200 || true

  # SPA は存在しないサブパスもフォールバックで 200 を返す
  run_test "GET $FRONTEND_URL/sns/unknown-path → 200 (SPA fallback)" \
    GET "$FRONTEND_URL/sns/unknown-path" -- 200 || true
fi

# ══════════════════════════════════════════════════
# 結果サマリー
# ══════════════════════════════════════════════════
TOTAL=$((TESTS_PASSED + TESTS_FAILED + TESTS_SKIPPED))

echo ""
echo -e "${BLUE}╔══════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║  テスト結果サマリー                      ║${NC}"
echo -e "${BLUE}╚══════════════════════════════════════════╝${NC}"
echo ""
printf "  総テスト数  : %d\n" "$TOTAL"
printf "  ${GREEN}成功${NC}        : %d\n" "$TESTS_PASSED"
printf "  ${RED}失敗${NC}        : %d\n" "$TESTS_FAILED"
printf "  ${YELLOW}スキップ${NC}    : %d\n" "$TESTS_SKIPPED"
echo ""

if [[ $TESTS_FAILED -eq 0 ]]; then
  echo -e "  ${GREEN}🎉 全テスト成功！ステージング環境は正常に動作しています。${NC}"
  exit 0
else
  echo -e "  ${RED}⚠️  $TESTS_FAILED 件のテストが失敗しました。上記のエラーを確認してください。${NC}"
  exit 1
fi
