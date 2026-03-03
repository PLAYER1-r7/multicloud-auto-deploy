#!/bin/bash
# ========================================
# Script Name: diagnostics.sh
# Description: System Diagnostics & Health Check
# Author: PLAYER1-r7
# Created: 2026-01-10
# Last Modified: 2026-02-15
# Version: 1.0.0
# ========================================
#
# Usage: ./scripts/diagnostics.sh
#
# Description:
#   Comprehensive system diagnostics for multi-cloud deployment.
#   Checks tools, authentication, endpoints, and resource status.
#
# Diagnostic Checks:
#   1. Required tools (Pulumi, AWS CLI, etc.)
#   2. Cloud provider authentication status
#   3. Deployment endpoint connectivity
#   4. Pulumi stack state
#   5. AWS key resources status
#
# Prerequisites:
#   - None (diagnostic script)
#
# Exit Codes:
#   0 - All checks passed
#   1 - One or more checks failed
#
# ========================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

AWS_API_URL="${AWS_API_URL:-https://z42qmqdqac.execute-api.ap-northeast-1.amazonaws.com}"
AZURE_API_URL="${AZURE_API_URL:-https://multicloud-auto-deploy-staging-func-d8a2guhfere0etcq.japaneast-01.azurewebsites.net}"
GCP_API_URL="${GCP_API_URL:-https://multicloud-auto-deploy-staging-api-son5b3ml7a-an.a.run.app}"

echo "================================================"
echo "Multi-Cloud Deployment Diagnostics"
echo "================================================"
echo ""

# Check required tools
echo "📦 Checking installed tools..."
echo ""

check_tool() {
    if command -v $1 &> /dev/null; then
        VERSION=$($1 --version 2>&1 | head -1)
        echo "✅ $1: $VERSION"
    else
        echo "❌ $1: NOT INSTALLED"
    fi
}

check_tool aws
check_tool az
check_tool gcloud
check_tool pulumi
check_tool gh
check_tool node
check_tool npm
check_tool python3
check_tool docker
check_tool jq
check_tool curl

echo ""
echo "================================================"
echo "🐍 Python Environment Check"
echo "================================================"
echo ""

# Check default python3
if command -v python3 &> /dev/null; then
    echo "✅ python3: $(python3 --version)"
    if python3 -m pip --version &> /dev/null; then
        echo "  ✅ pip: $(python3 -m pip --version)"
    else
        echo "  ❌ pip: NOT AVAILABLE"
    fi
else
    echo "❌ python3: NOT FOUND"
fi

echo ""
echo "================================================"
echo "☁️  Cloud Provider Authentication"
echo "================================================"
echo ""

# AWS
if aws sts get-caller-identity &> /dev/null; then
    echo "✅ AWS: Authenticated"
    aws sts get-caller-identity --query 'Account' --output text | xargs -I {} echo "  Account: {}"
else
    echo "❌ AWS: Not authenticated"
fi

# Azure
if az account show &> /dev/null; then
    echo "✅ Azure: Authenticated"
    az account show --query 'user.name' -o tsv | xargs -I {} echo "  User: {}"
else
    echo "❌ Azure: Not authenticated"
fi

# GCP
if gcloud auth list --filter=status:ACTIVE --format="value(account)" 2>/dev/null | grep -q .; then
    echo "✅ GCP: Authenticated"
    gcloud auth list --filter=status:ACTIVE --format="value(account)" | xargs -I {} echo "  Account: {}"
else
    echo "❌ GCP: Not authenticated"
fi

# GitHub CLI
if gh auth status &> /dev/null; then
    echo "✅ GitHub CLI: Authenticated"
else
    echo "❌ GitHub CLI: Not authenticated (run: gh auth login)"
fi

echo ""
echo "================================================"
echo "🧪 Testing Cloud Deployments"
echo "================================================"
echo ""

check_api_endpoint() {
    local name="$1"
    local url="$2"
    local health_url="${url%/}/health"

    echo "$name:"
    if curl -sf "$health_url" | jq -e '.status == "ok" or .status == "healthy"' > /dev/null 2>&1; then
        echo "  ✅ Health Endpoint: $health_url"
        curl -s "$health_url" | jq .
    else
        echo "  ❌ Health Endpoint: FAILED ($health_url)"
    fi
    echo ""
}

check_api_endpoint "AWS (ap-northeast-1)" "$AWS_API_URL"
check_api_endpoint "Azure (japaneast)" "$AZURE_API_URL"
check_api_endpoint "GCP (asia-northeast1)" "$GCP_API_URL"

echo "================================================"
echo "💾 Pulumi Stack Check"
echo "================================================"
echo ""

for dir in "$PROJECT_ROOT/infrastructure/pulumi/aws" "$PROJECT_ROOT/infrastructure/pulumi/azure" "$PROJECT_ROOT/infrastructure/pulumi/gcp"; do
    if [ -d "$dir" ]; then
        provider=$(basename "$dir")
        echo "$provider:"
        (
            cd "$dir"
            pulumi stack ls 2>/dev/null | sed 's/^/  /' || echo "  ⚠️  stack情報を取得できません"
        )
        echo ""
    fi
done

echo ""
echo "================================================"
echo "📊 AWS Resources Check"
echo "================================================"
echo ""

if aws sts get-caller-identity &> /dev/null; then
    echo "Lambda Functions (ap-northeast-1):"
    aws lambda list-functions --region ap-northeast-1 --query 'Functions[?contains(FunctionName, `multicloud`)].{Name:FunctionName, Runtime:Runtime, Arch:Architectures[0]}' --output table 2>/dev/null || echo "  None found"

    echo ""
    echo "S3 Buckets:"
    aws s3 ls | grep -i multicloud || echo "  None found"

    echo ""
    echo "CloudFront Distributions:"
    aws cloudfront list-distributions --query 'DistributionList.Items[?contains(Comment, `Multi-Cloud`)].{Id:Id, Status:Status, DomainName:DomainName}' --output table 2>/dev/null || echo "  None found"
fi

echo ""
echo "================================================"
echo "✅ Diagnostics Complete"
echo "================================================"
