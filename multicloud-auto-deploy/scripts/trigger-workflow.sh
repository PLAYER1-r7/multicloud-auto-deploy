#!/bin/bash
# ========================================
# Script Name: trigger-workflow.sh
# Description: GitHub Actions Workflow Trigger
# Author: PLAYER1-r7
# Created: 2026-01-15
# Last Modified: 2026-02-15
# Version: 1.0.0
# ========================================
#
# Usage: ./scripts/trigger-workflow.sh <workflow> [environment]
#
# Description:
#   Manually triggers GitHub Actions workflows and monitors execution.
#
# Parameters:
#   workflow     - Workflow name: aws|azure|gcp|multicloud
#   environment  - Target environment: staging (default)|production
#
# Examples:
#   ./scripts/trigger-workflow.sh aws
#   ./scripts/trigger-workflow.sh azure production
#   ./scripts/trigger-workflow.sh multicloud staging
#
# Prerequisites:
#   - GitHub CLI (gh) installed and authenticated
#   - Repository write access
#   - Valid workflow files in .github/workflows/
#
# Exit Codes:
#   0 - Workflow triggered successfully
#   1 - Invalid arguments or trigger failed
#
# ========================================

set -e

# カラー定義
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}GitHub Actions ワークフロートリガー${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# 引数確認
if [ $# -eq 0 ]; then
    echo "使用方法: $0 <workflow> [environment]"
    echo ""
    echo "ワークフロー:"
    echo "  aws        - AWS デプロイ"
    echo "  azure      - Azure デプロイ"
    echo "  gcp        - GCP デプロイ"
    echo "  multicloud - マルチクラウド デプロイ"
    echo ""
    echo "環境 (optional):"
    echo "  staging    - ステージング環境（デフォルト）"
    echo "  production - 本番環境"
    echo ""
    echo "例:"
    echo "  $0 aws staging"
    echo "  $0 azure"
    echo "  $0 multicloud production"
    exit 1
fi

WORKFLOW=$1
ENVIRONMENT=${2:-staging}

# ワークフローファイル名の決定
case $WORKFLOW in
    aws)
        WORKFLOW_FILE="deploy-aws.yml"
        ;;
    azure)
        WORKFLOW_FILE="deploy-azure.yml"
        ;;
    gcp)
        WORKFLOW_FILE="deploy-gcp.yml"
        ;;
    multicloud)
        WORKFLOW_FILE="deploy-multicloud.yml"
        ;;
    *)
        echo -e "${RED}エラー: 不明なワークフロー: $WORKFLOW${NC}"
        exit 1
        ;;
esac

echo "ワークフロー: $WORKFLOW_FILE"
echo "環境: $ENVIRONMENT"
echo ""

# gh CLIの確認
if ! command -v gh &> /dev/null; then
    echo -e "${RED}エラー: GitHub CLI (gh) がインストールされていません${NC}"
    echo ""
    echo "インストール方法:"
    echo "  https://cli.github.com/"
    echo ""
    exit 1
fi

# GitHub認証確認
if ! gh auth status &> /dev/null; then
    echo -e "${YELLOW}GitHub認証が必要です${NC}"
    echo ""
    gh auth login
fi

# リポジトリ情報取得
REPO=$(gh repo view --json nameWithOwner -q .nameWithOwner)
echo "リポジトリ: $REPO"
echo ""

# ワークフロー実行
echo -e "${YELLOW}ワークフローを実行中...${NC}"
gh workflow run "$WORKFLOW_FILE" -f environment="$ENVIRONMENT"

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ ワークフロー実行をトリガーしました${NC}"
    echo ""
    
    # 少し待機
    sleep 3
    
    # 最新の実行状況を表示
    echo -e "${BLUE}最新の実行状況:${NC}"
    gh run list --workflow="$WORKFLOW_FILE" --limit 5
    
    echo ""
    echo -e "${YELLOW}実行状況をリアルタイムで確認:${NC}"
    echo "  gh run watch"
    echo ""
    echo -e "${YELLOW}実行ログを確認:${NC}"
    echo "  gh run view --log"
    echo ""
    echo -e "${YELLOW}ブラウザで確認:${NC}"
    echo "  gh run view --web"
else
    echo -e "${RED}❌ ワークフロー実行のトリガーに失敗しました${NC}"
    exit 1
fi
