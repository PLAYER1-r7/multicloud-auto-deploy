#!/bin/bash
set -e

echo "=== Simple SNS GCP Deployment Script ==="

# Check if gcloud is installed
if ! command -v gcloud &> /dev/null; then
    echo "Error: gcloud CLI is not installed"
    echo "Please install from: https://cloud.google.com/sdk/docs/install"
    exit 1
fi

# Check if project ID is set
if [ -z "$GCP_PROJECT_ID" ]; then
    echo "Error: GCP_PROJECT_ID environment variable is not set"
    echo "Usage: export GCP_PROJECT_ID=your-project-id && ./deploy.sh"
    exit 1
fi

echo "Project ID: $GCP_PROJECT_ID"

# Set project
gcloud config set project $GCP_PROJECT_ID

# Build functions
echo ""
echo "=== Building Cloud Functions ==="
cd functions
npm install
npm run build
cd ..

# Create functions.zip
echo ""
echo "=== Creating functions.zip ==="
zip -r functions.zip functions/dist functions/package.json functions/package-lock.json

# Deploy infrastructure
echo ""
echo "=== Deploying Infrastructure with Terraform ==="
cd ../../terraform/gcp/envs/simple-sns
tofu init
tofu apply -var="gcp_project_id=$GCP_PROJECT_ID"

# Get outputs
echo ""
echo "=== Terraform Outputs ==="
tofu output

# Build frontend
echo ""
echo "=== Building Frontend ==="
cd ../frontend
npm install
npm run build

# Get frontend bucket name
FRONTEND_BUCKET=$(cd ../../terraform/gcp/envs/simple-sns && tofu output -raw frontend_bucket)

# Upload frontend to Cloud Storage
echo ""
echo "=== Uploading Frontend to Cloud Storage ==="
gsutil -m rsync -r -d dist/ gs://$FRONTEND_BUCKET/

echo ""
echo "✅ Deployment Complete!"
echo "Frontend URL: https://storage.googleapis.com/$FRONTEND_BUCKET/index.html"
