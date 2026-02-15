#!/bin/bash
# ========================================
# Script Name: deploy-frontend-aws.sh
# Description: AWS Frontend Deployment Script
# Author: PLAYER1-r7
# Created: 2026-01-20
# Last Modified: 2026-02-15
# Version: 1.0.0
# ========================================
#
# Usage: ./scripts/deploy-frontend-aws.sh [staging|production]
#
# Description:
#   Deploys React frontend to AWS S3 + CloudFront.
#   Builds, uploads, and invalidates cache.
#
# Parameters:
#   $1 - Environment name (default: staging)
#
# Deployment Steps:
#   1. Build React application (Vite)
#   2. Upload to S3 bucket
#   3. Invalidate CloudFront cache
#   4. Verify deployment
#
# Prerequisites:
#   - Node.js 18+ installed
#   - AWS CLI configured
#   - S3 bucket created
#   - CloudFront distribution created
#
# Exit Codes:
#   0 - Deployment successful
#   1 - Deployment failed
#
# ========================================

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

ENVIRONMENT=${1:-staging}

echo -e "${BLUE}🚀 Deploying React Frontend to AWS${NC}"
echo -e "${BLUE}Environment: ${ENVIRONMENT}${NC}"
echo "=================================="
echo ""

# Configuration based on environment
if [ "$ENVIRONMENT" = "production" ]; then
  S3_BUCKET="multicloud-auto-deploy-production-frontend"
  CLOUDFRONT_ID="YOUR_PROD_CLOUDFRONT_ID"
  API_URL="https://mcad-production-api-son5b3ml7a-an.a.run.app"
elif [ "$ENVIRONMENT" = "staging" ]; then
  S3_BUCKET="multicloud-auto-deploy-staging-frontend"
  CLOUDFRONT_ID="E2GDU7Y7UGDV3S"
  API_URL="https://mcad-staging-api-son5b3ml7a-an.a.run.app"
else
  echo -e "${RED}❌ Invalid environment: $ENVIRONMENT${NC}"
  echo "Usage: $0 [staging|production]"
  exit 1
fi

# Navigate to frontend directory
cd "$(dirname "$0")/../services/frontend_react"

# Create .env file with API URL
echo -e "${YELLOW}📝 Setting API URL: $API_URL${NC}"
echo "VITE_API_URL=$API_URL" > .env

# Build React app
echo -e "${YELLOW}🔨 Building React app...${NC}"
npm run build

if [ ! -d "dist" ]; then
  echo -e "${RED}❌ Build failed: dist/ directory not found${NC}"
  exit 1
fi

echo -e "${GREEN}✅ Build completed!${NC}"
echo ""

# Deploy to S3
echo -e "${YELLOW}📦 Deploying to S3: ${S3_BUCKET}${NC}"

# Sync assets with long cache
aws s3 sync dist/ s3://${S3_BUCKET}/ \
  --delete \
  --cache-control "public,max-age=31536000,immutable" \
  --exclude "index.html" \
  --exclude "*.html"

# Upload HTML files with no cache
aws s3 cp dist/index.html s3://${S3_BUCKET}/index.html \
  --cache-control "public,max-age=0,must-revalidate"

echo -e "${GREEN}✅ Deployed to S3!${NC}"
echo ""

# Invalidate CloudFront cache
echo -e "${YELLOW}🔄 Invalidating CloudFront cache...${NC}"
INVALIDATION_ID=$(aws cloudfront create-invalidation \
  --distribution-id "${CLOUDFRONT_ID}" \
  --paths "/*" \
  --query 'Invalidation.Id' \
  --output text)

echo -e "Invalidation ID: ${INVALIDATION_ID}"
echo -e "${GREEN}✅ Cache invalidation started!${NC}"
echo ""

# Get CloudFront domain
CLOUDFRONT_DOMAIN=$(aws cloudfront get-distribution \
  --id "${CLOUDFRONT_ID}" \
  --query 'Distribution.DomainName' \
  --output text)

# Display results
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}✅ Deployment Complete!${NC}"
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo -e "${BLUE}🌐 Website URLs:${NC}"
echo -e "  CloudFront: ${GREEN}https://${CLOUDFRONT_DOMAIN}${NC}"
echo -e "  S3 Website: ${GREEN}http://${S3_BUCKET}.s3-website-ap-northeast-1.amazonaws.com${NC}"
echo ""
echo -e "${BLUE}API Endpoint:${NC}"
echo -e "  ${API_URL}"
echo ""
echo -e "${YELLOW}Note: CloudFront cache invalidation takes 1-3 minutes to propagate globally.${NC}"
echo ""
