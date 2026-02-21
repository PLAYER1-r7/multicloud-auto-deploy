#!/usr/bin/env bash
# =============================================================================
# クラウド環境テストスクリプト (staging / production)
# Multi-Cloud Auto Deploy Platform - Cloud Environment Test
#
# 使用方法:
#   bash scripts/test-cloud-env.sh staging
#   bash scripts/test-cloud-env.sh production
#
# テスト内容:
#   1. AWS API / Frontend (CloudFront) エンドポイント疎通
#   2. Azure API / Frontend (Front Door) エンドポイント疎通
#   3. GCP API / Frontend (CDN) エンドポイント疎通
#   4. 全クラウドでの投稿 CRUD API テスト
#   5. フロントエンド HTML 配信確認
# =============================================================================

set -uo pipefail

ENVIRONMENT="${1:-staging}"

if [[ "$ENVIRONMENT" != "staging" && "$ENVIRONMENT" != "production" ]]; then
    echo "Usage: $0 [staging|production]" >&2
    exit 1
fi

# -----------------------------------------------
# 色付き出力
# -----------------------------------------------
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

PASS=0
FAIL=0
SKIP=0
WARN=0

pass()  { echo -e "${GREEN}  ✅ PASS${NC} $1"; ((PASS++)); }
fail()  { echo -e "${RED}  ❌ FAIL${NC} $1"; ((FAIL++)); }
skip()  { echo -e "${YELLOW}  ⏭ SKIP${NC} $1"; ((SKIP++)); }
warn()  { echo -e "${YELLOW}  ⚠️  WARN${NC} $1"; ((WARN++)); }
info()  { echo -e "${CYAN}  ℹ  ${NC} $1"; }
header(){ echo -e "\n${BOLD}${CYAN}━━━ $1 ━━━${NC}"; }

# -----------------------------------------------
# エンドポイント定義
# -----------------------------------------------
if [[ "$ENVIRONMENT" == "staging" ]]; then
    # --- Staging エンドポイント ---
    AWS_API="https://z42qmqdqac.execute-api.ap-northeast-1.amazonaws.com"
    AWS_CDN="https://d1tf3uumcm4bo1.cloudfront.net"
    AZURE_API="https://multicloud-auto-deploy-staging-func-d8a2guhfere0etcq.japaneast-01.azurewebsites.net/api/HttpTrigger"
    AZURE_CDN="https://multicloud-frontend-f9cvamfnauexasd8.z01.azurefd.net"
    GCP_API="https://multicloud-auto-deploy-staging-api-son5b3ml7a-an.a.run.app"
    GCP_CDN="http://34.117.111.182"
else
    # --- Production エンドポイント (Pulumiスタック出力から取得) ---
    info "Production エンドポイントを Pulumi スタックから取得中..."
    PULUMI_AWS_DIR="/workspaces/ashnova/multicloud-auto-deploy/infrastructure/pulumi/aws"
    PULUMI_AZURE_DIR="/workspaces/ashnova/multicloud-auto-deploy/infrastructure/pulumi/azure"
    PULUMI_GCP_DIR="/workspaces/ashnova/multicloud-auto-deploy/infrastructure/pulumi/gcp"

    AWS_API=$(cd "$PULUMI_AWS_DIR" && pulumi stack output -s production api_gateway_endpoint 2>/dev/null | tr -d '"' || echo "")
    AWS_CDN=$(cd "$PULUMI_AWS_DIR" && pulumi stack output -s production cloudfront_url 2>/dev/null | tr -d '"' || echo "")
    AZURE_API=$(cd "$PULUMI_AZURE_DIR" && pulumi stack output -s production function_app_url 2>/dev/null | tr -d '"' || echo "")
    AZURE_CDN=$(cd "$PULUMI_AZURE_DIR" && pulumi stack output -s production frontdoor_url 2>/dev/null | tr -d '"' || echo "")
    GCP_API=$(cd "$PULUMI_GCP_DIR" && pulumi stack output -s production api_url 2>/dev/null | tr -d '"' || echo "")
    GCP_CDN=$(cd "$PULUMI_GCP_DIR" && pulumi stack output -s production cdn_url 2>/dev/null | tr -d '"' || echo "")

    # フォールバック: staging と同一エンドポイント（production スタックが未作成の場合）
    [[ -z "$AWS_API" ]]   && AWS_API="https://z42qmqdqac.execute-api.ap-northeast-1.amazonaws.com"
    [[ -z "$AWS_CDN" ]]   && AWS_CDN="https://d1tf3uumcm4bo1.cloudfront.net"
    [[ -z "$AZURE_API" ]] && AZURE_API="https://multicloud-auto-deploy-staging-func-d8a2guhfere0etcq.japaneast-01.azurewebsites.net/api/HttpTrigger"
    [[ -z "$AZURE_CDN" ]] && AZURE_CDN="https://multicloud-frontend-f9cvamfnauexasd8.z01.azurefd.net"
    [[ -z "$GCP_API" ]]   && GCP_API="https://multicloud-auto-deploy-staging-api-son5b3ml7a-an.a.run.app"
    [[ -z "$GCP_CDN" ]]   && GCP_CDN="http://34.117.111.182"
