#!/bin/bash
# ========================================
# Script Name: monitor-cicd.sh
# Description: CI/CD Pipeline Status Monitor
# Author: PLAYER1-r7
# Created: 2026-01-15
# Last Modified: 2026-02-15
# Version: 1.0.0
# ========================================
#
# Usage: ./scripts/monitor-cicd.sh [--workflow=NAME]
#
# Description:
#   Continuously monitors GitHub Actions workflow execution status.
#   Displays real-time updates with color-coded status indicators.
#
# Options:
#   --workflow=NAME  - Monitor specific workflow only
#   -h, --help       - Show help message
#
# Prerequisites:
#   - GitHub CLI (gh) installed and authenticated
#   - Repository access
#
# Status Indicators:
#   - Green: Success
#   - Red: Failure
#   - Yellow: In Progress
#   - Blue: Queued
#
# Exit Codes:
#   0 - Normal exit
#   1 - Missing prerequisites
#
# ========================================

set -e

# カラー定義
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

# デフォルト値
WORKFLOW_FILTER=""
SHOW_HELP=false

# Usage
usage() {
    cat << EOF
Usage: $0 [OPTIONS]

CI/CD パイプライン監視スクリプト

OPTIONS:
    --workflow=NAME     特定のワークフローのみ監視
    -h, --help          このヘルプを表示

EXAMPLES:
    # 全ワークフロー監視
    $0
    
    # 特定ワークフロー監視
    $0 --workflow=deploy-aws.yml

EOF
    exit 0
}

# Parse arguments
for arg in "$@"; do
    case $arg in
        --workflow=*)
            WORKFLOW_FILTER="${arg#*=}"
            shift
            ;;
        -h|--help)
            usage
            ;;
        *)
            echo -e "${RED}Unknown option: $arg${NC}"
            usage
            ;;
    esac
done

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

# ワークフロー指定の表示
if [ -n "$WORKFLOW_FILTER" ]; then
    echo -e "${CYAN}対象ワークフロー: $WORKFLOW_FILTER${NC}"
    echo ""
fi

# ===========================================
# 1. ワークフロー一覧
# ===========================================
echo -e "${YELLOW}=== ワークフロー一覧 ===${NC}"
echo ""

if [ -n "$WORKFLOW_FILTER" ]; then
    gh workflow list | grep "$WORKFLOW_FILTER" || echo "ワークフロー '$WORKFLOW_FILTER' が見つかりません"
else
    gh workflow list
fi

echo ""

# ===========================================
# 2. 最近の実行履歴
# ===========================================
echo -e "${YELLOW}=== 最近の実行履歴 ===${NC}"
echo ""

if [ -n "$WORKFLOW_FILTER" ]; then
    gh run list --workflow="$WORKFLOW_FILTER" --limit 10
else
    gh run list --limit 10
fi

echo ""

# ===========================================
# 3. 失敗した実行の詳細
# ===========================================
echo -e "${YELLOW}=== 失敗した実行 ===${NC}"
echo ""

if [ -n "$WORKFLOW_FILTER" ]; then
    FAILED_RUNS=$(gh run list --workflow="$WORKFLOW_FILTER" --status failure --limit 5 --json databaseId,displayTitle,workflowName,conclusion,createdAt)
else
    FAILED_RUNS=$(gh run list --status failure --limit 5 --json databaseId,displayTitle,workflowName,conclusion,createdAt)
fi

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

if [ -n "$WORKFLOW_FILTER" ]; then
    RUNNING_RUNS=$(gh run list --workflow="$WORKFLOW_FILTER" --status in_progress --limit 10 --json databaseId,displayTitle,workflowName,status,createdAt)
else
    RUNNING_RUNS=$(gh run list --status in_progress --limit 10 --json databaseId,displayTitle,workflowName,status,createdAt)
fi

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
