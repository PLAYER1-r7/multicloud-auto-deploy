#!/bin/bash

# Cleanup old us-east-1 resources
# This script monitors and deletes the old CloudFront distribution

set -e

DIST_ID="E241KZLP132LO6"
CHECK_INTERVAL=30  # seconds

echo "🔍 CloudFront Distribution Cleanup Monitor"
echo "=========================================="
echo "Distribution ID: $DIST_ID"
echo ""

# Function to check distribution status
check_status() {
    aws cloudfront get-distribution --id $DIST_ID \
        --query 'Distribution.{Status:Status,Enabled:DistributionConfig.Enabled}' \
        --output json 2>/dev/null || echo '{"Status":"NotFound","Enabled":false}'
}

# Function to delete distribution
delete_distribution() {
    echo "🗑️  Deleting CloudFront distribution..."
    ETAG=$(aws cloudfront get-distribution --id $DIST_ID --query 'ETag' --output text)
    aws cloudfront delete-distribution --id $DIST_ID --if-match "$ETAG"
    echo "✅ Distribution deleted successfully!"
}

# Main monitoring loop
while true; do
    STATUS=$(check_status)
    DIST_STATUS=$(echo $STATUS | jq -r '.Status')
    ENABLED=$(echo $STATUS | jq -r '.Enabled')
    
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] Status: $DIST_STATUS, Enabled: $ENABLED"
    
    if [ "$DIST_STATUS" = "NotFound" ]; then
        echo "✅ Distribution already deleted or not found."
        break
    elif [ "$DIST_STATUS" = "Deployed" ] && [ "$ENABLED" = "false" ]; then
        echo "✅ Distribution is disabled and deployed!"
        delete_distribution
        break
    elif [ "$DIST_STATUS" = "Deployed" ] && [ "$ENABLED" = "true" ]; then
        echo "❌ Distribution is still enabled. Cannot delete."
        exit 1
    else
        echo "⏳ Waiting for deployment to complete... (checking again in ${CHECK_INTERVAL}s)"
        sleep $CHECK_INTERVAL
    fi
done

echo ""
echo "🎉 Cleanup completed!"
echo ""
echo "Summary:"
echo "✅ S3 Bucket deleted: multicloud-auto-deploy-terraform-state (us-east-1)"
echo "✅ CloudFront Distribution deleted: E241KZLP132LO6"
echo ""
echo "Remaining resources (ap-northeast-1):"
echo "- S3: multicloud-auto-deploy-staging-frontend"
echo "- S3: multicloud-auto-deploy-terraform-state-apne1"
echo "- CloudFront: E2GDU7Y7UGDV3S"