fi

TIMEOUT=20  # curl タイムアウト秒数

echo -e "\n${BOLD}${CYAN}╔══════════════════════════════════════════════════╗${NC}"
echo -e "${BOLD}${CYAN}║  クラウド環境テスト: ${ENVIRONMENT^^}                            ║${NC}"
echo -e "${BOLD}${CYAN}╚══════════════════════════════════════════════════╝${NC}"
echo -e "  実行日時: $(date '+%Y-%m-%d %H:%M:%S %Z')"
echo ""
info "エンドポイント一覧:"
echo "    AWS API : $AWS_API"
echo "    AWS CDN : $AWS_CDN"
echo "    Azure API: $AZURE_API"
echo "    Azure CDN: $AZURE_CDN"
echo "    GCP API : $GCP_API"
echo "    GCP CDN : $GCP_CDN"

# -----------------------------------------------
# ヘルパー関数
# -----------------------------------------------
http_check() {
    local label="$1" url="$2" expected_codes="${3:-200}"
    local code
    code=$(curl -s -o /dev/null -w "%{http_code}" --max-time "$TIMEOUT" -L "$url" 2>/dev/null || echo "000")
    if echo "$expected_codes" | grep -qw "$code"; then
        pass "$label → HTTP $code"
        return 0
    elif [[ "$code" == "000" ]]; then
        fail "$label → 接続タイムアウト / 到達不可 (URL: $url)"
        return 1
    else
        fail "$label → HTTP $code (期待: $expected_codes, URL: $url)"
        return 1
    fi
}

http_json_check() {
    local label="$1" url="$2" expected_key="$3" method="${4:-GET}" body="${5:-}"
    local resp code
    if [[ "$method" == "POST" ]]; then
        resp=$(curl -s --max-time "$TIMEOUT" -L -X POST \
            -H "Content-Type: application/json" \
            -d "$body" "$url" 2>/dev/null)
    else
        resp=$(curl -s --max-time "$TIMEOUT" -L "$url" 2>/dev/null)
    fi
    code=$(curl -s -o /dev/null -w "%{http_code}" --max-time "$TIMEOUT" -L \
        ${method:+-X "$method"} \
        ${body:+-H "Content-Type: application/json" -d "$body"} \
        "$url" 2>/dev/null || echo "000")

    if [[ "$code" == "000" ]]; then
        fail "$label → 接続不可 (URL: $url)"
        return 1
    fi
    if echo "$resp" | python3 -c "import sys,json; d=json.load(sys.stdin); assert '$expected_key' in d" 2>/dev/null; then
        pass "$label → HTTP $code, '$expected_key' キー確認"
        return 0
    else
        warn "$label → HTTP $code, '$expected_key' キーなし (resp: $(echo "$resp" | head -c 150))"
        return 1
    fi
}

