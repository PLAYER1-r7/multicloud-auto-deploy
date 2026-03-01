#!/bin/bash
# ========================================
# Script Name: deploy-azure.sh
# Description: Azure Deployment Script
# Author: PLAYER1-r7
# Created: 2025-12-15
# Last Modified: 2026-02-15
# Version: 1.0.0
# ========================================
#
# Usage: ./scripts/deploy-azure.sh [environment]
#
# Description:
#   Deploys infrastructure to Azure.
#   Creates Functions, Cosmos DB, Blob Storage, and Front Door.
#
# Parameters:
#   $1 - Environment name (default: staging)
#
# Deployment Components:
#   - Azure Functions (Flex Consumption, Python 3.13)
#   - Cosmos DB (Serverless)
#   - Blob Storage ($web container)
#   - Azure Front Door (Standard)
#
# Prerequisites:
#   - Azure CLI installed and authenticated
#   - Resource group created
#   - Valid Azure subscription
#
# Exit Codes:
#   0 - Deployment successful
#   1 - Deployment failed
#
# ========================================

set -e

ENVIRONMENT=${1:-staging}
PROJECT_NAME="multicloud-auto-deploy"
AZURE_REGION="eastus"

echo "🚀 Starting Azure deployment for environment: $ENVIRONMENT"

GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m'

# 1. フロントエンドのビルド
echo -e "${BLUE}📦 Building frontend...${NC}"
cd services/frontend
npm install
VITE_API_URL="https://api-${ENVIRONMENT}.azurewebsites.net" npm run build
cd ../..

# 2. Azureリソースグループの作成
echo -e "${BLUE}🏗️  Creating Azure resources...${NC}"
RESOURCE_GROUP="${PROJECT_NAME}-${ENVIRONMENT}-rg"
STORAGE_ACCOUNT="${PROJECT_NAME}${ENVIRONMENT}st"
FUNCTION_APP="${PROJECT_NAME}-${ENVIRONMENT}-api"

az group create --name "$RESOURCE_GROUP" --location "$AZURE_REGION"

# 3. ストレージアカウント（フロントエンド用）
az storage account create \
    --name "$STORAGE_ACCOUNT" \
    --resource-group "$RESOURCE_GROUP" \
    --location "$AZURE_REGION" \
    --sku Standard_LRS \
    --kind StorageV2 \
    --allow-blob-public-access true

# 静的Webサイトを有効化
az storage blob service-properties update \
    --account-name "$STORAGE_ACCOUNT" \
    --static-website \
    --index-document index.html \
    --404-document index.html

# 4. フロントエンドをデプロイ
echo -e "${BLUE}☁️  Deploying frontend...${NC}"
az storage blob upload-batch \
    --account-name "$STORAGE_ACCOUNT" \
    --destination '$web' \
    --source services/frontend/dist/ \
    --overwrite

# 5. Azure Functionsをデプロイ
echo -e "${BLUE}⚡ Deploying backend...${NC}"
az functionapp create \
    --resource-group "$RESOURCE_GROUP" \
    --name "$FUNCTION_APP" \
    --storage-account "$STORAGE_ACCOUNT" \
    --runtime python \
    --runtime-version 3.13 \
    --functions-version 4 \
    --os-type Linux

cd services/backend
func azure functionapp publish "$FUNCTION_APP"
cd ../..

FRONTEND_URL=$(az storage account show \
    --name "$STORAGE_ACCOUNT" \
    --resource-group "$RESOURCE_GROUP" \
    --query "primaryEndpoints.web" \
    --output tsv)

echo -e "${GREEN}✅ Azure deployment completed!${NC}"
echo -e "${GREEN}🌐 Frontend URL: $FRONTEND_URL${NC}"
echo -e "${GREEN}🔗 API Endpoint: https://${FUNCTION_APP}.azurewebsites.net${NC}"
