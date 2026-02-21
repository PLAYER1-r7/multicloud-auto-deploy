#!/usr/bin/env bash
# test-auth-crud.sh - 認証付きCRUDテスト (AWS / Azure / GCP)
# 使用法: CLOUD=aws|azure|gcp bash test-auth-crud.sh
set -euo pipefail

CLOUD="${CLOUD:-aws}"

# ========== カラー定義 ==========
GREEN="\033[0;32m"; RED="\033[0;31m"; YELLOW="\033[1;33m"; NC="\033[0m"
ok()   { echo -e "${GREEN}✅ PASS${NC} $*"; }
fail() { echo -e "${RED}❌ FAIL${NC} $*"; EXIT_CODE=1; }
info() { echo -e "${YELLOW}ℹ️  INFO${NC} $*"; }
EXIT_CODE=0
PASS=0; FAIL=0

run_test() {
  local name="$1"; local expect="${2:-200}"; local actual="$3"; local body="$4"
  if [[ "$actual" == "$expect" ]]; then
    ok "$name → HTTP $actual"
    PASS=$((PASS+1))
  else
    fail "$name → expected $expect, got $actual (body: $(echo "$body" | head -c 200))"
    FAIL=$((FAIL+1))
  fi
}

# ========== AWS ==========
if [[ "$CLOUD" == "aws" ]]; then
  echo "=== AWS 認証付き CRUD テスト ==="
  POOL_ID="ap-northeast-1_AoDxOvCib"
  CLIENT_ID="1k41lqkds4oah55ns8iod30dv2"
  API_BASE="https://z42qmqdqac.execute-api.ap-northeast-1.amazonaws.com"

  info "Cognito トークン取得中..."
  TOKEN=$(aws cognito-idp admin-initiate-auth \
    --user-pool-id "$POOL_ID" \
    --client-id "$CLIENT_ID" \
    --auth-flow ADMIN_USER_PASSWORD_AUTH \
    --auth-parameters "USERNAME=testuser-staging,PASSWORD=TestPass123!" \
    --region ap-northeast-1 \
    --query 'AuthenticationResult.AccessToken' --output text 2>&1)
  if [[ "$TOKEN" == "None" || -z "$TOKEN" ]]; then
    fail "Cognito トークン取得失敗"
    exit 1
  fi
  info "AccessToken 取得 OK: ${TOKEN:0:40}..."

  # 1. POST /posts (認証必須)
  BODY=$(curl -s -w "\n%{http_code}" -X POST "$API_BASE/posts" \
    -H "Authorization: Bearer $TOKEN" \
    -H "Content-Type: application/json" \
    -d '{"content":"Auth test post from test-auth-crud.sh","tags":["test","auth"]}')
  CODE=$(echo "$BODY" | tail -1); BODY=$(echo "$BODY" | head -n -1)
  run_test "POST /api/posts (auth)" 201 "$CODE" "$BODY"
  POST_ID=$(echo "$BODY" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get('post_id') or d.get('postId') or d.get('id') or '')" 2>/dev/null || echo "")
  info "作成された PostID: $POST_ID"

  # 2. POST /posts without auth → 401
  BODY=$(curl -s -w "\n%{http_code}" -X POST "$API_BASE/posts" \
    -H "Content-Type: application/json" \
    -d '{"content":"No auth test"}')
  CODE=$(echo "$BODY" | tail -1); BODY=$(echo "$BODY" | head -n -1)
  run_test "POST /api/posts (no auth → 401)" 401 "$CODE" "$BODY"

  # 3. GET /posts/{id} (公開)
  if [[ -n "$POST_ID" ]]; then
    BODY=$(curl -s -w "\n%{http_code}" "$API_BASE/posts/$POST_ID")
    CODE=$(echo "$BODY" | tail -1); BODY=$(echo "$BODY" | head -n -1)
    run_test "GET /api/posts/$POST_ID (public)" 200 "$CODE" "$BODY"
  else
    fail "POST_ID 未取得のため GET /posts/{id} スキップ"
    FAIL=$((FAIL+1))
  fi

  # 4. PUT /posts/{id} (auth) → update content
  if [[ -n "$POST_ID" ]]; then
    BODY=$(curl -s -w "\n%{http_code}" -X PUT "$API_BASE/posts/$POST_ID" \
      -H "Authorization: Bearer $TOKEN" \
      -H "Content-Type: application/json" \
      -d '{"content":"Updated auth test post"}')
    CODE=$(echo "$BODY" | tail -1); BODY=$(echo "$BODY" | head -n -1)
    run_test "PUT /api/posts/$POST_ID (auth)" 200 "$CODE" "$BODY"
  fi

  # 5. DELETE /posts/{id} (auth)
  if [[ -n "$POST_ID" ]]; then
    BODY=$(curl -s -w "\n%{http_code}" -X DELETE "$API_BASE/posts/$POST_ID" \
      -H "Authorization: Bearer $TOKEN")
    CODE=$(echo "$BODY" | tail -1); BODY=$(echo "$BODY" | head -n -1)
    run_test "DELETE /api/posts/$POST_ID (auth)" 200 "$CODE" "$BODY"
  fi

  # 6. DELETE /posts/{id} without auth → 401
  if [[ -n "$POST_ID" ]]; then
    BODY=$(curl -s -w "\n%{http_code}" -X DELETE "$API_BASE/posts/$POST_ID")
    CODE=$(echo "$BODY" | tail -1); BODY=$(echo "$BODY" | head -n -1)
    run_test "DELETE /api/posts/$POST_ID (no auth → 401/404)" "401" "$CODE" "$BODY"
  fi
