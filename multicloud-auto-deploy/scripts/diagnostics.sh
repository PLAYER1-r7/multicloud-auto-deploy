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
#   1. Required tools (Terraform, AWS CLI, etc.)
#   2. Cloud provider authentication status
#   3. Deployment endpoint connectivity
#   4. Terraform resource state
#   5. Environment variable configuration
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
check_tool terraform
check_tool gh
check_tool node
check_tool npm
check_tool python3.12
check_tool docker
check_tool jq
check_tool curl

echo ""
echo "================================================"
echo "🐍 Python Environment Check"
echo "================================================"
echo ""

# Check Python version and pip
if command -v python3.12 &> /dev/null; then
    echo "✅ python3.12: $(python3.12 --version)"
    if python3.12 -m pip --version &> /dev/null; then
        echo "  ✅ pip: $(python3.12 -m pip --version)"
    else
        echo "  ❌ pip: NOT AVAILABLE"
    fi
else
    echo "❌ python3.12: NOT FOUND"
fi

# Also check default python3
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

# Test AWS
echo "AWS (ap-northeast-1):"
if curl -sf https://52z731x570.execute-api.ap-northeast-1.amazonaws.com/ | jq -e '.cloud == "AWS"' > /dev/null 2>&1; then
    echo "  ✅ API Endpoint: https://52z731x570.execute-api.ap-northeast-1.amazonaws.com/"
    curl -s https://52z731x570.execute-api.ap-northeast-1.amazonaws.com/ | jq .
else
    echo "  ❌ API Endpoint: FAILED"
fi
echo ""

# Test Azure
echo "Azure (japaneast):"
if curl -sf https://mcad-staging-api--0000003.livelycoast-fa9d3350.japaneast.azurecontainerapps.io/ | jq -e '.cloud == "Azure"' > /dev/null 2>&1; then
    echo "  ✅ API Endpoint: https://mcad-staging-api--0000003.livelycoast-fa9d3350.japaneast.azurecontainerapps.io/"
    curl -s https://mcad-staging-api--0000003.livelycoast-fa9d3350.japaneast.azurecontainerapps.io/ | jq .
else
    echo "  ❌ API Endpoint: FAILED"
fi
echo ""

# Test GCP
echo "GCP (asia-northeast1):"
if curl -sf https://mcad-staging-api-son5b3ml7a-an.a.run.app/ | jq -e '.cloud == "GCP"' > /dev/null 2>&1; then
    echo "  ✅ API Endpoint: https://mcad-staging-api-son5b3ml7a-an.a.run.app/"
    curl -s https://mcad-staging-api-son5b3ml7a-an.a.run.app/ | jq .
else
    echo "  ❌ API Endpoint: FAILED"
fi
echo ""

echo "================================================"
echo "💾 Terraform State Check"
echo "================================================"
echo ""

if [ -d "infrastructure/terraform/aws" ]; then
    cd infrastructure/terraform/aws
    if [ -f "terraform.tfstate" ] || terraform state list &> /dev/null; then
        echo "✅ Terraform state exists"
        echo "  Resources:"
        terraform state list 2>/dev/null | sed 's/^/    /'
    else
        echo "⚠️  Terraform state not found"
    fi
    cd - > /dev/null
fi

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
