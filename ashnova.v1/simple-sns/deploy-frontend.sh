#!/bin/bash
set -e

echo "=== Building React App ==="
npm run build:frontend

echo ""
echo "=== Getting S3 bucket name from OpenTofu ==="
BUCKET_NAME=$(cd "$(dirname "$0")" && tofu output -raw frontend_bucket_name)
echo "S3 Bucket: $BUCKET_NAME"

echo ""
echo "=== Getting CloudFront Distribution ID from OpenTofu ==="
DISTRIBUTION_ID=$(cd "$(dirname "$0")" && tofu output -raw cloudfront_distribution_id)
echo "CloudFront Distribution ID: $DISTRIBUTION_ID"

echo ""
echo "=== Uploading to S3 ==="
aws s3 sync dist-frontend/ s3://$BUCKET_NAME/ --delete

echo ""
echo "=== Invalidating CloudFront Cache ==="
aws cloudfront create-invalidation --distribution-id $DISTRIBUTION_ID --paths "/*" --output text

echo ""
echo "✅ Deploy completed successfully!"
echo "🌐 URL: https://sns.adawak.net"
