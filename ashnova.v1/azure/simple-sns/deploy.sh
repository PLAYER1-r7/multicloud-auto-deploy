#!/bin/bash

# Azure Simple-SNS Deploy Script

set -e

echo "🚀 Deploying Simple-SNS to Azure..."

# Check if Azure CLI is installed
if ! command -v az &> /dev/null; then
    echo "❌ Azure CLI is not installed. Please install it first."
    exit 1
fi

# Check if logged in
if ! az account show &> /dev/null; then
    echo "❌ Not logged in to Azure. Please run 'az login' first."
    exit 1
fi

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Variables (can be overridden by environment)
RESOURCE_GROUP="${RESOURCE_GROUP:-rg-simple-sns-prod}"
STORAGE_ACCOUNT="${STORAGE_ACCOUNT:-}"
CONTAINER_NAME="\$web"
LOCATION="${LOCATION:-japaneast}"

# Try to read outputs from OpenTofu if available
if [ -d "$ROOT_DIR/../../terraform/azure/envs/simple-sns" ]; then
    pushd "$ROOT_DIR/../../terraform/azure/envs/simple-sns" >/dev/null
    if command -v tofu &> /dev/null; then
        if tofu output -raw resource_group_name &> /dev/null; then
            RESOURCE_GROUP="$(tofu output -raw resource_group_name)"
        fi
        if tofu output -raw storage_account_name &> /dev/null; then
            STORAGE_ACCOUNT="$(tofu output -raw storage_account_name)"
        fi
    fi
    popd >/dev/null
fi

if [ -z "$STORAGE_ACCOUNT" ]; then
    echo "❌ STORAGE_ACCOUNT is not set and could not be read from tofu outputs."
    exit 1
fi

echo "📦 Building frontend..."
cd "$ROOT_DIR"
npm run build:frontend

echo "☁️  Deploying to Azure Blob Storage..."

# Create storage account if it doesn't exist
if ! az storage account show --name "$STORAGE_ACCOUNT" --resource-group "$RESOURCE_GROUP" &> /dev/null; then
    echo "Creating storage account..."
    az storage account create \
        --name "$STORAGE_ACCOUNT" \
        --resource-group "$RESOURCE_GROUP" \
        --location "$LOCATION" \
        --sku Standard_LRS \
        --kind StorageV2 \
        --https-only true \
        --min-tls-version TLS1_2 \
        --allow-blob-public-access true
    
    # Enable static website hosting
    az storage blob service-properties update \
        --account-name "$STORAGE_ACCOUNT" \
        --static-website \
        --404-document error.html \
        --index-document index.html
fi

# Upload files
echo "📤 Uploading files..."
az storage blob upload-batch \
    --account-name "$STORAGE_ACCOUNT" \
    --source dist-frontend \
    --destination "$CONTAINER_NAME" \
    --overwrite \
    --auth-mode login

# Ensure index.html is not cached
az storage blob upload \
    --account-name "$STORAGE_ACCOUNT" \
    --container-name "$CONTAINER_NAME" \
    --file dist-frontend/index.html \
    --name index.html \
    --content-cache-control "no-cache, no-store, must-revalidate" \
    --content-type "text/html" \
    --overwrite \
    --auth-mode login

# Get the static website URL
WEBSITE_URL=$(az storage account show \
    --name "$STORAGE_ACCOUNT" \
    --resource-group "$RESOURCE_GROUP" \
    --query "primaryEndpoints.web" \
    --output tsv)

echo "✅ Deployment complete!"
echo "🌐 Website URL: $WEBSITE_URL"
echo ""
echo "Note: If using Azure Front Door or CDN, you may need to purge the cache."