fi

# ========== Azure ==========
if [[ "$CLOUD" == "azure" ]]; then
  echo "=== Azure 認証付き CRUD テスト ==="
  API_BASE="https://multicloud-auto-deploy-staging-func-d8a2guhfere0etcq.japaneast-01.azurewebsites.net/api"

  # Azure はブラウザOIDCフロー/Entra IDをテストするため、
  # ここではヘルスチェックのみ実行し、Auth テストは手動確認事項として記録する
  info "Azure CRUD テスト: API ベース = $API_BASE"
  BODY=$(curl -s -w "\n%{http_code}" "$API_BASE/health")
  CODE=$(echo "$BODY" | tail -1); BODY=$(echo "$BODY" | head -n -1)
  run_test "GET /api/health (Azure)" 200 "$CODE" "$BODY"

  # POST without auth → 401
  BODY=$(curl -s -w "\n%{http_code}" -X POST "$API_BASE/posts" \
    -H "Content-Type: application/json" \
    -d '{"content":"No auth test"}')
  CODE=$(echo "$BODY" | tail -1); BODY=$(echo "$BODY" | head -n -1)
  run_test "POST /api/posts (no auth → 401)" 401 "$CODE" "$BODY"

  info "Azure 有効認証テストはブラウザ/Entra ID OIDC フローが必要なため手動確認"
fi

# ========== GCP ==========
if [[ "$CLOUD" == "gcp" ]]; then
  echo "=== GCP 認証付き CRUD テスト ==="
  API_BASE="https://multicloud-auto-deploy-staging-api-son5b3ml7a-an.a.run.app"

  info "GCP CRUD テスト: API ベース = $API_BASE"
  BODY=$(curl -s -w "\n%{http_code}" "$API_BASE/health")
  CODE=$(echo "$BODY" | tail -1); BODY=$(echo "$BODY" | head -n -1)
  run_test "GET /api/health (GCP)" 200 "$CODE" "$BODY"

  # POST without auth → 401
  BODY=$(curl -s -w "\n%{http_code}" -X POST "$API_BASE/posts" \
    -H "Content-Type: application/json" \
    -d '{"content":"No auth test"}')
  CODE=$(echo "$BODY" | tail -1); BODY=$(echo "$BODY" | head -n -1)
  run_test "POST /api/posts (no auth → 401)" 401 "$CODE" "$BODY"

  info "GCP 有効認証テストは Firebase Auth ブラウザフローが必要なため手動確認"
fi

# ========== 結果 ==========
echo ""
echo "================================================"
echo "テスト結果 ($CLOUD): PASS=$PASS  FAIL=$FAIL"
echo "================================================"
exit $EXIT_CODE