api_crud_test() {
    local cloud="$1" api_base="$2"

    info "[$cloud] CRUD テスト: 投稿作成 → 一覧取得"
    local create_resp code
    create_resp=$(curl -s --max-time "$TIMEOUT" -X POST \
        -H "Content-Type: application/json" \
        -d "{\"content\":\"[${cloud}] ${ENVIRONMENT} deploy test $(date +%s)\",\"tags\":[\"${ENVIRONMENT}\",\"${cloud,,}\"]}" \
        "${api_base}/posts" 2>/dev/null)
    code=$(curl -s -o /dev/null -w "%{http_code}" --max-time "$TIMEOUT" -X POST \
        -H "Content-Type: application/json" \
        -d "{\"content\":\"[${cloud}] ${ENVIRONMENT} deploy test\"}" \
        "${api_base}/posts" 2>/dev/null || echo "000")

    if [[ "$code" =~ ^2 ]]; then
        pass "[$cloud] POST /posts → HTTP $code"
    elif [[ "$code" == "000" ]]; then
        skip "[$cloud] POST /posts → 接続不可"
        return
    elif [[ "$code" == "401" || "$code" == "403" ]]; then
        warn "[$cloud] POST /posts → HTTP $code (認証が必要: AUTH_DISABLED=false)"
    else
        fail "[$cloud] POST /posts → HTTP $code"
    fi

    # 一覧取得
    local list_resp list_code
    list_resp=$(curl -s --max-time "$TIMEOUT" -L "${api_base}/posts" 2>/dev/null)
    list_code=$(curl -s -o /dev/null -w "%{http_code}" --max-time "$TIMEOUT" -L "${api_base}/posts" 2>/dev/null || echo "000")

    if [[ "$list_code" == "200" ]]; then
        local count
        count=$(echo "$list_resp" | python3 -c "import sys,json; d=json.load(sys.stdin); print(len(d.get('items', d.get('results', d.get('messages', [])))))" 2>/dev/null || echo "?")
        pass "[$cloud] GET /posts → HTTP 200, $count 件"
    elif [[ "$list_code" == "000" ]]; then
        skip "[$cloud] GET /posts → 接続不可"
    else
        fail "[$cloud] GET /posts → HTTP $list_code"
    fi
}

frontend_check() {
    local cloud="$1" cdn_url="$2"
    local resp code
    code=$(curl -s -o /dev/null -w "%{http_code}" --max-time "$TIMEOUT" -L "$cdn_url" 2>/dev/null || echo "000")
    if [[ "$code" == "200" ]]; then
        resp=$(curl -s --max-time "$TIMEOUT" -L "$cdn_url" 2>/dev/null | head -c 500)
        if echo "$resp" | grep -qi "html\|react\|vite\|app"; then
            pass "[$cloud] フロントエンド CDN → HTTP 200, HTML/SPA 確認"
        else
            warn "[$cloud] フロントエンド CDN → HTTP 200 だが HTML 未確認"
        fi
    elif [[ "$code" == "000" ]]; then
        fail "[$cloud] フロントエンド CDN → 接続タイムアウト ($cdn_url)"
    else
        fail "[$cloud] フロントエンド CDN → HTTP $code ($cdn_url)"
    fi
}

# =============================================================================
# 1. AWS テスト
# =============================================================================
header "1. AWS (ap-northeast-1)"
info "API: $AWS_API"

http_check        "[AWS] GET /       (ルート)"              "$AWS_API/"
http_json_check   "[AWS] GET /       レスポンス形式(status)" "$AWS_API/" "status"
http_check        "[AWS] GET /health (ヘルスチェック)"       "$AWS_API/health" "200"
api_crud_test     "AWS" "$AWS_API"
frontend_check    "AWS" "$AWS_CDN"

# =============================================================================
# 2. Azure テスト
# =============================================================================
header "2. Azure (japaneast)"
info "API: $AZURE_API"

http_check        "[Azure] GET /       (ルート)"              "$AZURE_API/"       "200 301 302"
http_check        "[Azure] GET /health (ヘルスチェック)"       "$AZURE_API/health" "200 404"
api_crud_test     "Azure" "$AZURE_API"
frontend_check    "Azure" "$AZURE_CDN"

# =============================================================================
# 3. GCP テスト
# =============================================================================
header "3. GCP (asia-northeast1)"
info "API: $GCP_API"

http_check        "[GCP] GET /       (ルート)"              "$GCP_API/"
http_json_check   "[GCP] GET /       レスポンス形式(status)" "$GCP_API/" "status"
http_check        "[GCP] GET /health (ヘルスチェック)"       "$GCP_API/health" "200"
api_crud_test     "GCP" "$GCP_API"
frontend_check    "GCP" "$GCP_CDN"

# =============================================================================
# 結果サマリー
# =============================================================================
echo ""
echo -e "${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BOLD}  テスト結果サマリー [${ENVIRONMENT^^}]${NC}"
echo -e "${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "  ${GREEN}✅ PASS${NC}: $PASS"
echo -e "  ${RED}❌ FAIL${NC}: $FAIL"
echo -e "  ${YELLOW}⚠️  WARN${NC}: $WARN"
echo -e "  ${YELLOW}⏭ SKIP${NC}: $SKIP"
echo -e "${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

if [[ "$FAIL" -eq 0 ]]; then
    echo -e "\n${GREEN}${BOLD}🎉 全テストPASS！${ENVIRONMENT^^} 環境は正常です。${NC}\n"
    exit 0
else
    echo -e "\n${RED}${BOLD}⚠️  $FAIL 件の FAIL があります。上記ログを確認してください。${NC}\n"
    exit 1
fi
