#!/bin/bash
# ========================================
# Script Name: deploy-static-site.sh
# Description: Deploy cloud-specific landing pages to 3 clouds (AWS / Azure / GCP)
#              Each cloud gets its own themed HTML from static-site/{aws,azure,gcp}/
#              Landing pages served at /  and SNS app served at /sns/  (same CDN).
#
# Usage:
#   ./scripts/deploy-static-site.sh [ENVIRONMENT] [CLOUD]
#
# Arguments:
#   ENVIRONMENT  - production | staging  (default: production)
#   CLOUD        - aws | azure | gcp | all  (default: all)
#
# URL structure after deploy:
#   AWS  :  https://aws.yourdomain.com/        (landing)
#           https://aws.yourdomain.com/sns/    (SNS app)
#   Azure:  https://azure.yourdomain.com/
#           https://azure.yourdomain.com/sns/
#   GCP  :  https://gcp.yourdomain.com/
#           https://gcp.yourdomain.com/sns/
#
# Prerequisites:
#   AWS:   aws CLI configured with deployment credentials
#   Azure: az CLI logged in (az login)
#   GCP:   gcloud CLI authenticated (gcloud auth login)
#   Pulumi: stacks already deployed (pulumi up)
#
# ========================================

set -euo pipefail

# ── Arguments ──────────────────────────────────────────────────────────────────
ENVIRONMENT="${1:-production}"
CLOUD="${2:-all}"
PROJECT_NAME="multicloud-auto-deploy"

# ── Paths ──────────────────────────────────────────────────────────────────────
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
WORKSPACE_ROOT="$(cd "${PROJECT_ROOT}/.." && pwd)"
STATIC_SITE_DIR="${WORKSPACE_ROOT}/static-site"

PULUMI_AWS_DIR="${PROJECT_ROOT}/infrastructure/pulumi/aws"
PULUMI_AZURE_DIR="${PROJECT_ROOT}/infrastructure/pulumi/azure"
PULUMI_GCP_DIR="${PROJECT_ROOT}/infrastructure/pulumi/gcp"

# ── Colors ─────────────────────────────────────────────────────────────────────
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

info()    { echo -e "${BLUE}[INFO]${NC}  $*"; }
success() { echo -e "${GREEN}[OK]${NC}    $*"; }
warn()    { echo -e "${YELLOW}[WARN]${NC}  $*"; }
error()   { echo -e "${RED}[ERROR]${NC} $*" >&2; }

# ── Validate ───────────────────────────────────────────────────────────────────
if [[ ! -d "${STATIC_SITE_DIR}" ]]; then
  error "static-site directory not found: ${STATIC_SITE_DIR}"
  exit 1
fi

echo "========================================"
echo "  Static Landing Page Deploy"
echo "  Environment : ${ENVIRONMENT}"
echo "  Cloud       : ${CLOUD}"
echo "  Source      : ${STATIC_SITE_DIR}/{aws,azure,gcp}/"
echo "========================================"
echo

# ==========================================
# AWS: S3 sync + CloudFront invalidation
# ==========================================
deploy_aws() {
  info "=== AWS ====================================================="
  info "Fetching Pulumi outputs (stack: ${ENVIRONMENT}) ..."

  cd "${PULUMI_AWS_DIR}"
  pulumi stack select "${ENVIRONMENT}" --non-interactive 2>/dev/null || true

  LANDING_BUCKET=$(pulumi stack output landing_bucket_name 2>/dev/null || echo "")
  LANDING_CF_ID=$(pulumi stack output landing_cloudfront_id 2>/dev/null || echo "")
  LANDING_CF_URL=$(pulumi stack output landing_cloudfront_url 2>/dev/null || echo "")
  SNS_URL=$(pulumi stack output sns_url 2>/dev/null || echo "")
  CUSTOM_DOMAIN=$(pulumi stack output landing_custom_domain 2>/dev/null || echo "")

  if [[ -z "${LANDING_BUCKET}" ]]; then
    error "AWS: landing_bucket_name output not found. Run 'pulumi up' first."
    return 1
  fi

  info "Bucket        : ${LANDING_BUCKET}"
  info "CloudFront ID : ${LANDING_CF_ID}"
  info "Landing URL   : ${LANDING_CF_URL}"
  info "SNS URL       : ${SNS_URL}"
  [[ -n "${CUSTOM_DOMAIN}" ]] && info "Custom domain : https://${CUSTOM_DOMAIN}  (SNS: https://${CUSTOM_DOMAIN}/sns/)"

  # Upload AWS-specific landing page files
  info "Syncing static-site/aws/ to s3://${LANDING_BUCKET}/ ..."
  aws s3 sync "${STATIC_SITE_DIR}/aws/" "s3://${LANDING_BUCKET}/" \
    --delete \
    --cache-control "max-age=300" \
    --content-type "text/html; charset=utf-8" \
    --exclude "*.sh" \
    --exclude ".DS_Store"

  # Invalidate CloudFront cache
  if [[ -n "${LANDING_CF_ID}" ]]; then
    info "Invalidating CloudFront cache (${LANDING_CF_ID}) ..."
    INVALIDATION_ID=$(aws cloudfront create-invalidation \
      --distribution-id "${LANDING_CF_ID}" \
      --paths "/*" \
      --query "Invalidation.Id" \
      --output text)
    success "CloudFront invalidation created: ${INVALIDATION_ID}"
  fi

  success "AWS deploy complete"
  success "  Landing : ${LANDING_CF_URL}"
  success "  SNS app : ${SNS_URL}"
  echo
}

