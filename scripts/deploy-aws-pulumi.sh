#!/bin/bash
set -e

# ===========================================
# AWS Pulumi Deployment Script
# Python Full Stack Edition
# ===========================================

echo "🚀 Deploying Python Full Stack to AWS (Pulumi)"
echo "==============================================="

# Configuration
ENVIRONMENT="${1:-staging}"
AWS_REGION="${AWS_REGION:-ap-northeast-1}"
PROJECT_NAME="simple-sns"
GIT_COMMIT=$(git rev-parse --short HEAD 2>/dev/null || echo "unknown")

echo "Environment: $ENVIRONMENT"
echo "Region: $AWS_REGION"
echo "Git Commit: $GIT_COMMIT"
echo ""

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

# ===========================================
# 1. Prerequisites Check
# ===========================================

echo -e "${BLUE}🔍 Checking prerequisites...${NC}"

# Check AWS CLI
if ! command -v aws &> /dev/null; then
    echo "❌ Error: AWS CLI is not installed"
    exit 1
fi

# Check Pulumi
if ! command -v pulumi &> /dev/null; then
    echo "❌ Error: Pulumi is not installed"
    echo "Install from: https://www.pulumi.com/docs/get-started/install/"
    exit 1
fi

# Check Docker
if ! command -v docker &> /dev/null; then
    echo "❌ Error: Docker is not installed"
    exit 1
fi

# Verify AWS credentials
aws sts get-caller-identity &> /dev/null || {
    echo "❌ Error: AWS credentials not configured"
    exit 1
}

AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
echo "✅ AWS Account: $AWS_ACCOUNT_ID"
echo ""

# ===========================================
# 2. Deploy Infrastructure with Pulumi
# ===========================================

echo -e "${BLUE}📦 Step 1: Deploying infrastructure...${NC}"
cd infrastructure/pulumi/aws/simple-sns

# Setup Python venv
if [ ! -d "venv" ]; then
    python3 -m venv venv
fi
source venv/bin/activate
pip install -q -r requirements.txt

# Select or create stack
pulumi stack select $ENVIRONMENT 2>/dev/null || pulumi stack init $ENVIRONMENT
pulumi config set aws:region $AWS_REGION --non-interactive

# Deploy
pulumi up --yes

# Get outputs
API_URL=$(pulumi stack output api_url)
API_ECR=$(pulumi stack output api_ecr_repository)
FRONTEND_ECR=$(pulumi stack output frontend_ecr_repository)
MESSAGES_TABLE=$(pulumi stack output messages_table_name)
IMAGES_BUCKET=$(pulumi stack output images_bucket_name)

echo -e "${GREEN}✅ Infrastructure deployed${NC}"
cd ../../../../

# ===========================================
# 3. Build and Push Docker Images
# ===========================================

echo ""
echo -e "${BLUE}🐳 Step 2: Building and pushing Docker images...${NC}"

ECR_REGISTRY="$AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com"

# Login to ECR
aws ecr get-login-password --region $AWS_REGION | \
  docker login --username AWS --password-stdin $ECR_REGISTRY

# Build and push API
echo "Building API image..."
cd services/api
docker build -t mcad-api:$GIT_COMMIT -t mcad-api:latest .
docker tag mcad-api:latest $ECR_REGISTRY/$PROJECT_NAME-api-$ENVIRONMENT:latest
docker tag mcad-api:latest $ECR_REGISTRY/$PROJECT_NAME-api-$ENVIRONMENT:$GIT_COMMIT
docker push $ECR_REGISTRY/$PROJECT_NAME-api-$ENVIRONMENT:latest
docker push $ECR_REGISTRY/$PROJECT_NAME-api-$ENVIRONMENT:$GIT_COMMIT
echo -e "${GREEN}✅ API image pushed${NC}"

# Build and push Frontend
echo ""
echo "Building Frontend image..."
cd ../frontend_reflex
docker build -t mcad-frontend:$GIT_COMMIT -t mcad-frontend:latest .
docker tag mcad-frontend:latest $ECR_REGISTRY/$PROJECT_NAME-frontend-$ENVIRONMENT:latest
docker tag mcad-frontend:latest $ECR_REGISTRY/$PROJECT_NAME-frontend-$ENVIRONMENT:$GIT_COMMIT
docker push $ECR_REGISTRY/$PROJECT_NAME-frontend-$ENVIRONMENT:latest
docker push $ECR_REGISTRY/$PROJECT_NAME-frontend-$ENVIRONMENT:$GIT_COMMIT
echo -e "${GREEN}✅ Frontend image pushed${NC}"

cd ../../

# ===========================================
# 4. Health Check
# ===========================================

echo ""
echo -e "${BLUE}🏥 Step 3: Running health check...${NC}"
sleep 5

if curl -f -s "$API_URL/health" > /dev/null; then
    echo -e "${GREEN}✅ API is healthy${NC}"
else
    echo -e "${YELLOW}⚠️  API health check failed (may take a few minutes to start)${NC}"
fi

# ===========================================
# 5. Summary
# ===========================================

echo ""
echo "==============================================="
echo -e "${GREEN}🎉 Deployment Complete!${NC}"
echo "==============================================="
echo ""
echo "📋 Deployment Info:"
echo "  Environment: $ENVIRONMENT"
echo "  Region: $AWS_REGION"
echo "  Commit: $GIT_COMMIT"
echo "  Account: $AWS_ACCOUNT_ID"
echo ""
echo "🔗 Endpoints:"
echo "  API: $API_URL"
echo "  Health: $API_URL/health"
echo "  Docs: $API_URL/docs"
echo ""
echo "📦 Resources:"
echo "  DynamoDB: $MESSAGES_TABLE"
echo "  S3 Bucket: $IMAGES_BUCKET"
echo "  API ECR: $ECR_REGISTRY/$PROJECT_NAME-api-$ENVIRONMENT:$GIT_COMMIT"
echo "  Frontend ECR: $ECR_REGISTRY/$PROJECT_NAME-frontend-$ENVIRONMENT:$GIT_COMMIT"
echo ""
echo -e "${YELLOW}📚 Next Steps:${NC}"
echo "  1. Deploy frontend to App Runner:"
echo "     See docs/PRODUCTION_DEPLOYMENT.md"
echo ""
echo "  2. Test API:"
echo "     curl $API_URL/health"
echo "     curl $API_URL/api/messages/"
echo ""
echo "  3. View logs:"
echo "     aws logs tail /aws/lambda/$PROJECT_NAME-api-$ENVIRONMENT --follow"
echo ""
echo "  4. Monitor in AWS Console:"
echo "     https://console.aws.amazon.com/lambda/home?region=$AWS_REGION"
echo ""
