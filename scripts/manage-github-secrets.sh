#!/bin/bash
# ========================================
# Script Name: manage-github-secrets.sh
# Description: GitHub Secrets Management Tool (Unified)
# Author: PLAYER1-r7
# Created: 2026-01-10
# Last Modified: 2026-02-15
# Version: 2.0.0
# ========================================
#
# Usage: ./scripts/manage-github-secrets.sh [--auto|--guide]
#
# Description:
#   Manages GitHub Actions secrets for multi-cloud deployment.
#   Supports both automated setup and guided manual setup modes.
#
# Modes:
#   --guide (default) - Display manual setup commands
#   --auto            - Automatically set secrets from local environment
#
# Supported Secrets:
#   AWS: AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY
#   Azure: AZURE_CREDENTIALS, AZURE_*
#   GCP: GCP_CREDENTIALS, GCP_PROJECT_ID
#
# Prerequisites:
#   - GitHub CLI (gh) installed and authenticated
#   - Repository write access
#   - For --auto mode: Local environment variables set
#
# Examples:
#   ./scripts/manage-github-secrets.sh          # Guide mode
#   ./scripts/manage-github-secrets.sh --auto   # Auto setup
#
# Exit Codes:
#   0 - Success
#   1 - Missing prerequisites or setup failed
#
# ========================================

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# デフォルトモード
MODE="guide"

# Usage
usage() {
    cat << EOF
Usage: $0 [OPTIONS]

GitHub Secrets管理スクリプト

OPTIONS:
    --mode=auto         自動設定モード (gh CLI使用)
    --mode=guide        ガイド表示モード (デフォルト)
    --check-local       ローカル環境変数チェック
    -h, --help          このヘルプを表示

EXAMPLES:
    # ガイドを表示
    $0
    
    # 自動設定
    $0 --mode=auto
    
    # 環境変数確認
    $0 --check-local

EOF
    exit 0
}

# Parse arguments
CHECK_LOCAL=false
for arg in "$@"; do
    case $arg in
        --mode=auto|--auto)
            MODE="auto"
            shift
            ;;
        --mode=guide|--guide)
            MODE="guide"
            shift
            ;;
        --check-local)
            CHECK_LOCAL=true
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

echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}🔐 GitHub Secrets 管理スクリプト${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

# ローカル環境変数チェック
if [ "$CHECK_LOCAL" = true ]; then
    echo -e "${BLUE}ローカル環境変数チェック${NC}"
    echo "======================================"
    echo ""
    
    check_env() {
        local var_name=$1
        if [ -n "${!var_name}" ]; then
            echo -e "${GREEN}✓${NC} $var_name: 設定済み"
        else
            echo -e "${RED}✗${NC} $var_name: 未設定"
        fi
    }
    
    echo "AWS:"
    check_env "AWS_ACCESS_KEY_ID"
    check_env "AWS_SECRET_ACCESS_KEY"
    echo ""
    
    echo "Azure:"
    check_env "ARM_CLIENT_ID"
    check_env "ARM_CLIENT_SECRET"
    check_env "ARM_SUBSCRIPTION_ID"
    check_env "ARM_TENANT_ID"
    echo ""
    
    echo "GCP:"
    check_env "GCP_PROJECT_ID"
    check_env "GOOGLE_APPLICATION_CREDENTIALS"
    echo ""
    
    exit 0
fi

# リポジトリ取得
REPO=""
if command -v gh &> /dev/null && gh auth status &> /dev/null 2>&1; then
    REPO=$(gh repo view --json nameWithOwner -q .nameWithOwner 2>/dev/null || echo "")
fi

if [ -z "$REPO" ]; then
    REPO="PLAYER1-r7/multicloud-auto-deploy"
    echo -e "${YELLOW}⚠️  リポジトリを自動検出できませんでした${NC}"
    echo -e "デフォルト: ${CYAN}$REPO${NC}"
else
    echo -e "${GREEN}✅ Repository: $REPO${NC}"
fi
echo ""

# ガイドモード用関数
print_secret_section() {
    local title=$1
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BLUE}$title${NC}"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
}

print_secret() {
    local name=$1
    local description=$2
    local example=$3
    
    echo -e "${GREEN}Secret Name:${NC} ${YELLOW}$name${NC}"
    echo -e "${GREEN}説明:${NC} $description"
    if [ -n "$example" ]; then
        echo -e "${GREEN}例:${NC} $example"
    fi
    echo ""
}

