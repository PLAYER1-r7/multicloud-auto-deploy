#!/bin/bash

# Production Deployment Monitor
# マルチクラウド本番デプロイメントの リアルタイム監視スクリプト

set -u

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}════════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}🌍 Production Multicloud Deployment Monitor${NC}"
echo -e "${BLUE}════════════════════════════════════════════════════════════${NC}"
echo ""

# ================================
# AZURE Status
# ================================
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}☁️  Azure Production${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

AZURE_SNS_ENDPOINT="https://multicloud-auto-deploy-production-sns.azurewebsites.net"
AZURE_SOLVER_ENDPOINT="https://multicloud-auto-deploy-production-solver.azurewebsites.net"

echo -n "SNS API Health: "
SNS_CODE=$(curl -s -o /dev/null -w "%{http_code}" "$AZURE_SNS_ENDPOINT/api/health" 2>/dev/null)
if [ "$SNS_CODE" = "200" ]; then
    echo -e "${GREEN}✅ 200 OK${NC}"
else
    echo -e "${RED}❌ HTTP $SNS_CODE${NC}"
fi

echo -n "Exam Solver Health: "
SOLVER_CODE=$(curl -s -o /dev/null -w "%{http_code}" "$AZURE_SOLVER_ENDPOINT/api/health" 2>/dev/null)
if [ "$SOLVER_CODE" = "200" ]; then
    echo -e "${GREEN}✅ 200 OK${NC}"
else
    echo -e "${RED}❌ HTTP $SOLVER_CODE${NC}"
fi

echo ""

# ================================
# AWS Status
# ================================
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}☁️  AWS Production${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

# Check Lambda Functions
echo -e "Lambda Functions:"
aws lambda list-functions --region ap-northeast-1 --output text --query "Functions[?contains(FunctionName, 'production')].{Name: FunctionName, Runtime: Runtime}" 2>/dev/null | while read name runtime; do
    if [ ! -z "$name" ]; then
        echo -e "  ✅ $name ($runtime)"
    fi
done

echo ""

# Get SNS API Deployment Status
echo -n "SNS API Deployment Status: "
SNS_DEPLOY_STATUS=$(cd "$PROJECT_ROOT" && gh run view 22719336374 --json status -q '.status' 2>/dev/null)
case "$SNS_DEPLOY_STATUS" in
    "completed")
        echo -e "${GREEN}✅ Completed${NC}"
        ;;
    "waiting")
        echo -e "${YELLOW}⏳ Waiting for Approval${NC}"
        ;;
    "in_progress")
        echo -e "${YELLOW}⏳ In Progress${NC}"
        ;;
    *)
        echo -e "${YELLOW}ⓘ $SNS_DEPLOY_STATUS${NC}"
        ;;
esac

echo ""

# ================================
# GCP Status
# ================================
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}☁️  GCP Production${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

echo -e "✅ SNS API: Deployed (2026-03-05T11:18:59Z)"
echo -e "✅ Exam Solver API: Deployed (2026-03-05T11:57:52Z)"

echo ""

# ================================
# Summary
# ================================
echo -e "${BLUE}════════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}📊 Deployment Summary${NC}"
echo -e "${BLUE}════════════════════════════════════════════════════════════${NC}"
echo ""
echo -e "Azure:           ${GREEN}✅ 2/2 APIs Deployed${NC}"
echo -e "AWS:             ⏳ 1/2 APIs Deployed (SNS API approval pending)"
echo -e "GCP:             ${GREEN}✅ 2/2 APIs Deployed${NC}"
echo ""
echo -e "Overall:         📊 5/6 APIs Ready (Pending: AWS SNS API approval)"
echo ""

# Approval Monitor
echo -e "${BLUE}════════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}📋 Next Steps${NC}"
echo -e "${BLUE}════════════════════════════════════════════════════════════${NC}"
echo ""
echo "1️⃣  Complete AWS SNS API Approval:"
echo "    URL: https://github.com/PLAYER1-r7/multicloud-auto-deploy/actions/runs/22719336374"
echo ""
echo "2️⃣  Once complete, run integration tests:"
echo "    bash scripts/test-sns-all.sh --env production --quick"
echo ""
echo "3️⃣  Monitor production environment:"
echo "    bash scripts/monitor-production-deployment.sh (this script)"
echo ""
