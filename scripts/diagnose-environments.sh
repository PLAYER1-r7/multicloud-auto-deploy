#!/bin/bash
# Multi-Cloud Environment Diagnostics Script
# Usage: ./scripts/diagnose-environments.sh

set -e

echo "============================================"
echo "Multi-Cloud Environment Diagnostics"
echo "============================================"
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# AWS Staging
echo -e "${YELLOW}🟧 AWS Staging Environment${NC}"
echo "-------------------------------------------"
echo "API Endpoint:"
AWS_API_RESPONSE=$(curl -s -w "\nHTTP_STATUS:%{http_code}" https://z42qmqdqac.execute-api.ap-northeast-1.amazonaws.com/)
AWS_API_BODY=$(echo "$AWS_API_RESPONSE" | sed -e 's/HTTP_STATUS\:.*//g')
AWS_API_STATUS=$(echo "$AWS_API_RESPONSE" | tr -d '\n' | sed -e 's/.*HTTP_STATUS://')

echo "$AWS_API_BODY" | head -5
if [ "$AWS_API_STATUS" = "200" ]; then
    echo -e "${GREEN}HTTP Status: $AWS_API_STATUS ✅${NC}"
else
    echo -e "${RED}HTTP Status: $AWS_API_STATUS ❌${NC}"
fi

echo ""
echo "Frontend CloudFront:"
AWS_FRONTEND_STATUS=$(curl -s -o /dev/null -w "%{http_code}" https://d1tf3uumcm4bo1.cloudfront.net/)
if [ "$AWS_FRONTEND_STATUS" = "200" ]; then
    echo -e "${GREEN}HTTP Status: $AWS_FRONTEND_STATUS ✅${NC}"
else
    echo -e "${RED}HTTP Status: $AWS_FRONTEND_STATUS ❌${NC}"
fi

echo ""
echo "Lambda Configuration:"
if command -v aws &> /dev/null; then
    aws lambda get-function \
      --function-name multicloud-auto-deploy-staging-api \
      --region ap-northeast-1 \
      --query 'Configuration.{Runtime:Runtime,Handler:Handler,CodeSize:CodeSize,Layers:Layers}' 2>/dev/null || echo "  (AWS CLI credentials not configured)"
else
    echo "  (AWS CLI not installed)"
fi

echo ""
echo "Lambda Recent Errors:"
if command -v aws &> /dev/null; then
    aws logs tail /aws/lambda/multicloud-auto-deploy-staging-api \
      --region ap-northeast-1 \
      --since 10m \
      --format short \
      --filter-pattern "ERROR" 2>/dev/null | tail -5 || echo "  (No recent errors or AWS CLI not configured)"
else
    echo "  (AWS CLI not installed)"
fi

echo ""
echo ""

# Azure Staging
echo -e "${BLUE}🟦 Azure Staging Environment${NC}"
echo "-------------------------------------------"
echo "API Endpoint:"
AZURE_API_RESPONSE=$(curl -s -w "\nHTTP_STATUS:%{http_code}" https://multicloud-auto-deploy-staging-func-d8a2guhfere0etcq.japaneast-01.azurewebsites.net/api/HttpTrigger/)
AZURE_API_BODY=$(echo "$AZURE_API_RESPONSE" | sed -e 's/HTTP_STATUS\:.*//g')
AZURE_API_STATUS=$(echo "$AZURE_API_RESPONSE" | tr -d '\n' | sed -e 's/.*HTTP_STATUS://')

echo "$AZURE_API_BODY" | head -5
if [ "$AZURE_API_STATUS" = "200" ]; then
    echo -e "${GREEN}HTTP Status: $AZURE_API_STATUS ✅${NC}"
else
    echo -e "${RED}HTTP Status: $AZURE_API_STATUS ❌${NC}"
fi

echo ""
echo "Frontend Azure Front Door:"
AZURE_FRONTEND_STATUS=$(curl -s -o /dev/null -w "%{http_code}" https://multicloud-frontend-f9cvamfnauexasd8.z01.azurefd.net/)
if [ "$AZURE_FRONTEND_STATUS" = "200" ]; then
    echo -e "${GREEN}HTTP Status: $AZURE_FRONTEND_STATUS ✅${NC}"
else
    echo -e "${RED}HTTP Status: $AZURE_FRONTEND_STATUS ❌${NC}"
fi

echo ""
echo ""

# GCP Staging
echo -e "${GREEN}🟩 GCP Staging Environment${NC}"
echo "-------------------------------------------"
echo "API Endpoint:"
GCP_API_RESPONSE=$(curl -s -w "\nHTTP_STATUS:%{http_code}" https://multicloud-auto-deploy-staging-api-son5b3ml7a-an.a.run.app/)
GCP_API_BODY=$(echo "$GCP_API_RESPONSE" | sed -e 's/HTTP_STATUS\:.*//g')
GCP_API_STATUS=$(echo "$GCP_API_RESPONSE" | tr -d '\n' | sed -e 's/.*HTTP_STATUS://')

echo "$GCP_API_BODY" | head -5
if [ "$GCP_API_STATUS" = "200" ]; then
    echo -e "${GREEN}HTTP Status: $GCP_API_STATUS ✅${NC}"
else
    echo -e "${RED}HTTP Status: $GCP_API_STATUS ❌${NC}"
fi

echo ""
echo "Frontend Load Balancer:"
GCP_FRONTEND_STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://34.117.111.182/)
if [ "$GCP_FRONTEND_STATUS" = "200" ]; then
    echo -e "${GREEN}HTTP Status: $GCP_FRONTEND_STATUS ✅${NC}"
else
    echo -e "${RED}HTTP Status: $GCP_FRONTEND_STATUS ❌${NC}"
fi

echo ""
echo ""

# CI/CD Status
echo "🔄 CI/CD Workflow Status (Latest 5)"
echo "-------------------------------------------"
if command -v jq &> /dev/null; then
    curl -s "https://api.github.com/repos/PLAYER1-r7/multicloud-auto-deploy/actions/runs?per_page=5" | \
      jq -r '.workflow_runs[] | "\(.created_at | .[0:19]) - \(.name) [\(.head_branch)]: \(.conclusion // "running")"' | \
      while IFS= read -r line; do
        if [[ $line == *"success"* ]]; then
            echo -e "${GREEN}$line ✅${NC}"
        elif [[ $line == *"failure"* ]]; then
            echo -e "${RED}$line ❌${NC}"
        elif [[ $line == *"running"* ]] || [[ $line == *"in_progress"* ]]; then
            echo -e "${YELLOW}$line ⏳${NC}"
        else
            echo "$line"
        fi
      done
else
    echo "  (jq not installed - cannot parse JSON)"
fi

echo ""
echo "============================================"
echo "Diagnostics Complete"
echo "============================================"
echo ""

# Summary
echo "📊 Summary:"
echo "-------------------------------------------"
TOTAL_CHECKS=6
PASSED_CHECKS=0

[ "$AWS_API_STATUS" = "200" ] && ((PASSED_CHECKS++))
[ "$AWS_FRONTEND_STATUS" = "200" ] && ((PASSED_CHECKS++))
[ "$AZURE_API_STATUS" = "200" ] && ((PASSED_CHECKS++))
[ "$AZURE_FRONTEND_STATUS" = "200" ] && ((PASSED_CHECKS++))
[ "$GCP_API_STATUS" = "200" ] && ((PASSED_CHECKS++))
[ "$GCP_FRONTEND_STATUS" = "200" ] && ((PASSED_CHECKS++))

echo -e "Checks Passed: ${GREEN}$PASSED_CHECKS${NC} / $TOTAL_CHECKS"

if [ $PASSED_CHECKS -eq $TOTAL_CHECKS ]; then
    echo -e "${GREEN}✅ All systems operational!${NC}"
elif [ $PASSED_CHECKS -ge 4 ]; then
    echo -e "${YELLOW}⚠️  Some systems have issues${NC}"
else
    echo -e "${RED}❌ Multiple systems are down${NC}"
fi

echo ""
echo "For detailed troubleshooting, see:"
echo "  docs/ENVIRONMENT_DIAGNOSTICS.md"
echo "  docs/ENVIRONMENT_STATUS.md"
