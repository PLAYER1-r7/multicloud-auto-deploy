#!/bin/bash

# GCP Production Pulumi Deployment Plan
# Pre-flight checks and step-by-step deployment guide
# This script validates the environment before attempting: pulumi up --stack production

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

PROJECT="ashnova"
REGION="asia-northeast1"
STACK="production"

# Counters
CHECKS_PASS=0
CHECKS_FAIL=0

# Helper functions
log_header() {
    echo ""
    echo -e "${BLUE}======================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}======================================${NC}"
    echo ""
}

log_check() {
    echo -e "${BLUE}→${NC}  $1"
}

log_pass() {
    echo -e "${GREEN}✅${NC} $1"
    ((CHECKS_PASS++))
}

log_fail() {
    echo -e "${RED}❌${NC} $1"
    ((CHECKS_FAIL++))
}

log_warn() {
    echo -e "${YELLOW}⚠️${NC}  $1"
}

log_info() {
    echo -e "${BLUE}ℹ${NC}  $1"
}

# ========================================
# Check 1: CLI Tools
# ========================================
log_header "Pre-flight Check 1: CLI Tools"

log_check "Checking required CLI tools..."

if command -v pulumi &> /dev/null; then
    PULUMI_VERSION=$(pulumi version)
    log_pass "pulumi: $PULUMI_VERSION"
else
    log_fail "pulumi: NOT FOUND (install from https://pulumi.com/docs/install)"
fi

if command -v gcloud &> /dev/null; then
    GCP_VERSION=$(gcloud --version | head -1)
    log_pass "gcloud: $GCP_VERSION"
else
    log_fail "gcloud: NOT FOUND (install from https://cloud.google.com/sdk/docs/install)"
fi

if command -v git &> /dev/null; then
    GIT_VERSION=$(git --version)
    log_pass "git: $GIT_VERSION"
else
    log_fail "git: NOT FOUND"
fi

# ========================================
# Check 2: Authentication
# ========================================
log_header "Pre-flight Check 2: Authentication"

log_check "Checking Pulumi authentication..."
if pulumi whoami &> /dev/null; then
    PULUMI_USER=$(pulumi whoami)
    log_pass "Pulumi user: $PULUMI_USER"
else
    log_fail "Pulumi: NOT AUTHENTICATED"
    log_warn "Run: pulumi login"
fi

log_check "Checking GCP authentication..."
if gcloud auth list --filter=status:ACTIVE --format="value(account)" &> /dev/null; then
    GCP_ACCOUNT=$(gcloud auth list --filter=status:ACTIVE --format="value(account)" | head -1)
    log_pass "GCP account: $GCP_ACCOUNT"
else
    log_fail "GCP: NOT AUTHENTICATED"
    log_warn "Run: gcloud auth login"
fi

log_check "Checking GCP project..."
CURRENT_PROJECT=$(gcloud config get-value project 2>/dev/null || echo "")
if [ "$CURRENT_PROJECT" = "$PROJECT" ]; then
    log_pass "GCP project: $PROJECT"
else
    log_fail "GCP project: Expected $PROJECT, got $CURRENT_PROJECT"
    log_warn "Run: gcloud config set project $PROJECT"
fi

# ========================================
# Check 3: Repository State
# ========================================
log_header "Pre-flight Check 3: Repository State"

log_check "Checking git branch..."
CURRENT_BRANCH=$(git rev-parse --abbrev-ref HEAD)
if [ "$CURRENT_BRANCH" = "main" ]; then
    log_pass "Branch: $CURRENT_BRANCH"
else
    log_warn "Branch: $CURRENT_BRANCH (expected: main)"
fi

log_check "Checking for uncommitted changes..."
if [ -z "$(git status --porcelain)" ]; then
    log_pass "Working directory: CLEAN"
else
    log_fail "Working directory: HAS UNCOMMITTED CHANGES"
    git status --short
fi

