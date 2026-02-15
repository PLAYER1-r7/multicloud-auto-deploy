#!/bin/bash
# ========================================
# Script Name: test-deployments.sh
# Description: Multi-Cloud Deployment Integration Test
# Author: PLAYER1-r7
# Created: 2026-01-15
# Last Modified: 2026-02-15
# Version: 1.0.0
# ========================================
#
# Usage: ./scripts/test-deployments.sh
#
# Description:
#   Tests all cloud deployments (API and Frontend) for connectivity
#   and basic functionality across AWS, Azure, and GCP.
#
# Test Targets:
#   AWS:
#     - API: Lambda + API Gateway
#     - Frontend: S3 + CloudFront
#   Azure:
#     - API: Functions + Flex Consumption
#     - Frontend: Blob Storage + Front Door
#   GCP:
#     - API: Cloud Run
#     - Frontend: Cloud Storage + Load Balancer
#
# Prerequisites:
#   - curl command available
#   - Active deployments on all clouds
#
# Exit Codes:
#   0 - All deployments responding
#   1 - One or more deployments failed
#
# ========================================

set -e

echo "🧪 Multi-Cloud Deployment Testing"
echo "=================================="

# 色付き出力
GREEN='\033[0;32m'
RED='\033[0;31m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

# テスト結果カウンター
TOTAL_TESTS=0
PASSED_TESTS=0
FAILED_TESTS=0

# テスト関数
test_endpoint() {
    local name=$1
    local url=$2
    local expected_status=${3:-200}
    
    TOTAL_TESTS=$((TOTAL_TESTS + 1))
    echo -e "\n${BLUE}Testing: $name${NC}"
    echo "URL: $url"
    
    HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" "$url" 2>/dev/null || echo "000")
    
    if [ "$HTTP_CODE" -eq "$expected_status" ]; then
        echo -e "${GREEN}✓ PASSED${NC} (HTTP $HTTP_CODE)"
        PASSED_TESTS=$((PASSED_TESTS + 1))
        return 0
    else
        echo -e "${RED}✗ FAILED${NC} (HTTP $HTTP_CODE, expected $expected_status)"
        FAILED_TESTS=$((FAILED_TESTS + 1))
        return 1
    fi
}

test_api_response() {
    local name=$1
    local url=$2
    local expected_cloud=$3
    
    TOTAL_TESTS=$((TOTAL_TESTS + 1))
    echo -e "\n${BLUE}Testing API: $name${NC}"
    echo "URL: $url"
    
    RESPONSE=$(curl -s "$url" 2>/dev/null || echo "{}")
    CLOUD=$(echo "$RESPONSE" | jq -r '.cloud' 2>/dev/null || echo "unknown")
    
    if [ "$CLOUD" = "$expected_cloud" ]; then
        echo -e "${GREEN}✓ PASSED${NC} (Cloud: $CLOUD)"
        echo "Response: $RESPONSE"
        PASSED_TESTS=$((PASSED_TESTS + 1))
        return 0
    else
        echo -e "${RED}✗ FAILED${NC} (Cloud: $CLOUD, expected $expected_cloud)"
        echo "Response: $RESPONSE"
        FAILED_TESTS=$((FAILED_TESTS + 1))
        return 1
    fi
}

echo -e "\n${YELLOW}=== AWS Tests ===${NC}"

# AWS API
test_api_response \
    "AWS API Root" \
    "https://i0w1fvqd85.execute-api.us-east-1.amazonaws.com/" \
    "AWS"

test_endpoint \
    "AWS API Health" \
    "https://i0w1fvqd85.execute-api.us-east-1.amazonaws.com/api/health"

test_endpoint \
    "AWS API Messages" \
    "https://i0w1fvqd85.execute-api.us-east-1.amazonaws.com/api/messages"

# AWS Frontend
test_endpoint \
    "AWS Frontend (CloudFront)" \
    "https://d2g1ria3j13hll.cloudfront.net/"

echo -e "\n${YELLOW}=== Azure Tests ===${NC}"

# Azure API
test_api_response \
    "Azure API Root" \
    "https://mcad-staging-api--ni077zg.livelycoast-fa9d3350.japaneast.azurecontainerapps.io/" \
    "Azure"

test_endpoint \
    "Azure API Health" \
    "https://mcad-staging-api--ni077zg.livelycoast-fa9d3350.japaneast.azurecontainerapps.io/api/health"

test_endpoint \
    "Azure API Messages" \
    "https://mcad-staging-api--ni077zg.livelycoast-fa9d3350.japaneast.azurecontainerapps.io/api/messages"

# Azure Frontend
test_endpoint \
    "Azure Frontend (Storage)" \
    "https://mcadfestaging.z11.web.core.windows.net/"

echo -e "\n${YELLOW}=== GCP Tests ===${NC}"

# GCP API
test_api_response \
    "GCP API Root" \
    "https://mcad-staging-api-son5b3ml7a-an.a.run.app/" \
    "GCP"

test_endpoint \
    "GCP API Health" \
    "https://mcad-staging-api-son5b3ml7a-an.a.run.app/api/health"

test_endpoint \
    "GCP API Messages" \
    "https://mcad-staging-api-son5b3ml7a-an.a.run.app/api/messages"

# GCP Frontend (Cloud Storage)
test_endpoint \
    "GCP Frontend (Cloud Storage)" \
    "https://storage.googleapis.com/mcad-staging-frontend/index.html"

# GCP Frontend (Load Balancer)
test_endpoint \
    "GCP Frontend (Load Balancer)" \
    "http://34.117.111.182/"

# 結果サマリー
echo -e "\n${YELLOW}==================================${NC}"
echo -e "${YELLOW}Test Summary${NC}"
echo -e "${YELLOW}==================================${NC}"
echo -e "Total Tests:  $TOTAL_TESTS"
echo -e "${GREEN}Passed:       $PASSED_TESTS${NC}"
echo -e "${RED}Failed:       $FAILED_TESTS${NC}"
echo -e "${YELLOW}==================================${NC}"

if [ $FAILED_TESTS -eq 0 ]; then
    echo -e "\n${GREEN}🎉 All tests passed!${NC}"
    exit 0
else
    echo -e "\n${RED}❌ Some tests failed!${NC}"
    exit 1
fi
