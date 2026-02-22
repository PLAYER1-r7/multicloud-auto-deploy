#!/usr/bin/env bash
# =============================================================================
# fix-staging-routing.sh
# =============================================================================
# Staging 環境の CDN ルーティングを React SPA 対応に修正するスクリプト。
#
# 背景:
#   2026-02-21 に React SPA 移行が行われ、Production の CDN ルーティングが修正された。
#   しかし Staging 環境は同等の修正が未適用のため、旧 Python frontend-web が表示される。
#   (詳細: docs/REACT_SPA_MIGRATION_REPORT.md)
#
# 修正内容:
#   [AWS]   CloudFront Function "spa-sns-rewrite-staging" を作成し、
#           /sns* behavior を S3 オリジンへ向ける (pulumi up --stack staging)
#   [Azure] /sns/* → Azure Functions frontend-web の古いルートを削除し、
#           /* → Blob Storage (React SPA) のみにする
#   [GCP]   URL Map の /sns/* → Cloud Run pathRule を削除し、
#           デフォルト (GCS backend bucket) に落とす
#
# 前提条件:
#   - AWS CLI (aws) が設定済み
#   - Azure CLI (az) がログイン済み
#   - gcloud CLI がログイン済み / プロジェクト設定済み
#   - Pulumi CLI + PULUMI_ACCESS_TOKEN 設定済み
#   - python3 が利用可能

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

log()   { echo "▶ $*"; }
ok()    { echo "  ✅ $*"; }
warn()  { echo "  ⚠️  $*"; }
err()   { echo "  ❌ $*" >&2; }

AWS_REGION="ap-northeast-1"

STAGING_CF_DISTRIBUTION="E1TBH4R432SZBZ"
STAGING_S3_CF_URL="https://d1tf3uumcm4bo1.cloudfront.net"

AZURE_RG="multicloud-auto-deploy-staging-rg"
AZURE_FD_PROFILE="multicloud-auto-deploy-staging-fd"
AZURE_AFD_ENDPOINT="mcad-staging-d45ihd"
AZURE_AFD_URL="https://mcad-staging-d45ihd-dseygrc9c3a3htgj.z01.azurefd.net"

GCP_URLMAP="multicloud-auto-deploy-staging-cdn-urlmap"
GCP_STAGING_IP="34.117.111.182"

echo "============================================="
echo " Staging CDN Routing Fix (React SPA)"
echo "============================================="
echo ""

# ===========================================
# [AWS] CloudFront Function + Pulumi up
# ===========================================
log "[AWS] CloudFront Function spa-sns-rewrite-staging の確認・作成"

EXISTING_FUNC=$(aws cloudfront list-functions \
  --region us-east-1 \
  --query "FunctionList.Items[?Name=='spa-sns-rewrite-staging'].FunctionSummary.Name" \
  --output text 2>/dev/null || echo "")

if [ -n "$EXISTING_FUNC" ]; then
  ok "spa-sns-rewrite-staging は既に存在します"
else
  warn "spa-sns-rewrite-staging が存在しません。作成します..."
  CF_CODE='function handler(event){var request=event.request;var uri=request.uri;if(uri==="/sns"||uri==="/sns/"){request.uri="/sns/index.html";}return request;}'

  CREATE_OUTPUT=$(aws cloudfront create-function \
    --region us-east-1 \
    --name "spa-sns-rewrite-staging" \
    --function-config '{"Comment":"SPA /sns routing staging","Runtime":"cloudfront-js-2.0"}' \
    --function-code "$CF_CODE")

  ETAG=$(echo "$CREATE_OUTPUT" | python3 -c "import sys,json; print(json.load(sys.stdin)['ETag'])")

  aws cloudfront publish-function \
    --region us-east-1 \
    --name "spa-sns-rewrite-staging" \
    --if-match "$ETAG"

  ok "spa-sns-rewrite-staging を作成・LIVE 公開しました"
fi

log "[AWS] pulumi up --stack staging を実行"
cd "${REPO_ROOT}/infrastructure/pulumi/aws"
pulumi stack select staging
pulumi up --stack staging --yes
ok "AWS staging stack に CloudFront routing + CF Function が適用されました"

# CloudFront キャッシュ無効化
log "[AWS] CloudFront キャッシュ無効化 (/sns*)"
aws cloudfront create-invalidation \
  --distribution-id "$STAGING_CF_DISTRIBUTION" \
  --paths "/sns*" \
  --region us-east-1 \
  --no-cli-pager
ok "CloudFront キャッシュ無効化リクエストを発行"

cd "${REPO_ROOT}"
echo ""

# ===========================================
# [Azure] Front Door 旧 /sns/* ルート削除
# ===========================================
log "[Azure] staging Front Door の現在のルート一覧"
az afd route list \
  --resource-group "$AZURE_RG" \
  --profile-name "$AZURE_FD_PROFILE" \
  --endpoint-name "$AZURE_AFD_ENDPOINT" \
  --query "[].{Name:name, Patterns:patternsToMatch, OriginGroup:originGroup.id}" \
  --output table

