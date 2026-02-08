#!/bin/bash

# Ashnova Static Website Deployment Script for Azure

set -e

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
TERRAFORM_DIR="$SCRIPT_DIR/../terraform/azure/envs/static-website"
WEBSITE_DIR="$SCRIPT_DIR/website"

echo "🚀 Ashnova Static Website Deployment (Azure)"
echo "=============================================="

# Check Azure CLI login
echo ""
echo "🔐 Checking Azure CLI authentication..."
if ! az account show &> /dev/null; then
    echo "❌ Not logged in to Azure. Please run: az login"
    exit 1
fi

SUBSCRIPTION=$(az account show --query name -o tsv)
echo "✅ Logged in to Azure"
echo "   Subscription: $SUBSCRIPTION"

# Change to terraform directory
cd "$TERRAFORM_DIR"

# Initialize OpenTofu
echo ""
echo "📦 Initializing OpenTofu..."
tofu init

# Plan
echo ""
echo "📋 Creating execution plan..."
tofu plan

# Ask for confirmation
echo ""
read -p "Do you want to apply these changes? (yes/no): " confirm

if [ "$confirm" != "yes" ]; then
    echo "❌ Deployment cancelled."
    exit 0
fi

# Apply
echo ""
echo "🔨 Applying changes..."
tofu apply -auto-approve

# Get outputs
echo ""
echo "📊 Getting deployment information..."
STORAGE_ACCOUNT=$(tofu output -raw storage_account_name)
WEBSITE_URL=$(tofu output -raw website_url)

# Upload website files
echo ""
echo "📤 Uploading website files to Azure Storage..."
az storage blob upload-batch \
    --account-name "$STORAGE_ACCOUNT" \
    --destination '$web' \
    --source "$WEBSITE_DIR" \
    --overwrite

# Purge Front Door cache if enabled
FD_ENDPOINT=$(tofu output -raw frontdoor_endpoint_host 2>/dev/null || echo "")
if [ ! -z "$FD_ENDPOINT" ] && [ "$FD_ENDPOINT" != "null" ]; then
    echo ""
    echo "🔄 Purging Front Door cache..."
    
    RESOURCE_GROUP=$(tofu output -raw resource_group_name)
    FD_PROFILE=$(az afd profile list -g "$RESOURCE_GROUP" --query "[0].name" -o tsv)
    FD_ENDPOINT_NAME=$(az afd endpoint list -g "$RESOURCE_GROUP" --profile-name "$FD_PROFILE" --query "[0].name" -o tsv)
    
    az afd endpoint purge \
        --resource-group "$RESOURCE_GROUP" \
        --profile-name "$FD_PROFILE" \
        --endpoint-name "$FD_ENDPOINT_NAME" \
        --domains "$FD_ENDPOINT" \
        --content-paths "/*"
fi

echo ""
echo "✅ Deployment completed successfully!"
echo ""
echo "🌐 Website URL: $WEBSITE_URL"
echo ""
