#!/bin/bash
# ========================================
# Script Name: test-endpoints.sh
# Description: Multi-Cloud Endpoint Testing
# Author: PLAYER1-r7
# Created: 2026-01-15
# Last Modified: 2026-02-15
# Version: 1.0.0
# ========================================
#
# Usage: ./scripts/test-endpoints.sh
#
# Description:
#   Tests connectivity and basic health of all deployed endpoints
#   across AWS, Azure, and GCP environments.
#
# Test Targets:
#   - AWS: API + CloudFront Frontend
#   - Azure: Functions API + Front Door Frontend
#   - GCP: Cloud Run API + Cloud CDN Frontend
#
# Prerequisites:
#   - curl command available
#   - Active deployments on all clouds
#
# Exit Codes:
#   0 - All endpoints responding
#   1 - One or more endpoints failed
#
# ========================================

set -e

# カラー定義
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# エンドポイント定義
AWS_API="https://z42qmqdqac.execute-api.ap-northeast-1.amazonaws.com"
AWS_FRONTEND="https://d1tf3uumcm4bo1.cloudfront.net"

AZURE_API="https://multicloud-auto-deploy-staging-func-d8a2guhfere0etcq.japaneast-01.azurewebsites.net/api/HttpTrigger"
AZURE_FRONTEND="https://mcad-staging-d45ihd-dseygrc9c3a3htgj.z01.azurefd.net"

GCP_API="https://multicloud-auto-deploy-staging-api-son5b3ml7a-an.a.run.app"
GCP_FRONTEND="http://34.117.111.182"

# ヘルパー関数
print_header() {
    echo -e "${BLUE}========================================${NC}"
    echo -e "${BLUE}  $1${NC}"
    echo -e "${BLUE}========================================${NC}"
}

test_endpoint() {
    local name=$1
    local url=$2
    local expected_code=${3:-200}
    
    echo -e "\n${YELLOW}Testing: ${name}${NC}"
    echo "URL: $url"
    
    response=$(curl -s -w "\n%{http_code}" "$url" 2>&1)
    http_code=$(echo "$response" | tail -n 1)
    body=$(echo "$response" | head -n -1)
    
    if [ "$http_code" = "$expected_code" ]; then
        echo -e "${GREEN}✓ Status: $http_code OK${NC}"
        if [ -n "$body" ]; then
            echo "Response: $body" | head -c 200
            echo ""
        fi
        return 0
    else
        echo -e "${RED}✗ Status: $http_code (Expected: $expected_code)${NC}"
        return 1
    fi
}

# メイン処理
main() {
    print_header "Multi-Cloud Endpoint Test"
    
    local aws_pass=0
    local azure_pass=0
    local gcp_pass=0
    
    # AWS テスト
    print_header "AWS (ap-northeast-1)"
    if test_endpoint "AWS API" "$AWS_API/"; then
        ((aws_pass++))
    fi
    if test_endpoint "AWS Frontend" "$AWS_FRONTEND/"; then
        ((aws_pass++))
    fi
    
    # Azure テスト
    print_header "Azure (japaneast)"
    if test_endpoint "Azure API" "$AZURE_API/"; then
        ((azure_pass++))
    fi
    if test_endpoint "Azure Frontend" "$AZURE_FRONTEND/"; then
        ((azure_pass++))
    fi
    
    # GCP テスト
    print_header "GCP (asia-northeast1)"
    if test_endpoint "GCP API" "$GCP_API/"; then
        ((gcp_pass++))
    fi
    if test_endpoint "GCP Frontend" "$GCP_FRONTEND/"; then
        ((gcp_pass++))
    fi
    
    # 結果サマリー
    print_header "Test Summary"
    echo -e "AWS:   ${aws_pass}/2 tests passed"
    echo -e "Azure: ${azure_pass}/2 tests passed"
    echo -e "GCP:   ${gcp_pass}/2 tests passed"
    echo ""
    
    local total_pass=$((aws_pass + azure_pass + gcp_pass))
    local total_tests=6
    
    if [ $total_pass -eq $total_tests ]; then
        echo -e "${GREEN}✓ All tests passed! ($total_pass/$total_tests)${NC}"
        return 0
    else
        echo -e "${YELLOW}⚠ Some tests failed ($total_pass/$total_tests)${NC}"
        return 1
    fi
}

# 詳細モード
if [ "$1" = "-v" ] || [ "$1" = "--verbose" ]; then
    main
else
    main 2>&1 | grep -v "^$"
fi
