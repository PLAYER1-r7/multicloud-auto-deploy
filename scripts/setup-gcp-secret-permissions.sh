#!/bin/bash

# GCP Secret Manager Permissions Setup Script
# This script grants Secret Manager access to the GitHub Actions service account

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}GCP Secret Manager Permissions Setup${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""

# Check if GCP_PROJECT_ID is set
if [ -z "$GCP_PROJECT_ID" ]; then
    echo -e "${RED}Error: GCP_PROJECT_ID environment variable is not set${NC}"
    echo "Please set it with: export GCP_PROJECT_ID=your-project-id"
    exit 1
fi

PROJECT_ID=$GCP_PROJECT_ID

echo -e "${YELLOW}Project ID: $PROJECT_ID${NC}"
echo ""

# Get the current authenticated user/service account
CURRENT_ACCOUNT=$(gcloud config get-value account 2>/dev/null)
echo -e "${YELLOW}Current account: $CURRENT_ACCOUNT${NC}"
echo ""

# Option 1: Grant to specific service account (if known)
if [ -n "$SERVICE_ACCOUNT_EMAIL" ]; then
    echo -e "${YELLOW}Granting Secret Manager access to: $SERVICE_ACCOUNT_EMAIL${NC}"
    
    gcloud projects add-iam-policy-binding $PROJECT_ID \
        --member="serviceAccount:$SERVICE_ACCOUNT_EMAIL" \
        --role="roles/secretmanager.secretAccessor" \
        --condition=None
    
    echo -e "${GREEN}✅ Granted roles/secretmanager.secretAccessor${NC}"
else
    echo -e "${YELLOW}SERVICE_ACCOUNT_EMAIL not set, skipping specific service account grant${NC}"
fi

# Option 2: Grant to default compute service account (commonly used)
echo ""
echo -e "${YELLOW}Granting Secret Manager access to default compute service account${NC}"

COMPUTE_SA="${PROJECT_ID}-compute@developer.gserviceaccount.com"
gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:$COMPUTE_SA" \
    --role="roles/secretmanager.secretAccessor" \
    --condition=None || echo -e "${YELLOW}⚠️  Compute service account may not exist${NC}"

# Option 3: Grant to App Engine default service account
echo ""
echo -e "${YELLOW}Granting Secret Manager access to App Engine default service account${NC}"

APP_ENGINE_SA="${PROJECT_ID}@appspot.gserviceaccount.com"
gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:$APP_ENGINE_SA" \
    --role="roles/secretmanager.secretAccessor" \
    --condition=None || echo -e "${YELLOW}⚠️  App Engine service account may not exist${NC}"

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Permissions setup complete!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo -e "${YELLOW}Verification:${NC}"
echo "Run the following to verify IAM bindings:"
echo "  gcloud projects get-iam-policy $PROJECT_ID --flatten='bindings[].members' --filter='bindings.role:roles/secretmanager.secretAccessor'"
echo ""
echo -e "${YELLOW}For GitHub Actions:${NC}"
echo "If using a custom service account for GitHub Actions, run:"
echo "  export SERVICE_ACCOUNT_EMAIL=your-sa@$PROJECT_ID.iam.gserviceaccount.com"
echo "  $0"
