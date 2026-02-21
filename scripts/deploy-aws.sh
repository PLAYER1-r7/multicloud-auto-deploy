#!/bin/bash
# ========================================
# Script Name: deploy-aws.sh
# Description: AWS Terraform Deployment Script
# Author: PLAYER1-r7
# Created: 2025-12-15
# Last Modified: 2026-02-15
# Version: 1.0.0
# ========================================
#
# Usage: ./scripts/deploy-aws.sh [environment]
#
# Description:
#   Deploys infrastructure to AWS using Terraform.
#   Creates Lambda, API Gateway, DynamoDB, and S3 resources.
#
# Parameters:
#   $1 - Environment name (default: staging)
#
# Deployment Components:
#   - Lambda Functions (Python 3.12)
#   - API Gateway v2 (HTTP)
#   - DynamoDB (PAY_PER_REQUEST)
#   - S3 Static Website
#   - CloudFront Distribution
#
# Prerequisites:
#   - Terraform 1.5+ installed
#   - AWS CLI configured
#   - Valid AWS credentials
#
# Exit Codes:
#   0 - Deployment successful
#   1 - Deployment failed
#
# ========================================

set -e

ENVIRONMENT=${1:-staging}
PROJECT_NAME="multicloud-auto-deploy"
AWS_REGION="ap-northeast-1"

echo "🚀 Starting AWS deployment for environment: $ENVIRONMENT"

# 色付き出力
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# 1. フロントエンドのビルド
echo -e "${BLUE}📦 Building frontend...${NC}"
cd services/frontend
npm install
VITE_API_URL="https://api-${ENVIRONMENT}.example.com" npm run build
cd ../..

# 2. バックエンドのパッケージング
echo -e "${BLUE}📦 Packaging backend...${NC}"
cd services/backend
pip install -r requirements.txt -t package/
cp -r src/* package/
cd package && zip -r ../lambda.zip . && cd ..
cd ../..

# 3. Terraformによるインフラデプロイ
echo -e "${BLUE}🏗️  Deploying infrastructure with Terraform...${NC}"
cd infrastructure/terraform/aws

# Lambda用のプレースホルダーZIPを作成（初回のみ）
if [ ! -f lambda_placeholder.zip ]; then
    echo "print('placeholder')" > lambda_placeholder.py
    zip lambda_placeholder.zip lambda_placeholder.py
    rm lambda_placeholder.py
fi

terraform init
terraform plan -var="environment=$ENVIRONMENT" -var="project_name=$PROJECT_NAME" -out=tfplan
terraform apply -auto-approve tfplan

# Terraformの出力を取得
S3_BUCKET=$(terraform output -raw frontend_bucket_name)
CLOUDFRONT_ID=$(terraform output -raw cloudfront_distribution_id)
LAMBDA_FUNCTION=$(terraform output -raw lambda_function_name)
API_ENDPOINT=$(terraform output -raw api_endpoint)

cd ../../..

# 4. フロントエンドをS3にデプロイ
echo -e "${BLUE}☁️  Deploying frontend to S3...${NC}"
aws s3 sync services/frontend/dist/ "s3://${S3_BUCKET}/" --delete

# 5. CloudFrontキャッシュを無効化
echo -e "${BLUE}🔄 Invalidating CloudFront cache...${NC}"
aws cloudfront create-invalidation --distribution-id "$CLOUDFRONT_ID" --paths "/*"

# 6. Lambda関数を更新
echo -e "${BLUE}⚡ Updating Lambda function...${NC}"
aws lambda update-function-code \
    --function-name "$LAMBDA_FUNCTION" \
    --zip-file fileb://services/backend/lambda.zip

echo -e "${GREEN}✅ Deployment completed successfully!${NC}"
echo -e "${GREEN}🌐 Frontend URL: https://$(aws cloudfront get-distribution --id $CLOUDFRONT_ID --query 'Distribution.DomainName' --output text)${NC}"
echo -e "${GREEN}🔗 API Endpoint: $API_ENDPOINT${NC}"
