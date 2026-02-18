#!/usr/bin/env bash
# =============================================================================
# デプロイパイプライン結果レポート生成
# 使用方法: bash scripts/generate-pipeline-report.sh TIMESTAMP LOCAL_LOG STAGING_LOG PROD_LOG
# =============================================================================

set -uo pipefail

TIMESTAMP="${1:-$(date '+%Y%m%d_%H%M%S')}"
LOCAL_LOG="${2:-/tmp/pipeline-local.log}"
STAGING_LOG="${3:-/tmp/pipeline-staging.log}"
PROD_LOG="${4:-/tmp/pipeline-production.log}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
REPORT_FILE="$PROJECT_ROOT/docs/DEPLOY_PIPELINE_REPORT_${TIMESTAMP}.md"

RUN_DATE=$(echo "$TIMESTAMP" | sed 's/_/ /' | awk '{print $1}')
RUN_TIME=$(echo "$TIMESTAMP" | awk -F_ '{print $2}' | sed 's/../&:/g' | sed 's/:$//')

extract_summary() {
    local logfile="$1"
    if [[ -f "$logfile" ]]; then
        local pass fail skip
        pass=$(grep -c "✅ PASS" "$logfile" 2>/dev/null || echo 0)
        fail=$(grep -c "❌ FAIL" "$logfile" 2>/dev/null || echo 0)
        skip=$(grep -c "⏭ SKIP\|⚠️  WARN" "$logfile" 2>/dev/null || echo 0)
        echo "PASS: $pass / FAIL: $fail / WARN+SKIP: $skip"
    else
        echo "ログなし"
    fi
}

extract_test_lines() {
    local logfile="$1"
    if [[ -f "$logfile" ]]; then
        grep -E "✅ PASS|❌ FAIL|⏭ SKIP|⚠️  WARN|ℹ  " "$logfile" 2>/dev/null \
            | sed 's/^  //' \
            | head -60
    else
        echo "(ログファイルなし: $logfile)"
    fi
}

LOCAL_SUMMARY=$(extract_summary "$LOCAL_LOG")
STAGING_SUMMARY=$(extract_summary "$STAGING_LOG")
PROD_SUMMARY=$(extract_summary "$PROD_LOG")

OVERALL_STATUS="✅ 全テストPASS"
if grep -q "❌ FAIL" "$LOCAL_LOG" "$STAGING_LOG" "$PROD_LOG" 2>/dev/null; then
    OVERALL_STATUS="❌ 一部テストFAIL"
fi

# GitHub Actions の最近の実行を取得
get_actions_status() {
    local branch="$1" workflow="$2"
    gh run list \
        --workflow="$workflow" \
        --branch="$branch" \
        --limit=1 \
        --json status,conclusion,databaseId,createdAt,headSha \
        --jq '.[0] | "\(.conclusion // .status) (run_id: \(.databaseId), sha: \(.headSha[:7]))"' \
        2>/dev/null || echo "取得不可"
}

AWS_STAGING_STATUS=$(get_actions_status "develop" "deploy-aws.yml")
AWS_PROD_STATUS=$(get_actions_status "main" "deploy-aws.yml")
GCP_STAGING_STATUS=$(get_actions_status "develop" "deploy-gcp.yml")
AZURE_STAGING_STATUS=$(get_actions_status "develop" "deploy-azure.yml")

COMMIT_SHA=$(cd "$PROJECT_ROOT" && git rev-parse --short HEAD 2>/dev/null || echo "N/A")
DEVELOP_SHA=$(cd "$PROJECT_ROOT" && git rev-parse --short develop 2>/dev/null || echo "N/A")
MAIN_SHA=$(cd "$PROJECT_ROOT" && git rev-parse --short main 2>/dev/null || echo "N/A")

cat > "$REPORT_FILE" << EOF
# デプロイパイプライン実行レポート

**実行日時**: ${RUN_DATE} ${RUN_TIME}  
**総合結果**: ${OVERALL_STATUS}  
**担当者**: 自動実行 (deploy-pipeline.sh)

---

## パイプライン概要

\`\`\`
local → develop (push) → [GitHub Actions staging deploy] → staging test
       → main (merge+push) → [GitHub Actions production deploy] → production test
\`\`\`

---

## 各ステップ結果

| ステップ | 内容 | 結果 |
|---------|------|------|
| STEP 1 | ローカルテスト | $LOCAL_SUMMARY |
| STEP 2 | develop ブランチ push | commit: $DEVELOP_SHA |
| STEP 3 | GitHub Actions (staging) 待機 | AWS: $AWS_STAGING_STATUS |
| STEP 4 | staging 環境テスト | $STAGING_SUMMARY |
| STEP 5 | main ブランチ merge + push | commit: $MAIN_SHA |
| STEP 6 | GitHub Actions (production) 待機 | AWS: $AWS_PROD_STATUS |
| STEP 7 | production 環境テスト | $PROD_SUMMARY |

---

## GitHub Actions ステータス

| ワークフロー | ブランチ | ステータス |
|------------|--------|---------|
| deploy-aws.yml | develop (staging) | $AWS_STAGING_STATUS |
| deploy-aws.yml | main (production) | $AWS_PROD_STATUS |
| deploy-gcp.yml | develop (staging) | $GCP_STAGING_STATUS |
| deploy-azure.yml | develop (staging) | $AZURE_STAGING_STATUS |

---

## エンドポイント (staging)

| クラウド | API | Frontend CDN |
|---------|-----|-------------|
| AWS | https://z42qmqdqac.execute-api.ap-northeast-1.amazonaws.com | https://d1tf3uumcm4bo1.cloudfront.net |
| Azure | https://multicloud-auto-deploy-staging-func-d8a2guhfere0etcq.japaneast-01.azurewebsites.net/api/HttpTrigger | https://multicloud-frontend-f9cvamfnauexasd8.z01.azurefd.net |
| GCP | https://multicloud-auto-deploy-staging-api-son5b3ml7a-an.a.run.app | http://34.117.111.182 |

---

## ローカルテスト詳細

\`\`\`
$(extract_test_lines "$LOCAL_LOG")
\`\`\`

---

## Staging テスト詳細

\`\`\`
$(extract_test_lines "$STAGING_LOG")
\`\`\`

---

## Production テスト詳細

\`\`\`
$(extract_test_lines "$PROD_LOG")
\`\`\`

---

## git ログ (直近5件)

\`\`\`
$(cd "$PROJECT_ROOT" && git log --oneline -5 2>/dev/null || echo "N/A")
\`\`\`

---

*このレポートは scripts/generate-pipeline-report.sh により自動生成されました。*
EOF

echo "📝 レポートを生成しました: $REPORT_FILE"
