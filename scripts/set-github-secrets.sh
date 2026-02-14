#!/bin/bash

# GitHub Secrets自動設定スクリプト
# このスクリプトは現在の環境からGitHub Secretsを自動的に設定します

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🔐 GitHub Secrets 自動設定スクリプト${NC}"
echo "======================================"
echo ""

# Check if gh CLI is installed
if ! command -v gh &> /dev/null; then
    echo -e "${RED}❌ GitHub CLI (gh) がインストールされていません${NC}"
    echo "インストール手順: https://cli.github.com/"
    exit 1
fi

# Check if authenticated
if ! gh auth status &> /dev/null; then
    echo -e "${YELLOW}⚠️  GitHub CLI にログインしていません${NC}"
    echo "以下のコマンドでログインしてください:"
    echo "  gh auth login"
    exit 1
fi

# Get repository
REPO=$(gh repo view --json nameWithOwner -q .nameWithOwner 2>/dev/null || echo "")
if [ -z "$REPO" ]; then
    echo -e "${RED}❌ リポジトリが見つかりません${NC}"
    echo "このスクリプトはGitリポジトリ内で実行してください"
    exit 1
fi

echo -e "${GREEN}✅ Repository: $REPO${NC}"
echo ""

# Function to set secret
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

echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}Azure Secrets${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

# Check Azure CLI
if ! command -v az &> /dev/null; then
    echo -e "${YELLOW}⚠️  Azure CLI がインストールされていません。Azure Secrets をスキップします。${NC}"
else
    # Azure Container Registry
    ACR_NAME=$(az acr list --query "[0].name" -o tsv 2>/dev/null || echo "")
    ACR_LOGIN_SERVER=$(az acr list --query "[0].loginServer" -o tsv 2>/dev/null || echo "")

    # Azure Resource Group
    RESOURCE_GROUP=$(az group list --query "[?contains(name, 'multicloud') || contains(name, 'mcad')].name | [0]" -o tsv 2>/dev/null || echo "")

    # Azure Container Apps
    CONTAINER_APP_API=$(az containerapp list --query "[?contains(name, 'api')].name | [0]" -o tsv 2>/dev/null || echo "")
    CONTAINER_APP_FRONTEND=$(az containerapp list --query "[?contains(name, 'frontend')].name | [0]" -o tsv 2>/dev/null || echo "")

    echo ""
    echo -e "${BLUE}検出された Azure 環境:${NC}"
    echo "  ACR: ${ACR_LOGIN_SERVER:-未検出}"
    echo "  Resource Group: ${RESOURCE_GROUP:-未検出}"
    echo "  Container App API: ${CONTAINER_APP_API:-未検出}"
    echo "  Container App Frontend: ${CONTAINER_APP_FRONTEND:-未検出}"
    echo ""

    # Set Azure Secrets
    set_secret "AZURE_CONTAINER_REGISTRY" "$ACR_LOGIN_SERVER"
    
    if [ -n "$ACR_NAME" ]; then
        ACR_USERNAME=$(az acr credential show --name "$ACR_NAME" --query "username" -o tsv 2>/dev/null || echo "")
        ACR_PASSWORD=$(az acr credential show --name "$ACR_NAME" --query "passwords[0].value" -o tsv 2>/dev/null || echo "")
        set_secret "AZURE_CONTAINER_REGISTRY_USERNAME" "$ACR_USERNAME"
        set_secret "AZURE_CONTAINER_REGISTRY_PASSWORD" "$ACR_PASSWORD"
    fi
    
    set_secret "AZURE_RESOURCE_GROUP" "$RESOURCE_GROUP"
    set_secret "AZURE_CONTAINER_APP_API" "$CONTAINER_APP_API"
    set_secret "AZURE_CONTAINER_APP_FRONTEND" "$CONTAINER_APP_FRONTEND"
    
    # AZURE_CREDENTIALS
    echo ""
    echo -e "${YELLOW}⚠️  AZURE_CREDENTIALS は手動で設定する必要があります${NC}"
    echo "以下のコマンドを実行してください:"
    echo ""
    SUBSCRIPTION_ID=$(az account show --query id -o tsv 2>/dev/null || echo "YOUR_SUBSCRIPTION_ID")
    echo -e "${GREEN}# Service Principal を作成${NC}"
    echo "az ad sp create-for-rbac \\"
    echo "  --name \"github-actions-mcad\" \\"
    echo "  --role contributor \\"
    echo "  --scopes /subscriptions/$SUBSCRIPTION_ID/resourceGroups/$RESOURCE_GROUP \\"
    echo "  --sdk-auth"
    echo ""
    echo -e "${GREEN}# 出力されたJSONをSecretに設定${NC}"
    echo "gh secret set AZURE_CREDENTIALS --repo $REPO"
    echo "(JSONをペーストしてEnter、Ctrl+Dで終了)"
    echo ""
fi

echo ""
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}GCP Secrets${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

# Check gcloud CLI
if ! command -v gcloud &> /dev/null; then
    echo -e "${YELLOW}⚠️  gcloud CLI がインストールされていません。GCP Secrets をスキップします。${NC}"
else
    # GCP Project
    GCP_PROJECT=$(gcloud config get-value project 2>/dev/null || echo "")

    # GCP Artifact Registry
    GCP_REPO=$(gcloud artifacts repositories list --format="value(name)" 2>/dev/null | head -1 || echo "")

    # GCP Cloud Run
    CLOUD_RUN_API=$(gcloud run services list --format="value(metadata.name)" --region asia-northeast1 2>/dev/null | grep -i api | head -1 || echo "")
    CLOUD_RUN_FRONTEND=$(gcloud run services list --format="value(metadata.name)" --region asia-northeast1 2>/dev/null | grep -i frontend | head -1 || echo "")

    echo ""
    echo -e "${BLUE}検出された GCP 環境:${NC}"
    echo "  Project ID: ${GCP_PROJECT:-未検出}"
    echo "  Artifact Registry: ${GCP_REPO:-未検出}"
    echo "  Cloud Run API: ${CLOUD_RUN_API:-未検出}"
    echo "  Cloud Run Frontend: ${CLOUD_RUN_FRONTEND:-未検出}"
    echo ""

    # Set GCP Secrets
    set_secret "GCP_PROJECT_ID" "$GCP_PROJECT"
    set_secret "GCP_ARTIFACT_REGISTRY_REPO" "$GCP_REPO"
    set_secret "GCP_CLOUD_RUN_API" "$CLOUD_RUN_API"
    set_secret "GCP_CLOUD_RUN_FRONTEND" "$CLOUD_RUN_FRONTEND"
    
    # GCP_CREDENTIALS
    echo ""
    echo -e "${YELLOW}⚠️  GCP_CREDENTIALS は手動で設定する必要があります${NC}"
    echo ""
    
    # Check if service account exists
    SA_EMAIL="github-actions-mcad@$GCP_PROJECT.iam.gserviceaccount.com"
    if gcloud iam service-accounts describe $SA_EMAIL &>/dev/null; then
        echo -e "${GREEN}✅ Service Account が存在します: $SA_EMAIL${NC}"
        echo ""
        echo "既存のキーを使用するか、新しいキーを作成してください:"
        echo ""
        echo -e "${GREEN}# 新しいキーを作成${NC}"
        echo "gcloud iam service-accounts keys create github-actions-key.json \\"
        echo "  --iam-account=$SA_EMAIL"
        echo ""
        echo -e "${GREEN}# Secretに設定${NC}"
        echo "gh secret set GCP_CREDENTIALS --repo $REPO < github-actions-key.json"
        echo ""
    else
        echo -e "${YELLOW}Service Account が存在しません。以下の手順で作成してください:${NC}"
        echo ""
        echo -e "${GREEN}# 1. Service Account を作成${NC}"
        echo "gcloud iam service-accounts create github-actions-mcad \\"
        echo "  --display-name=\"GitHub Actions MCAD\" \\"
        echo "  --project=$GCP_PROJECT"
        echo ""
        echo -e "${GREEN}# 2. 必要な権限を付与${NC}"
        echo "gcloud projects add-iam-policy-binding $GCP_PROJECT \\"
        echo "  --member=\"serviceAccount:$SA_EMAIL\" \\"
        echo "  --role=\"roles/run.admin\""
        echo ""
        echo "gcloud projects add-iam-policy-binding $GCP_PROJECT \\"
        echo "  --member=\"serviceAccount:$SA_EMAIL\" \\"
        echo "  --role=\"roles/artifactregistry.writer\""
        echo ""
        echo "gcloud projects add-iam-policy-binding $GCP_PROJECT \\"
        echo "  --member=\"serviceAccount:$SA_EMAIL\" \\"
        echo "  --role=\"roles/iam.serviceAccountUser\""
        echo ""
        echo -e "${GREEN}# 3. サービスアカウントキーを作成${NC}"
        echo "gcloud iam service-accounts keys create github-actions-key.json \\"
        echo "  --iam-account=$SA_EMAIL"
        echo ""
        echo -e "${GREEN}# 4. Secretに設定${NC}"
        echo "gh secret set GCP_CREDENTIALS --repo $REPO < github-actions-key.json"
        echo ""
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
echo -e "${BLUE}次のステップ:${NC}"
echo "1. 上記の手動設定が必要な Secrets を設定"
echo "2. GitHub Actions ワークフローをテスト:"
echo "   https://github.com/$REPO/actions/workflows/deploy-multicloud.yml"
echo ""
