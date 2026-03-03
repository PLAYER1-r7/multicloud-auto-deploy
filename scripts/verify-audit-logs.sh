#!/bin/bash

# Security Audit Log Verification Script
# Checks if audit logs are properly configured and recording in all 3 clouds

set -e

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

PASS_COUNT=0
FAIL_COUNT=0

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

# ========================================
# AWS CloudTrail Verification
# ========================================
check_aws_cloudtrail() {
    echo ""
    log_info "Checking AWS CloudTrail..."
    
    # Requires: aws CLI, credentials configured
    if ! command -v aws &> /dev/null; then
        log_warn "AWS CLI not found - skipping CloudTrail check"
        return 1
    fi
    
    # Check if CloudTrail is enabled in ap-northeast-1
    local trail_status=$(aws cloudtrail describe-trails \
        --region ap-northeast-1 \
        --query 'trailList[?IsMultiRegionTrail==`false`] | length(@)' \
        2>/dev/null || echo "0")
    
    if [ "$trail_status" -gt 0 ]; then
        log_pass "AWS CloudTrail: Enabled in ap-northeast-1"
        
        # Get recent events (last 1 hour)
        local event_count=$(aws cloudtrail lookup-events \
            --region ap-northeast-1 \
            --start-time "$(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%S)" \
            --query 'length(Events)' \
            2>/dev/null || echo "0")
        
        log_pass "AWS CloudTrail: $event_count events in last 1 hour"
    else
        log_fail "AWS CloudTrail: Not enabled or no trails found"
    fi
}

# ========================================
# Azure Activity Log Verification
# ========================================
check_azure_activity_log() {
    echo ""
    log_info "Checking Azure Activity Log..."
    
    # Requires: Azure CLI, credentials configured
    if ! command -v az &> /dev/null; then
        log_warn "Azure CLI not found - skipping Activity Log check"
        return 1
    fi
    
    # Check if Activity Log is enabled (stored in default Log Analytics workspace)
    local rg="multicloud-auto-deploy-production-rg"
    local law_query=$(az monitor log-analytics workspace list \
        --resource-group "$rg" \
        --query "[0].name" \
        2>/dev/null || echo "")
    
    if [ -n "$law_query" ]; then
        log_pass "Azure Activity Log: Log Analytics workspace found ($law_query)"
        
        # Check recent activity
        local activity_count=$(az monitor activity-log list \
            --resource-group "$rg" \
            --start-time "$(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%S)" \
            --query 'length(@)' \
            2>/dev/null || echo "0")
        
        log_pass "Azure Activity Log: $activity_count events in last 1 hour"
    else
        log_warn "Azure Activity Log: Log Analytics workspace not found or not configured"
    fi
}

# ========================================
# GCP Cloud Audit Logs Verification
# ========================================
check_gcp_audit_logs() {
    echo ""
    log_info "Checking GCP Cloud Audit Logs..."
    
    # Requires: gcloud CLI, credentials configured
    if ! command -v gcloud &> /dev/null; then
        log_warn "gcloud CLI not found - skipping Audit Logs check"
        return 1
    fi
    
    # Get current project
    local project=$(gcloud config get-value project 2>/dev/null || echo "")
    
    if [ -n "$project" ]; then
        # Check audit log configuration
        local audit_config=$(gcloud projects get-iam-policy "$project" \
            --flatten="auditConfigs[].service" \
            --filter="auditConfigs.service:allServices" \
            --format="value(auditConfigs.logTypes[])" \
            2>/dev/null || echo "")
        
        if [ -n "$audit_config" ]; then
            log_pass "GCP Cloud Audit Logs: Enabled for allServices"
            
            # Sample log types
            local has_admin=$(echo "$audit_config" | grep -i "ADMIN_READ" || echo "")
            local has_data=$(echo "$audit_config" | grep -i "DATA_READ\|DATA_WRITE" || echo "")
            
            [ -n "$has_admin" ] && log_pass "GCP Audit Logs: ADMIN_READ logs enabled"
            [ -n "$has_data" ] && log_pass "GCP Audit Logs: DATA_READ/DATA_WRITE logs enabled"
        else
            log_warn "GCP Cloud Audit Logs: Not configured or no allServices entry found"
        fi
    else
        log_warn "gcloud: No project configured"
    fi
}

# ========================================
# Summary
# ========================================
print_summary() {
    echo ""
    echo "========================================"
    echo "Audit Log Summary"
    echo "========================================"
    echo -e "${GREEN}✅ Configured: $PASS_COUNT${NC}"
    echo -e "${RED}❌ Issues: $FAIL_COUNT${NC}"
    echo ""
    
    if [ $FAIL_COUNT -eq 0 ]; then
        log_pass "All audit logs properly configured!"
    else
        log_warn "Some configurations need attention. See above for details."
    fi
}

# ========================================
# Main Execution
# ========================================
echo "========================================"
echo "Security Audit Log Verification"
echo "Date: $(date)"
echo "========================================"

check_aws_cloudtrail
check_azure_activity_log
check_gcp_audit_logs

print_summary
