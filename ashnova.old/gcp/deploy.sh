#!/bin/bash

# Ashnova Static Website Deployment Script for Google Cloud

set -e

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
TERRAFORM_DIR="$SCRIPT_DIR/../terraform/gcp/envs/static-website"
WEBSITE_DIR="$SCRIPT_DIR/website"

echo "🚀 Ashnova Static Website Deployment (Google Cloud)"
echo "===================================================="

# Check gcloud authentication
echo ""
echo "🔐 Checking Google Cloud authentication..."
if ! gcloud auth list --filter=status:ACTIVE --format="value(account)" &> /dev/null; then
    echo "❌ Not logged in to Google Cloud. Please run: gcloud auth application-default login"
    exit 1
fi

ACCOUNT=$(gcloud auth list --filter=status:ACTIVE --format="value(account)" 2>/dev/null | head -n1)
PROJECT=$(gcloud config get-value project 2>/dev/null)

if [ -z "$PROJECT" ]; then
    echo "❌ No project set. Please run: gcloud config set project YOUR_PROJECT_ID"
    exit 1
fi

echo "✅ Logged in to Google Cloud"
echo "   Account: $ACCOUNT"
echo "   Project: $PROJECT"

# Change to terraform directory
cd "$TERRAFORM_DIR"

# Check if terraform.tfvars exists, if not create it
if [ ! -f terraform.tfvars ]; then
    echo ""
    echo "📝 Creating terraform.tfvars with project ID..."
    cat > terraform.tfvars <<EOF
gcp_project_id = "$PROJECT"
EOF
fi

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
BUCKET_NAME=$(tofu output -raw bucket_name)
WEBSITE_URL=$(tofu output -raw website_url)

# Upload website files
echo ""
echo "📤 Uploading website files to Cloud Storage..."
gcloud storage cp "$WEBSITE_DIR/index.html" "gs://$BUCKET_NAME/"
gcloud storage cp "$WEBSITE_DIR/error.html" "gs://$BUCKET_NAME/"

# Set proper content types
echo ""
echo "🔧 Setting content types..."
gcloud storage objects update "gs://$BUCKET_NAME/index.html" --content-type="text/html"
gcloud storage objects update "gs://$BUCKET_NAME/error.html" --content-type="text/html"

# Invalidate CDN cache if enabled
LB_IP=$(tofu output -raw load_balancer_ip 2>/dev/null || echo "")
if [ ! -z "$LB_IP" ] && [ "$LB_IP" != "null" ]; then
    echo ""
    echo "ℹ️  CDN cache will be refreshed automatically based on TTL settings"
    echo "   For immediate refresh, you can manually invalidate the cache using Cloud Console"
fi

echo ""
echo "✅ Deployment completed successfully!"
echo ""
echo "🌐 Website URL: $WEBSITE_URL"
echo ""

# Show DNS configuration if custom domain is used
DNS_INFO=$(tofu output -json dns_configuration 2>/dev/null || echo "null")
if [ "$DNS_INFO" != "null" ]; then
    echo "📝 DNS Configuration:"
    echo "$DNS_INFO" | jq -r '"   Domain: \(.domain)\n   Type: \(.type)\n   Value: \(.value)"'
    echo ""
fi