# ==========================================
# Azure: Blob upload + static website enable + Front Door purge
# ==========================================
deploy_azure() {
  info "=== Azure ==================================================="
  info "Fetching Pulumi outputs (stack: ${ENVIRONMENT}) ..."

  cd "${PULUMI_AZURE_DIR}"
  pulumi stack select "${ENVIRONMENT}" --non-interactive 2>/dev/null || true

  LANDING_STORAGE=$(pulumi stack output landing_storage_name 2>/dev/null || echo "")
  LANDING_FD_URL=$(pulumi stack output landing_frontdoor_url 2>/dev/null || echo "")
  SNS_URL=$(pulumi stack output sns_url 2>/dev/null || echo "")
  RESOURCE_GROUP=$(pulumi stack output resource_group_name 2>/dev/null || echo "")
  FD_EP_NAME=$(pulumi stack output frontdoor_endpoint_name 2>/dev/null || echo "")
  CUSTOM_DOMAIN=$(pulumi stack output landing_custom_domain 2>/dev/null || echo "")

  if [[ -z "${LANDING_STORAGE}" ]]; then
    error "Azure: landing_storage_name output not found. Run 'pulumi up' first."
    return 1
  fi

  info "Storage Account : ${LANDING_STORAGE}"
  info "Landing URL     : ${LANDING_FD_URL}"
  info "SNS URL         : ${SNS_URL}"
  [[ -n "${CUSTOM_DOMAIN}" ]] && info "Custom domain   : https://${CUSTOM_DOMAIN}"

  # Enable static website hosting on landing storage account
  info "Enabling static website hosting on ${LANDING_STORAGE} ..."
  az storage blob service-properties update \
    --account-name "${LANDING_STORAGE}" \
    --static-website \
    --index-document "index.html" \
    --404-document "error.html" \
    --auth-mode login 2>/dev/null || \
  az storage blob service-properties update \
    --account-name "${LANDING_STORAGE}" \
    --static-website \
    --index-document "index.html" \
    --404-document "error.html"

  # Upload Azure-specific landing page files
  info "Uploading static-site/azure/ to ${LANDING_STORAGE}/\$web ..."
  az storage blob upload-batch \
    --account-name "${LANDING_STORAGE}" \
    --destination "\$web" \
    --source "${STATIC_SITE_DIR}/azure/" \
    --overwrite \
    --content-type "text/html; charset=utf-8" \
    --content-cache-control "max-age=300"

  # Purge Front Door cache for the single endpoint
  if [[ -n "${RESOURCE_GROUP}" && -n "${FD_EP_NAME}" ]]; then
    FD_PROFILE_NAME="${PROJECT_NAME}-${ENVIRONMENT}-fd"
    info "Purging Front Door cache (${FD_PROFILE_NAME} / ${FD_EP_NAME}) ..."
    az afd endpoint purge \
      --resource-group "${RESOURCE_GROUP}" \
      --profile-name "${FD_PROFILE_NAME}" \
      --endpoint-name "${FD_EP_NAME}" \
      --content-paths "/*" 2>/dev/null || warn "Front Door purge skipped (may not be supported on free tier)"
  fi

  success "Azure deploy complete"
  success "  Landing : ${LANDING_FD_URL}"
  success "  SNS app : ${SNS_URL}"
  echo
}

