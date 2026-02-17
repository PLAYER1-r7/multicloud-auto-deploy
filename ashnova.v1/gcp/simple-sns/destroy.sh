#!/bin/bash
set -euo pipefail

SCRIPT_DIR=$(cd "$(dirname "$0")" && pwd)

echo "=== Simple SNS GCP Destroy ==="

# Check if gcloud is installed
if ! command -v gcloud &> /dev/null; then
  echo "Error: gcloud CLI is not installed"
  echo "Please install from: https://cloud.google.com/sdk/docs/install"
  exit 1
fi

# Check if tofu is installed
if ! command -v tofu &> /dev/null; then
  echo "Error: OpenTofu (tofu) is not installed"
  exit 1
fi

# Check if project ID is set
if [ -z "${GCP_PROJECT_ID:-}" ]; then
  echo "Error: GCP_PROJECT_ID environment variable is not set"
  echo "Usage: export GCP_PROJECT_ID=your-project-id && ./destroy.sh"
  exit 1
fi

echo "Project ID: $GCP_PROJECT_ID"

gcloud config set project "$GCP_PROJECT_ID"

if [ "${DELETE_FIRESTORE:-false}" = "true" ]; then
  if [ "${CONFIRM_DELETE:-}" != "YES" ]; then
    echo "Error: CONFIRM_DELETE=YES is required to delete Firestore data"
    echo "Usage: DELETE_FIRESTORE=true CONFIRM_DELETE=YES ./destroy.sh"
    exit 1
  fi
  echo "=== Deleting Firestore documents (all collections) ==="
  gcloud firestore bulk-delete --collection-ids="posts" --database="(default)" --project "$GCP_PROJECT_ID" --quiet
fi

echo "=== Destroying Infrastructure with OpenTofu ==="
cd "$SCRIPT_DIR/../../terraform/gcp/envs/simple-sns"
tofu init
tofu destroy -auto-approve

echo "✅ Destroy Complete!"
