#!/bin/bash
# ========================================
# Script Name: deploy-gcp.sh
# Description: GCP Deployment Script
# Author: PLAYER1-r7
# Created: 2025-12-15
# Last Modified: 2026-02-15
# Version: 1.0.0
# ========================================
#
# Usage: ./scripts/deploy-gcp.sh [environment] [project_id]
#
# Description:
#   Deploys infrastructure to GCP.
#   Creates Cloud Run, Firestore, Cloud Storage, and Cloud CDN.
#
# Parameters:
#   $1 - Environment name (default: staging)
#   $2 - GCP Project ID (required for first run)
#
# Deployment Components:
#   - Cloud Run (Containerized FastAPI)
#   - Firestore (Native Mode)
#   - Cloud Storage (Static Website)
#   - Cloud CDN (via Load Balancer)
#
# Prerequisites:
#   - gcloud CLI installed and authenticated
#   - Valid GCP project with billing enabled
#   - Required APIs enabled
#
# Exit Codes:
#   0 - Deployment successful
#   1 - Deployment failed
#
# ========================================

set -e

ENVIRONMENT=${1:-staging}
GCP_PROJECT_ID=${2:-your-gcp-project-id}
GCP_REGION="us-central1"
PROJECT_NAME="multicloud-auto-deploy"

echo "🚀 Starting GCP deployment for environment: $ENVIRONMENT"

GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m'

# 1. プロジェクトを設定
gcloud config set project "$GCP_PROJECT_ID"

# 2. フロントエンドのビルド
echo -e "${BLUE}📦 Building frontend...${NC}"
cd services/frontend
npm install
VITE_API_URL="https://${GCP_REGION}-${GCP_PROJECT_ID}.cloudfunctions.net/api" npm run build
cd ../..

# 3. Cloud Storageバケットの作成
echo -e "${BLUE}☁️  Creating Cloud Storage bucket...${NC}"
BUCKET_NAME="${PROJECT_NAME}-${ENVIRONMENT}-frontend"
gsutil mb -p "$GCP_PROJECT_ID" -l "$GCP_REGION" "gs://${BUCKET_NAME}/" || true
gsutil web set -m index.html -e index.html "gs://${BUCKET_NAME}/"
gsutil iam ch allUsers:objectViewer "gs://${BUCKET_NAME}/"

# 4. フロントエンドをデプロイ
echo -e "${BLUE}📤 Deploying frontend...${NC}"
gsutil -m rsync -r -d services/frontend/dist/ "gs://${BUCKET_NAME}/"

# 5. Cloud Functionsをデプロイ
echo -e "${BLUE}⚡ Deploying backend...${NC}"
cd services/backend
gcloud functions deploy "${PROJECT_NAME}-${ENVIRONMENT}-api" \
    --gen2 \
    --runtime=python311 \
    --region="$GCP_REGION" \
    --source=. \
    --entry-point=handler \
    --trigger-http \
    --allow-unauthenticated
cd ../..

# 6. FirestoreまたはCloud SQL（オプション）
echo -e "${BLUE}📊 Setting up database...${NC}"
gcloud firestore databases create --location="$GCP_REGION" || echo "Firestore already exists"

FUNCTION_URL=$(gcloud functions describe "${PROJECT_NAME}-${ENVIRONMENT}-api" \
    --region="$GCP_REGION" \
    --format="value(serviceConfig.uri)")

echo -e "${GREEN}✅ GCP deployment completed!${NC}"
echo -e "${GREEN}🌐 Frontend URL: https://storage.googleapis.com/${BUCKET_NAME}/index.html${NC}"
echo -e "${GREEN}🔗 API Endpoint: $FUNCTION_URL${NC}"