# ==========================================
# GCP: gsutil copy + CDN cache invalidation
# ==========================================
deploy_gcp() {
  info "=== GCP ====================================================="
  info "Fetching Pulumi outputs (stack: ${ENVIRONMENT}) ..."

  cd "${PULUMI_GCP_DIR}"
  pulumi stack select "${ENVIRONMENT}" --non-interactive 2>/dev/null || true

  LANDING_BUCKET=$(pulumi stack output landing_bucket 2>/dev/null || echo "")
  LANDING_URL=$(pulumi stack output landing_url 2>/dev/null || echo "")
  SNS_URL=$(pulumi stack output sns_url 2>/dev/null || echo "")
  CUSTOM_DOMAIN=$(pulumi stack output landing_custom_domain 2>/dev/null || echo "")
  GCP_PROJECT=$(pulumi stack output project_id 2>/dev/null || echo "")

  if [[ -z "${LANDING_BUCKET}" ]]; then
    error "GCP: landing_bucket output not found. Run 'pulumi up' first."
    return 1
  fi

  info "Bucket        : ${LANDING_BUCKET}"
  info "Landing URL   : ${LANDING_URL}"
  info "SNS URL       : ${SNS_URL}"
  [[ -n "${CUSTOM_DOMAIN}" ]] && info "Custom domain : https://${CUSTOM_DOMAIN}"

  # Upload GCP-specific landing page files
  info "Uploading static-site/gcp/ to gs://${LANDING_BUCKET}/ ..."
  gsutil -m -h "Cache-Control:public, max-age=300" \
    cp -r "${STATIC_SITE_DIR}/gcp/"* "gs://${LANDING_BUCKET}/"

  # Set Content-Type explicitly for HTML files
  gsutil -m setmeta \
    -h "Content-Type:text/html; charset=utf-8" \
    -h "Cache-Control:public, max-age=300" \
    "gs://${LANDING_BUCKET}/*.html"

  # Invalidate Cloud CDN cache (shared URL map)
  if [[ -n "${GCP_PROJECT}" ]]; then
    info "Invalidating Cloud CDN cache for landing backend ..."
    gcloud compute url-maps invalidate-cdn-cache \
      "${PROJECT_NAME}-${ENVIRONMENT}-cdn-urlmap" \
      --path "/*" \
      --project "${GCP_PROJECT}" \
      --async 2>/dev/null || warn "CDN cache invalidation skipped"
  fi

  success "GCP deploy complete"
  success "  Landing : ${LANDING_URL}"
  success "  SNS app : ${SNS_URL}"
  [[ -n "${CUSTOM_DOMAIN}" ]] && info "Note: SSL certificate provisioning takes 10-60 minutes after DNS A record is set."
  echo
}

# ==========================================
# Main
# ==========================================
case "${CLOUD}" in
  aws)   deploy_aws   ;;
  azure) deploy_azure ;;
  gcp)   deploy_gcp   ;;
  all)
    deploy_aws   || true
    deploy_azure || true
    deploy_gcp   || true
    ;;
  *)
    error "Unknown cloud: ${CLOUD}. Use: aws | azure | gcp | all"
    exit 1
    ;;
esac

echo "========================================"
success "Static site deploy finished!"
echo "========================================"
echo
echo "Next steps (if using custom domains):"
echo ""
echo "  AWS:"
echo "    1. Request ACM certificate in us-east-1:"
echo "       aws acm request-certificate --domain-name aws.yourdomain.com --validation-method DNS --region us-east-1"
echo "    2. Add CNAME for DNS validation"
echo "    3. Set Pulumi config:"
echo "       cd infrastructure/pulumi/aws"
echo "       pulumi config set staticSiteDomain aws.yourdomain.com"
echo "       pulumi config set staticSiteAcmCertificateArn arn:aws:acm:us-east-1:ACCOUNT:certificate/ID"
echo "       pulumi up"
echo "    4. Add DNS CNAME: aws.yourdomain.com → <landing_cloudfront_domain output>"
echo "    URLs: https://aws.yourdomain.com/        (landing)"
echo "          https://aws.yourdomain.com/sns/    (SNS app)"
echo ""
echo "  Azure:"
echo "    1. Set Pulumi config:"
echo "       cd infrastructure/pulumi/azure"
echo "       pulumi config set staticSiteDomain azure.yourdomain.com"
echo "       pulumi up"
echo "    2. Add DNS CNAME: azure.yourdomain.com → <frontdoor_hostname output>"
echo "       (Managed certificate is auto-provisioned by Front Door)"
echo "    URLs: https://azure.yourdomain.com/       (landing)"
echo "          https://azure.yourdomain.com/sns/   (SNS app)"
echo ""
echo "  GCP:"
echo "    1. Set Pulumi config:"
echo "       cd infrastructure/pulumi/gcp"
echo "       pulumi config set customDomain gcp.yourdomain.com"
echo "       pulumi config set staticSiteDomain gcp.yourdomain.com"
echo "       pulumi up"
echo "    2. Add DNS A record: gcp.yourdomain.com → <cdn_ip_address output>"
echo "       (Managed SSL certificate takes 10-60 minutes after DNS is set)"
echo "    URLs: https://gcp.yourdomain.com/        (landing)"
echo "          https://gcp.yourdomain.com/sns/    (SNS app)"
echo ""
