#!/bin/bash
set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Environment URLs
declare -A APIS=(
    ["AWS"]="https://z42qmqdqac.execute-api.ap-northeast-1.amazonaws.com"
    ["GCP"]="https://multicloud-auto-deploy-staging-api-son5b3ml7a-an.a.run.app"
    ["Azure"]="https://multicloud-auto-deploy-staging-func-d8a2guhfere0etcq.japaneast-01.azurewebsites.net/api/HttpTrigger"
)

# Test counters
TOTAL_TESTS=0
PASSED_TESTS=0
FAILED_TESTS=0

# Function to print test result
print_result() {
    local status=$1
    local message=$2
    
    TOTAL_TESTS=$((TOTAL_TESTS + 1))
    
    if [ "$status" = "PASS" ]; then
        echo -e "${GREEN}✓${NC} $message"
        PASSED_TESTS=$((PASSED_TESTS + 1))
    else
        echo -e "${RED}✗${NC} $message"
        FAILED_TESTS=$((FAILED_TESTS + 1))
    fi
}

# Function to test health endpoint
test_health() {
    local env=$1
    local api_url=$2
    
    echo -e "\n${BLUE}Testing Health Endpoint${NC}"
    
    response=$(curl -sf "${api_url}/health" 2>&1)
    if [ $? -eq 0 ]; then
        status=$(echo "$response" | jq -r '.status' 2>/dev/null)
        if [ "$status" = "ok" ]; then
            print_result "PASS" "Health check returned 'ok'"
        else
            print_result "FAIL" "Health check returned unexpected status: $status"
        fi
    else
        print_result "FAIL" "Health check failed: $response"
    fi
}

# Function to test CRUD operations
test_crud() {
    local env=$1
    local api_url=$2
    local message_id=""
    
    # All environments use /api/messages/ path
    local api_path="/api/messages/"
    
    echo -e "\n${BLUE}Testing CRUD Operations${NC}"
    
    # CREATE (POST)
    echo -e "${YELLOW}→${NC} Creating message..."
    create_response=$(curl -sf -X POST "${api_url}${api_path}" \
        -H "Content-Type: application/json" \
        -d '{"content":"E2E Test Message from '"$env"'","author":"E2E Test User"}' 2>&1)
    
    if [ $? -eq 0 ]; then
        message_id=$(echo "$create_response" | jq -r '.id' 2>/dev/null)
        if [ -n "$message_id" ] && [ "$message_id" != "null" ]; then
            print_result "PASS" "Create message (ID: ${message_id:0:8}...)"
        else
            print_result "FAIL" "Create message returned invalid ID"
            return
        fi
    else
        print_result "FAIL" "Create message failed: $create_response"
        return
    fi
    
    # Small delay to ensure consistency
    sleep 1
    
    # READ ALL (GET)
    echo -e "${YELLOW}→${NC} Fetching all messages..."
    list_response=$(curl -sf "${api_url}${api_path}" 2>&1)
    
    if [ $? -eq 0 ]; then
        # Check if response has 'messages' array
        messages=$(echo "$list_response" | jq -r '.messages' 2>/dev/null)
        if [ "$messages" != "null" ]; then
            count=$(echo "$messages" | jq '. | length' 2>/dev/null)
            if [ -n "$count" ] && [ "$count" -ge 0 ]; then
                print_result "PASS" "List messages (found $count)"
            else
                print_result "FAIL" "List messages returned invalid response"
            fi
        else
            print_result "FAIL" "List messages missing 'messages' field"
        fi
    else
        print_result "FAIL" "List messages failed: $list_response"
    fi
    
    # READ ONE (GET by ID)
    echo -e "${YELLOW}→${NC} Fetching specific message..."
    get_response=$(curl -sf "${api_url}${api_path}${message_id}" 2>&1)
    
    if [ $? -eq 0 ]; then
        content=$(echo "$get_response" | jq -r '.content' 2>/dev/null)
        if [ -n "$content" ] && [ "$content" != "null" ]; then
            print_result "PASS" "Get message by ID"
        else
            print_result "FAIL" "Get message returned invalid content"
        fi
    else
        print_result "FAIL" "Get message failed: $get_response"
    fi
    
    # UPDATE (PUT)
    echo -e "${YELLOW}→${NC} Updating message..."
    update_response=$(curl -sf -X PUT "${api_url}${api_path}${message_id}" \
        -H "Content-Type: application/json" \
        -d '{"content":"Updated E2E Test Message from '"$env"'","author":"Updated E2E Test User"}' 2>&1)
    
    if [ $? -eq 0 ]; then
        updated_content=$(echo "$update_response" | jq -r '.content' 2>/dev/null)
        if echo "$updated_content" | grep -q "Updated"; then
            print_result "PASS" "Update message"
        else
            print_result "FAIL" "Update message did not reflect changes"
        fi
    else
        print_result "FAIL" "Update message failed: $update_response"
    fi
    
    # DELETE
    echo -e "${YELLOW}→${NC} Deleting message..."
    # Delete returns 204 No Content, use -w for status code
    delete_status=$(curl -sf -w "%{http_code}" -o /dev/null -X DELETE "${api_url}${api_path}${message_id}" 2>&1)
    
    if [ "$delete_status" = "204" ] || [ "$delete_status" = "200" ]; then
        # Small delay before verification
        sleep 1
        # Verify deletion - should return 404
        verify_status=$(curl -s -o /dev/null -w "%{http_code}" "${api_url}${api_path}${message_id}" 2>&1)
        if [ "$verify_status" = "404" ]; then
            print_result "PASS" "Delete message"
        else
            print_result "FAIL" "Delete message - record still exists (status: $verify_status)"
        fi
    else
        print_result "FAIL" "Delete message failed (status: $delete_status)"
    fi
}

# Main execution
main() {
    echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"
    echo -e "${BLUE}        Multi-Cloud E2E Test Suite${NC}"
    echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"
    
    for env in AWS GCP Azure; do
        api_url="${APIS[$env]}"
        
        echo -e "\n${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
        echo -e "${GREEN}  Testing: $env${NC}"
        echo -e "${GREEN}  API URL: $api_url${NC}"
        echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
        
        test_health "$env" "$api_url"
        test_crud "$env" "$api_url"
    done
    
    # Summary
    echo -e "\n${BLUE}═══════════════════════════════════════════════════════${NC}"
    echo -e "${BLUE}        Test Summary${NC}"
    echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"
    echo -e "Total Tests:  $TOTAL_TESTS"
    echo -e "${GREEN}Passed:       $PASSED_TESTS${NC}"
    
    if [ $FAILED_TESTS -gt 0 ]; then
        echo -e "${RED}Failed:       $FAILED_TESTS${NC}"
        exit 1
    else
        echo -e "${GREEN}All tests passed! ✓${NC}"
        exit 0
    fi
}

# Run main function
main
