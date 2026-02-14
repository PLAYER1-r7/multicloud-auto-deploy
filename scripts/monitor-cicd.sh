#!/bin/bash

# CI/CD パイプライン状態監視スクリプト
# GitHub Actionsの実行状態を継続的に監視

set -e

# カラー定義
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}CI/CD パイプライン監視${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# gh CLIの確認
if ! command -v gh &> /dev/null; then
    echo -e "${RED}エラー: GitHub CLI (gh) がインストールされていません${NC}"
    exit 1
fi

# GitHub認証確認
if ! gh auth status &> /dev/null; then
    echo -e "${RED}エラー: GitHub認証が必要です${NC}"
    gh auth login
    exit 1
fi

# リポジトリ情報取得
REPO=$(gh repo view --json nameWithOwner -q .nameWithOwner 2>/dev/null)
if [ -z "$REPO" ]; then
    echo -e "${RED}エラー: GitHubリポジトリが見つかりません${NC}"
    exit 1
fi

echo "リポジトリ: $REPO"
echo ""

# ===========================================
# 1. ワークフロー一覧
# ===========================================
echo -e "${YELLOW}=== ワークフロー一覧 ===${NC}"
echo ""

gh workflow list

echo ""

# ===========================================
# 2. 最近の実行履歴
# ===========================================
echo -e "${YELLOW}=== 最近の実行履歴 ===${NC}"
echo ""

gh run list --limit 10

echo ""

# ===========================================
# 3. 失敗した実行の詳細
# ===========================================
echo -e "${YELLOW}=== 失敗した実行 ===${NC}"
echo ""

FAILED_RUNS=$(gh run list --status failure --limit 5 --json databaseId,displayTitle,workflowName,conclusion,createdAt)

if [ "$FAILED_RUNS" = "[]" ]; then
    echo -e "${GREEN}✅ 最近の失敗した実行はありません${NC}"
else
    echo "$FAILED_RUNS" | jq -r '.[] | "🔴 \(.workflowName) - \(.displayTitle) (\(.createdAt))"'
fi

echo ""

# ===========================================
# 4. 実行中のワークフロー
# ===========================================
echo -e "${YELLOW}=== 実行中のワークフロー ===${NC}"
echo ""

RUNNING_RUNS=$(gh run list --status in_progress --limit 10 --json databaseId,displayTitle,workflowName,status,createdAt)

if [ "$RUNNING_RUNS" = "[]" ]; then
    echo "実行中のワークフローはありません"
else
    echo "$RUNNING_RUNS" | jq -r '.[] | "🔵 \(.workflowName) - \(.displayTitle) (\(.status))"'
    
    echo ""
    echo -e "${BLUE}リアルタイム監視を開始しますか？ (y/N)${NC}"
    read -r response
    if [[ "$response" =~ ^[Yy]$ ]]; then
        RUN_ID=$(echo "$RUNNING_RUNS" | jq -r '.[0].databaseId')
        gh run watch "$RUN_ID"
    fi
fi

echo ""

# ===========================================
# 5. 成功率統計
# ===========================================
echo -e "${YELLOW}=== 成功率統計（直近20実行） ===${NC}"
echo ""

ALL_RUNS=$(gh run list --limit 20 --json conclusion)
TOTAL=$(echo "$ALL_RUNS" | jq length)
SUCCESS=$(echo "$ALL_RUNS" | jq '[.[] | select(.conclusion == "success")] | length')
FAILURE=$(echo "$ALL_RUNS" | jq '[.[] | select(.conclusion == "failure")] | length')
CANCELLED=$(echo "$ALL_RUNS" | jq '[.[] | select(.conclusion == "cancelled")] | length')

if [ "$TOTAL" -gt 0 ]; then
    SUCCESS_RATE=$(awk "BEGIN {printf \"%.1f\", ($SUCCESS/$TOTAL)*100}")
    
    echo "総実行数: $TOTAL"
    echo -e "${GREEN}成功: $SUCCESS${NC}"
    echo -e "${RED}失敗: $FAILURE${NC}"
    echo -e "${YELLOW}キャンセル: $CANCELLED${NC}"
    echo ""
    echo "成功率: $SUCCESS_RATE%"
    
    if (( $(echo "$SUCCESS_RATE >= 90" | bc -l) )); then
        echo -e "${GREEN}✅ パイプラインの健全性: 良好${NC}"
    elif (( $(echo "$SUCCESS_RATE >= 70" | bc -l) )); then
        echo -e "${YELLOW}⚠️  パイプラインの健全性: 注意${NC}"
    else
        echo -e "${RED}❌ パイプラインの健全性: 要対応${NC}"
    fi
else
    echo "実行履歴がありません"
fi

echo ""

# ===========================================
# 6. ワークフロー別統計
# ===========================================
echo -e "${YELLOW}=== ワークフロー別統計 ===${NC}"
echo ""

WORKFLOWS=("deploy-aws.yml" "deploy-azure.yml" "deploy-gcp.yml" "deploy-multicloud.yml")

for workflow in "${WORKFLOWS[@]}"; do
    echo "【$workflow】"
    
    WORKFLOW_RUNS=$(gh run list --workflow="$workflow" --limit 10 --json conclusion 2>/dev/null)
    
    if [ -n "$WORKFLOW_RUNS" ] && [ "$WORKFLOW_RUNS" != "[]" ]; then
        W_TOTAL=$(echo "$WORKFLOW_RUNS" | jq length)
        W_SUCCESS=$(echo "$WORKFLOW_RUNS" | jq '[.[] | select(.conclusion == "success")] | length')
        W_FAILURE=$(echo "$WORKFLOW_RUNS" | jq '[.[] | select(.conclusion == "failure")] | length')
        
        if [ "$W_TOTAL" -gt 0 ]; then
            W_SUCCESS_RATE=$(awk "BEGIN {printf \"%.1f\", ($W_SUCCESS/$W_TOTAL)*100}")
            echo "  直近10実行: 成功 $W_SUCCESS / 失敗 $W_FAILURE (成功率: $W_SUCCESS_RATE%)"
        else
            echo "  実行履歴なし"
        fi
    else
        echo "  実行履歴なし"
    fi
    echo ""
done

# ===========================================
# 7. 便利なコマンド
# ===========================================
echo -e "${YELLOW}=== 便利なコマンド ===${NC}"
echo ""
echo "最新の実行を監視:"
echo "  gh run watch"
echo ""
echo "最新の実行ログを表示:"
echo "  gh run view --log"
echo ""
echo "ブラウザで確認:"
echo "  gh run view --web"
echo ""
echo "特定のワークフローを実行:"
echo "  gh workflow run deploy-aws.yml -f environment=staging"
echo ""
echo "実行をキャンセル:"
echo "  gh run cancel <run-id>"
echo ""
echo "失敗した実行を再実行:"
echo "  gh run rerun <run-id>"
echo ""
