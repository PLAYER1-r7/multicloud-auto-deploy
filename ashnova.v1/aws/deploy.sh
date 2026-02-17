#!/bin/bash

# Ashnova Static Website Deployment Script

set -e

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
TERRAFORM_DIR="$SCRIPT_DIR/../terraform/aws/envs/merged"
WEBSITE_DIR="$SCRIPT_DIR/website"

echo "🚀 Ashnova Static Website Deployment"
echo "======================================"

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
BUCKET_NAME=$(tofu output -raw s3_bucket_name)
WEBSITE_URL=$(tofu output -raw website_url)

# Upload website files
echo ""
echo "📤 Uploading website files to S3..."
aws s3 sync "$WEBSITE_DIR/" "s3://$BUCKET_NAME/" --profile satoshi --delete

# Invalidate CloudFront cache if enabled
DISTRIBUTION_ID=$(tofu output -raw cloudfront_distribution_id 2>/dev/null || echo "")
if [ ! -z "$DISTRIBUTION_ID" ] && [ "$DISTRIBUTION_ID" != "null" ]; then
    echo ""
    echo "🔄 Invalidating CloudFront cache..."
    aws cloudfront create-invalidation \
        --distribution-id "$DISTRIBUTION_ID" \
        --paths "/*" \
        --profile satoshi
fi

echo ""
echo "✅ Deployment completed successfully!"
echo ""
echo "🌐 Website URL: $WEBSITE_URL"
echo ""