log "[Azure] /sns/* ルートの確認"
SNS_ROUTE=$(az afd route list \
  --resource-group "$AZURE_RG" \
  --profile-name "$AZURE_FD_PROFILE" \
  --endpoint-name "$AZURE_AFD_ENDPOINT" \
  --query "[?contains(patternsToMatch, '/sns/*')].name" \
  --output tsv 2>/dev/null || echo "")

if [ -n "$SNS_ROUTE" ]; then
  warn "旧 /sns/* ルート '${SNS_ROUTE}' を削除します..."
  az afd route delete \
    --resource-group "$AZURE_RG" \
    --profile-name "$AZURE_FD_PROFILE" \
    --endpoint-name "$AZURE_AFD_ENDPOINT" \
    --route-name "$SNS_ROUTE" \
    --yes
  ok "旧 /sns/* ルートを削除しました"
else
  ok "/sns/* の旧ルートは存在しません"
fi

log "[Azure] AFD キャッシュパージ"
az afd endpoint purge \
  --resource-group "$AZURE_RG" \
  --profile-name "$AZURE_FD_PROFILE" \
  --endpoint-name "$AZURE_AFD_ENDPOINT" \
  --content-paths "/*"
ok "Azure Front Door キャッシュをパージしました"

echo ""

# ===========================================
# [GCP] URL Map の /sns/* pathRule 削除
# ===========================================
log "[GCP] staging URL Map をエクスポート"
gcloud compute url-maps export "$GCP_URLMAP" \
  --destination /tmp/urlmap-staging.yaml \
  --quiet

# /sns/* pathRule の有無を確認
if grep -qE '^\s*-\s*/sns/' /tmp/urlmap-staging.yaml 2>/dev/null; then
  warn "/sns/* パスルールが存在します。削除します..."
  python3 - << 'PYEOF'
import yaml

with open('/tmp/urlmap-staging.yaml', 'r') as f:
    data = yaml.safe_load(f)

removed_total = 0
for pm in data.get('pathMatchers', []):
    original = pm.get('pathRules', [])
    filtered = [
        r for r in original
        if not any('/sns' in p for p in (r.get('paths') or []))
    ]
    removed_total += len(original) - len(filtered)
    pm['pathRules'] = filtered

with open('/tmp/urlmap-staging-fixed.yaml', 'w') as f:
    yaml.dump(data, f, default_flow_style=False, allow_unicode=True)

print(f"  /sns/* pathRule を {removed_total} 件削除しました")
PYEOF

  gcloud compute url-maps import "$GCP_URLMAP" \
    --source /tmp/urlmap-staging-fixed.yaml \
    --quiet
  ok "GCP staging URL Map から /sns/* pathRule を削除しました"
else
  ok "/sns/* の pathRule は存在しません"
fi

log "[GCP] CDN キャッシュ無効化 (/sns/*)"
gcloud compute url-maps invalidate-cdn-cache "$GCP_URLMAP" \
  --path "/sns/*" \
  --global \
  --async
ok "GCP CDN キャッシュ無効化リクエストを発行"

echo ""

# ===========================================
# Pulumi up (Azure / GCP)
# ===========================================
log "[Azure] pulumi up --stack staging を実行"
cd "${REPO_ROOT}/infrastructure/pulumi/azure"
pulumi stack select staging
pulumi up --stack staging --yes
ok "Azure staging stack を適用"
cd "${REPO_ROOT}"

log "[GCP] pulumi up --stack staging を実行"
cd "${REPO_ROOT}/infrastructure/pulumi/gcp"
pulumi stack select staging
pulumi up --stack staging --yes
ok "GCP staging stack を適用"
cd "${REPO_ROOT}"

echo ""

# ===========================================
# 動作確認
# ===========================================
log "=== 動作確認 (CDN 反映まで 1-2 分待機) ==="
sleep 30

check_react() {
  local LABEL="$1"
  local URL="$2"
  local HTTP_STATUS
  HTTP_STATUS=$(curl -s -o /dev/null -w "%{http_code}" --max-time 20 "${URL}/sns/")
  if [ "$HTTP_STATUS" == "200" ]; then
    local BODY
    BODY=$(curl -s --max-time 20 "${URL}/sns/")
    if echo "$BODY" | grep -qiE 'frontend_react|vite|/sns/assets/'; then
      ok "${LABEL} /sns/ → React SPA (HTTP ${HTTP_STATUS})"
    else
      warn "${LABEL} /sns/ → HTTP ${HTTP_STATUS} だが React SPA マーカーが見つからない"
      echo "     先頭200文字: $(echo "$BODY" | head -c 200)"
    fi
  else
    warn "${LABEL} /sns/ → HTTP ${HTTP_STATUS} (CDN 反映待ちの可能性あり)"
  fi
}

check_react "AWS staging"   "$STAGING_S3_CF_URL"
check_react "Azure staging" "$AZURE_AFD_URL"
check_react "GCP staging"   "http://${GCP_STAGING_IP}"

echo ""
echo "============================================="
echo " staging CDN ルーティング修正完了"
echo " React SPA が表示されない場合は数分後に再確認してください"
echo " 詳細: docs/REACT_SPA_MIGRATION_REPORT.md"
echo "============================================="