# 自動設定モード用関数
set_secret() {
    local secret_name=$1
    local secret_value=$2
    
    if [ -z "$secret_value" ] || [ "$secret_value" = "null" ]; then
        echo -e "${YELLOW}⊘ $secret_name: スキップ（値が空）${NC}"
        return 1
    fi
    
    echo -n "Setting $secret_name... "
    if echo "$secret_value" | gh secret set "$secret_name" --repo "$REPO" 2>/dev/null; then
        echo -e "${GREEN}✅${NC}"
        return 0
    else
        echo -e "${RED}❌ 失敗${NC}"
        return 1
    fi
}

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# ガイドモード
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
if [ "$MODE" = "guide" ]; then
    echo -e "${CYAN}GitHub Secrets 設定ガイド${NC}"
    echo ""
    echo "以下の情報をGitHub Repositoryに設定してください："
    echo "Settings → Secrets and variables → Actions → New repository secret"
    echo ""
    
    # AWS Secrets
    print_secret_section "AWS Secrets"
    
    print_secret \
        "AWS_ACCESS_KEY_ID" \
        "AWSアクセスキーID" \
        "AKIAIOSFODNN7EXAMPLE"
    
    print_secret \
        "AWS_SECRET_ACCESS_KEY" \
        "AWSシークレットアクセスキー" \
        "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"
    
    echo -e "${CYAN}取得方法:${NC}"
    echo "aws iam create-access-key --user-name YOUR_USER"
    echo ""
    echo -e "${CYAN}必要な権限:${NC}"
    echo "- AmazonAPIGatewayAdministrator"
    echo "- AWSLambda_FullAccess"
    echo "- AmazonS3FullAccess"
    echo "- CloudFrontFullAccess"
    echo "- AmazonDynamoDBFullAccess"
    echo ""
    echo "---"
    echo ""
    
    echo -e "${CYAN}💡 Tip:${NC}"
    echo "このガイドを保存: ./scripts/manage-github-secrets.sh > SECRETS_GUIDE.txt"
    echo "自動設定: ./scripts/manage-github-secrets.sh --mode=auto"
    echo ""
    
    exit 0
fi

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 自動設定モード
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
if [ "$MODE" = "auto" ]; then
    echo -e "${CYAN}GitHub Secrets 自動設定モード${NC}"
    echo ""
    
    # gh CLI チェック
    if ! command -v gh &> /dev/null; then
        echo -e "${RED}❌ GitHub CLI (gh) がインストールされていません${NC}"
        echo "インストール手順: https://cli.github.com/"
        exit 1
    fi
    
    # 認証チェック
    if ! gh auth status &> /dev/null; then
        echo -e "${YELLOW}⚠️  GitHub CLI にログインしていません${NC}"
        echo "以下のコマンドでログインしてください:"
        echo "  gh auth login"
        exit 1
    fi
    
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BLUE}Azure Secrets${NC}"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    
    # Azure CLI チェック
    if ! command -v az &> /dev/null; then
        echo -e "${YELLOW}⚠️  Azure CLI がインストールされていません。スキップします。${NC}"
    else
        ACR_NAME=$(az acr list --query "[0].name" -o tsv 2>/dev/null || echo "")
        ACR_LOGIN_SERVER=$(az acr list --query "[0].loginServer" -o tsv 2>/dev/null || echo "")
        RESOURCE_GROUP=$(az group list --query "[?contains(name, 'multicloud') || contains(name, 'mcad')].name | [0]" -o tsv 2>/dev/null || echo "")
        
        echo ""
        echo -e "${BLUE}検出された Azure 環境:${NC}"
        echo "  ACR: ${ACR_LOGIN_SERVER:-未検出}"
        echo "  Resource Group: ${RESOURCE_GROUP:-未検出}"
        echo ""
        
        set_secret "AZURE_CONTAINER_REGISTRY" "$ACR_LOGIN_SERVER"
        set_secret "AZURE_RESOURCE_GROUP" "$RESOURCE_GROUP"
        
        if [ -n "$ACR_NAME" ]; then
            ACR_USERNAME=$(az acr credential show --name "$ACR_NAME" --query "username" -o tsv 2>/dev/null || echo "")
            ACR_PASSWORD=$(az acr credential show --name "$ACR_NAME" --query "passwords[0].value" -o tsv 2>/dev/null || echo "")
            set_secret "AZURE_CONTAINER_REGISTRY_USERNAME" "$ACR_USERNAME"
            set_secret "AZURE_CONTAINER_REGISTRY_PASSWORD" "$ACR_PASSWORD"
        fi
    fi
    
    echo ""
    echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${GREEN}✅ セットアップ完了！${NC}"
    echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
    echo -e "${BLUE}設定されたSecretsを確認:${NC}"
    echo "  gh secret list --repo $REPO"
    echo ""
    
    exit 0
fi
