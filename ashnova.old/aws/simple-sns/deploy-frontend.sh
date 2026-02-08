#!/bin/bash
set -e

echo "=== Building React App ==="
npm run build:frontend

echo ""
TF_OUTPUT_DIR="$(dirname "$0")/../../terraform/aws/envs/simple-sns"

echo "=== Getting S3 bucket name from OpenTofu ==="
BUCKET_NAME=$(cd "$TF_OUTPUT_DIR" && tofu output -raw frontend_bucket_name 2>/dev/null || true)
if [ -z "$BUCKET_NAME" ] || [[ "$BUCKET_NAME" == *"Warning:"* ]]; then
	BUCKET_NAME=$(grep -m1 'bucket = ' "$(dirname "$0")/../../terraform/aws/elements/merged/simple-sns-frontend.tf" | awk -F '"' '{print $2}')
fi
echo "S3 Bucket: $BUCKET_NAME"

echo ""
echo "=== Getting CloudFront Distribution ID from OpenTofu ==="
DISTRIBUTION_ID=$(cd "$TF_OUTPUT_DIR" && tofu output -raw cloudfront_distribution_id 2>/dev/null || true)
if [ -z "$DISTRIBUTION_ID" ] || [[ "$DISTRIBUTION_ID" == *"Warning:"* ]]; then
	DISTRIBUTION_ID=$(aws cloudfront list-distributions \
		--query "DistributionList.Items[?contains(Origins.Items[0].DomainName, '${BUCKET_NAME}')].Id | [0]" \
		--output text)
fi
echo "CloudFront Distribution ID: $DISTRIBUTION_ID"

echo ""
echo "=== Uploading to S3 ==="
aws s3 sync dist-frontend/ s3://$BUCKET_NAME/ --delete

echo ""
echo "=== Invalidating CloudFront Cache ==="
aws cloudfront create-invalidation --distribution-id $DISTRIBUTION_ID --paths "/*" --output text

echo ""
echo "✅ Deploy completed successfully!"
echo "🌐 URL: https://sns.aws.ashnova.jp"