log_check "Checking git remote..."
REMOTE_URL=$(git remote get-url origin)
if [[ "$REMOTE_URL" == *"multicloud-auto-deploy"* ]]; then
    log_pass "Remote: $REMOTE_URL"
else
    log_fail "Remote: Not recognized ($REMOTE_URL)"
fi

# ========================================
# Check 4: Pulumi Stack
# ========================================
log_header "Pre-flight Check 4: Pulumi Stack"

log_check "Checking Pulumi stack selection..."
cd infrastructure/pulumi/gcp

if [ -f "Pulumi.${STACK}.yaml" ]; then
    log_pass "Stack config: Pulumi.${STACK}.yaml exists"
else
    log_fail "Stack config: Pulumi.${STACK}.yaml NOT FOUND"
fi

# Try to select the stack
if pulumi stack select "$STACK" 2>&1 | grep -q "Current stack"; then
    log_pass "Stack: $STACK selected"
else
    log_fail "Stack: Could not select $STACK"
fi

# ========================================
# Check 5: Python Dependencies
# ========================================
log_header "Pre-flight Check 5: Python Dependencies"

log_check "Checking Python environment..."
if [ -f "requirements.txt" ]; then
    log_pass "requirements.txt: FOUND"
    PYTHON_PACKAGE_COUNT=$(grep -c "^[^#]" requirements.txt)
    log_info "Python packages: $PYTHON_PACKAGE_COUNT"
else
    log_fail "requirements.txt: NOT FOUND"
fi

# ========================================
# Check 6: Known Issues & Workarounds
# ========================================
log_header "Pre-flight Check 6: Known Issues & Workarounds"

log_info "Issue 1: ManagedSslCertificate 400 error"
log_info "  Workaround: pulumi refresh --yes (already in workflow)"
log_info "  Status: READY (refresh step exists)"

log_info "Issue 2: URLMap 412 precondition failed"
log_info "  Workaround: pulumi refresh --yes (already in workflow)"
log_info "  Status: READY (refresh step exists)"

log_info "Issue 3: billing_budget IAM permission error"
log_info "  Workaround: enableBillingBudget=false (already configured)"
log_info "  Status: READY (config in Pulumi.production.yaml)"

log_check "Checking billing budget flag..."
if grep -q "enableBillingBudget.*false" Pulumi.production.yaml; then
    log_pass "Billing budget: DISABLED (to avoid IAM errors)"
else
    log_warn "Billing budget: Flag not found or enabled (may cause errors)"
fi

# ========================================
# Summary
# ========================================
log_header "Pre-flight Check Summary"

TOTAL_CHECKS=$((CHECKS_PASS + CHECKS_FAIL))
echo -e "${GREEN}✅ Passed: $CHECKS_PASS${NC}"
echo -e "${RED}❌ Failed: $CHECKS_FAIL${NC}"
echo -e "Total: $TOTAL_CHECKS"
echo ""

if [ $CHECKS_FAIL -eq 0 ]; then
    echo -e "${GREEN}All pre-flight checks PASSED!${NC}"
    echo ""
    echo "Next steps:"
    echo "1. Review deploy plan: https://github.com/ashnova/multicloud-auto-deploy/blob/main/docs/TECH_STRATEGY_2026.md"
    echo "2. Option A (Recommended): Trigger GitHub Actions workflow"
    echo "   → .github/workflows/deploy-gcp.yml"
    echo "   → Environment: production"
    echo ""
    echo "3. Option B (Manual): Run locally"
    echo "   → cd infrastructure/pulumi/gcp"
    echo "   → pulumi refresh --yes --stack production"
    echo "   → pulumi up --yes --stack production"
    echo ""
    echo "⚠️  WARNING: This will modify production infrastructure in GCP!"
    echo "    Ensure you have proper approvals before proceeding."
    exit 0
else
    echo -e "${RED}Some pre-flight checks FAILED!${NC}"
    echo "Please fix the issues above before proceeding."
    exit 1
fi
