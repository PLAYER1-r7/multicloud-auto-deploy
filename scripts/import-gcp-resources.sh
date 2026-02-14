#!/bin/bash
# GCP既存リソースをTerraform Stateにインポートするスクリプト

set -e

# カラー定義
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# 設定
PROJECT_ID="${GCP_PROJECT_ID:-ashnova}"
ENVIRONMENT="${ENVIRONMENT:-staging}"
REGION="${GCP_REGION:-asia-northeast1}"
TERRAFORM_DIR="./infrastructure/terraform/gcp"

# リソース名のプレフィックス
PREFIX="mcad-${ENVIRONMENT}"

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  GCP Resource Import Script${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""
echo "Project ID:   $PROJECT_ID"
echo "Environment:  $ENVIRONMENT"
echo "Region:       $REGION"
echo "Prefix:       $PREFIX"
echo ""

# Terraform ディレクトリに移動
if [ ! -d "$TERRAFORM_DIR" ]; then
    echo -e "${RED}Error: Terraform directory not found: $TERRAFORM_DIR${NC}"
    exit 1
fi

cd "$TERRAFORM_DIR"

# Terraform初期化
echo -e "${YELLOW}Initializing Terraform...${NC}"
terraform init

# インポート関数
import_resource() {
    local resource_type=$1
    local resource_name=$2
    local resource_id=$3
    
    echo -e "\n${YELLOW}Importing: ${resource_type}.${resource_name}${NC}"
    echo "ID: $resource_id"
    
    # 既にインポート済みかチェック
    if terraform state show "${resource_type}.${resource_name}" &>/dev/null; then
        echo -e "${GREEN}✓ Already imported${NC}"
        return 0
    fi
    
    # インポート実行
    if terraform import \
        -var="project_id=$PROJECT_ID" \
        -var="environment=$ENVIRONMENT" \
        "${resource_type}.${resource_name}" \
        "$resource_id"; then
        echo -e "${GREEN}✓ Import successful${NC}"
        return 0
    else
        echo -e "${RED}✗ Import failed${NC}"
        return 1
    fi
}

# リソース存在確認関数
check_resource_exists() {
    local resource_type=$1
    local resource_name=$2
    
    case $resource_type in
        artifact_registry)
            gcloud artifacts repositories describe "$resource_name" \
                --location="$REGION" &>/dev/null
            ;;
        storage_bucket)
            gcloud storage buckets describe "gs://$resource_name" &>/dev/null
            ;;
        compute_address)
            gcloud compute addresses describe "$resource_name" \
                --global &>/dev/null
            ;;
        cloud_run_service)
            gcloud run services describe "$resource_name" \
                --region="$REGION" &>/dev/null
            ;;
        *)
            return 1
            ;;
    esac
}

# メイン処理
echo -e "\n${BLUE}Step 1: Checking existing resources${NC}"

# Artifact Registry
REPO_NAME="${PREFIX}-repo"
if check_resource_exists "artifact_registry" "$REPO_NAME"; then
    echo -e "${GREEN}✓ Found: Artifact Registry - $REPO_NAME${NC}"
    import_resource \
        "google_artifact_registry_repository" \
        "main" \
        "projects/${PROJECT_ID}/locations/${REGION}/repositories/${REPO_NAME}"
else
    echo -e "${YELLOW}⚠ Not found: Artifact Registry - $REPO_NAME${NC}"
fi

# Storage Bucket
BUCKET_NAME="${PREFIX}-frontend"
if check_resource_exists "storage_bucket" "$BUCKET_NAME"; then
    echo -e "${GREEN}✓ Found: Storage Bucket - $BUCKET_NAME${NC}"
    import_resource \
        "google_storage_bucket" \
        "frontend" \
        "$BUCKET_NAME"
else
    echo -e "${YELLOW}⚠ Not found: Storage Bucket - $BUCKET_NAME${NC}"
fi

# Global Address
ADDRESS_NAME="${PREFIX}-frontend-ip"
if check_resource_exists "compute_address" "$ADDRESS_NAME"; then
    echo -e "${GREEN}✓ Found: Global Address - $ADDRESS_NAME${NC}"
    import_resource \
        "google_compute_global_address" \
        "frontend" \
        "projects/${PROJECT_ID}/global/addresses/${ADDRESS_NAME}"
else
    echo -e "${YELLOW}⚠ Not found: Global Address - $ADDRESS_NAME${NC}"
fi

# Firestore Database
echo -e "\n${YELLOW}Importing: Firestore Database (default)${NC}"
import_resource \
    "google_firestore_database" \
    "main" \
    "projects/${PROJECT_ID}/databases/(default)"

# Cloud Run Service
SERVICE_NAME="${PREFIX}-api"
if check_resource_exists "cloud_run_service" "$SERVICE_NAME"; then
    echo -e "${GREEN}✓ Found: Cloud Run Service - $SERVICE_NAME${NC}"
    import_resource \
        "google_cloud_run_v2_service" \
        "api" \
        "projects/${PROJECT_ID}/locations/${REGION}/services/${SERVICE_NAME}"
else
    echo -e "${YELLOW}⚠ Not found: Cloud Run Service - $SERVICE_NAME${NC}"
fi

# Backend Bucket
BACKEND_BUCKET="${PREFIX}-backend"
echo -e "\n${YELLOW}Importing: Backend Bucket - $BACKEND_BUCKET${NC}"
import_resource \
    "google_compute_backend_bucket" \
    "frontend" \
    "$BACKEND_BUCKET"

# URL Map
URLMAP_NAME="${PREFIX}-urlmap"
echo -e "\n${YELLOW}Importing: URL Map - $URLMAP_NAME${NC}"
import_resource \
    "google_compute_url_map" \
    "frontend" \
    "projects/${PROJECT_ID}/global/urlMaps/${URLMAP_NAME}"

# HTTP Proxy
PROXY_NAME="${PREFIX}-http-proxy"
echo -e "\n${YELLOW}Importing: HTTP Proxy - $PROXY_NAME${NC}"
import_resource \
    "google_compute_target_http_proxy" \
    "frontend" \
    "projects/${PROJECT_ID}/global/targetHttpProxies/${PROXY_NAME}"

# Forwarding Rule
RULE_NAME="${PREFIX}-http-rule"
echo -e "\n${YELLOW}Importing: Forwarding Rule - $RULE_NAME${NC}"
import_resource \
    "google_compute_global_forwarding_rule" \
    "frontend_http" \
    "projects/${PROJECT_ID}/global/forwardingRules/${RULE_NAME}"

# Storage Bucket ACL
echo -e "\n${YELLOW}Importing: Storage Bucket ACL${NC}"
import_resource \
    "google_storage_default_object_acl" \
    "frontend_public" \
    "$BUCKET_NAME"

# 結果確認
echo -e "\n${BLUE}Step 2: Verifying imported resources${NC}"
terraform state list

echo -e "\n${BLUE}Step 3: Checking for configuration drift${NC}"
terraform plan \
    -var="project_id=$PROJECT_ID" \
    -var="environment=$ENVIRONMENT"

echo -e "\n${GREEN}========================================${NC}"
echo -e "${GREEN}  Import Complete!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo "Next steps:"
echo "1. Review the terraform plan output above"
echo "2. If everything looks good, commit the state:"
echo "   git add ${TERRAFORM_DIR}/.terraform.lock.hcl"
echo "3. The state is already persisted in GCS"
echo ""
