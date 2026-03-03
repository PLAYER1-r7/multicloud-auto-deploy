#!/bin/bash

# Production Endpoint Validation Script
# Validates health, response times, and CORS for all 3 cloud environments

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
TIMEOUT=5
EXPECTED_STATUS=200
CORS_ORIGIN="https://example.com"

# Endpoints
declare -A ENDPOINTS=(
    ["aws_frontend"]="https://d1qob7569mn5nw.cloudfront.net"
    ["aws_api"]="https://qkzypr32af.execute-api.ap-northeast-1.amazonaws.com"
    ["azure_frontend"]="https://mcadwebd45ihd.z11.web.core.windows.net"
    ["azure_api"]="https://multicloud-auto-deploy-production-func-d8a2guhfere0etcq.japaneast-01.azurewebsites.net"
    ["gcp_frontend"]="https://www.gcp.ashnova.jp"
    ["gcp_api"]="https://multicloud-auto-deploy-production-api-***-an.a.run.app"
)

# Test results
declare -A RESULTS
PASS_COUNT=0
FAIL_COUNT=0

# Helper functions
log_info() {
    echo -e "${BLUE}ℹ${NC}  $1"
}

log_pass() {
    echo -e "${GREEN}✅${NC} $1"
    ((PASS_COUNT++))
}

log_fail() {
    echo -e "${RED}❌${NC} $1"
    ((FAIL_COUNT++))
}

log_warn() {
    echo -e "${YELLOW}⚠️${NC}  $1"
}

test_endpoint_health() {
    local name=$1
    local url=$2

    log_info "Testing: $name"
    log_info "  URL: $url"

    # Test 1: HTTP Status
    local http_code=$(curl -s -o /dev/null -w "%{http_code}" -m $TIMEOUT "$url" 2>/dev/null || echo "000")

    if [ "$http_code" = "$EXPECTED_STATUS" ]; then
        log_pass "$name: HTTP $http_code (expected)"
    else
        log_fail "$name: HTTP $http_code (expected $EXPECTED_STATUS)"
        return 1
    fi

    # Test 2: Response Time
    local response_time=$(curl -s -o /dev/null -w "%{time_total}" -m $TIMEOUT "$url" 2>/dev/null || echo "999")
    response_time_ms=$(echo "$response_time * 1000" | bc -l | cut -d. -f1)

    if [ -z "$response_time" ] || [ "$response_time" = "999" ]; then
        log_fail "$name: Could not measure response time"
        return 1
    fi

    if [ "$response_time_ms" -lt 2000 ]; then
        log_pass "$name: Response time ${response_time_ms}ms (excellent)"
    elif [ "$response_time_ms" -lt 5000 ]; then
        log_pass "$name: Response time ${response_time_ms}ms (good)"
    else
        log_warn "$name: Response time ${response_time_ms}ms (slow - may indicate cold start)"
    fi

    # Test 3: Headers (basic check)
    local has_content_type=$(curl -s -I "$url" 2>/dev/null | grep -i "Content-Type:" || echo "")
    if [ -n "$has_content_type" ]; then
        log_pass "$name: Content-Type header present"
    else
        log_warn "$name: Content-Type header missing"
    fi

    echo ""
}

test_api_cors() {
    local name=$1
    local url=$2

    log_info "Testing CORS: $name"

    local cors_header=$(curl -s -I -H "Origin: $CORS_ORIGIN" "$url" 2>/dev/null | grep -i "Access-Control-Allow-Origin:" || echo "")

    if [ -n "$cors_header" ]; then
        log_pass "$name: CORS header present: $cors_header"
    else
        log_warn "$name: CORS header missing (may be restricted)"
    fi

    echo ""
}

test_ssl_certificate() {
    local name=$1
    local url=$2

    log_info "Testing SSL: $name"

    # Extract hostname from URL
    local hostname=$(echo "$url" | sed -E 's|https://([^/]+).*|\1|')

    if echo | openssl s_client -servername "$hostname" -connect "$hostname:443" 2>/dev/null | grep -q "Verify return code: 0"; then
        log_pass "$name: SSL certificate valid"
    else
        log_fail "$name: SSL certificate validation failed"
    fi

    echo ""
}

# Main execution
echo "========================================"
echo "Production Endpoint Validation"
echo "Date: $(date)"
echo "========================================"
echo ""

log_info "Testing Frontend Endpoints..."
echo ""

test_endpoint_health "AWS CloudFront" "${ENDPOINTS[aws_frontend]}"
test_endpoint_health "Azure Storage" "${ENDPOINTS[azure_frontend]}"
test_endpoint_health "GCP CDN" "${ENDPOINTS[gcp_frontend]}"

echo ""
log_info "Testing API Endpoints..."
echo ""

test_endpoint_health "AWS API Gateway" "${ENDPOINTS[aws_api]}"
test_endpoint_health "Azure Functions" "${ENDPOINTS[azure_api]}"
# Note: GCP API endpoint requires credentials, skip for now
log_warn "GCP API endpoint: Requires Cloud Run credentials, skipping direct test"

echo ""
log_info "Testing SSL Certificates..."
echo ""

test_ssl_certificate "AWS CloudFront" "${ENDPOINTS[aws_frontend]}"
test_ssl_certificate "GCP CDN" "${ENDPOINTS[gcp_frontend]}"

echo ""
log_info "Testing CORS Headers..."
echo ""

test_api_cors "AWS API Gateway" "${ENDPOINTS[aws_api]}"
test_api_cors "Azure Functions" "${ENDPOINTS[azure_api]}"

# Summary
echo ""
echo "========================================"
echo "Test Summary"
echo "========================================"
echo -e "${GREEN}✅ Passed: $PASS_COUNT${NC}"
echo -e "${RED}❌ Failed: $FAIL_COUNT${NC}"
echo ""

if [ $FAIL_COUNT -eq 0 ]; then
    log_pass "All tests passed!"
    exit 0
else
    log_fail "Some tests failed. Review above for details."
    exit 1
fi
