# GCP Production Pulumi Deployment Plan

> **Date**: 2026-03-03 Session 2
> **Context**: Phase 2 - GCP production state drift resolution
> **Objective**: Execute `pulumi up --stack production` to resolve ManagedSslCertificate & URLMap state conflicts
> **Owner**: AI Agent (automated) / User approval required

---

## 📋 Deployment Overview

### Current State

| Component | Status | Details |
|-----------|--------|---------|
| **Code Changes** | ✅ Ready | `monitoring.py` billing budget flag implemented (PR #[pending]) |
| **GCP Credentials** | ✅ Ready | GitHub Actions secrets configured |
| **Pulumi Stack** | ⚠️ State Drift | Known: ManagedSslCertificate (400), URLMap (412) |
| **Monitoring** | ✅ Ready | Cloud Audit Logs, monitoring alerts configured |

### Deployment Target

```
Pulumi Stack:     production
Project:          ashnova
Region:           asia-northeast1
Configuration:    Pulumi.production.yaml
```

**Configuration Values (verified 2026-02-28)**:
```yaml
customDomain: www.gcp.ashnova.jp
alarmEmail: sat0sh1kawada@spa.nifty.com
monthlyBudgetUsd: "100"
enableAuditLogs: "true"
billingAccountId: 01F139-282A95-9BBA25
enableBillingBudget: "false"  # ← NEW (prevents IAM quota error)
```

---

## 🔧 Deployment Steps

### Step 1: Pre-flight Validation (Automated in GitHub Actions)

**File**: `.github/workflows/deploy-gcp.yml`

```bash
# 1. Authenticate to Google Cloud
#    Source: secrets.GCP_CREDENTIALS (base64-encoded service account JSON)

# 2. Set up Cloud SDK
#    Validates: gcloud CLI, project_id

# 3. Install Pulumi & dependencies
#    Command: pip install -r infrastructure/pulumi/gcp/requirements.txt

# 4. Validate Python syntax
#    Files: __main__.py, monitoring.py
```

**Expected Output**:
```
✅ gcloud authenticated (ashnova project)
✅ Pulumi CLI v3.224.0+ ready
✅ Python 3.13+ environment activated
✅ Git repo clean (main branch)
```

### Step 2: Stack Initialization (Idempotent)

**File**: `.github/workflows/deploy-gcp.yml`

```bash
pulumi login
pulumi stack select production 2>/dev/null || pulumi stack init production
pulumi config set gcp:project ashnova
pulumi config set gcp:region asia-northeast1
```

**Expected Output**:
```
Current stack: production
```

### Step 3: State Synchronization (Conflict Resolution)

**File**: `.github/workflows/deploy-gcp.yml`

**Critical for State Drift**:
```bash
# Remove SecretVersion from state (IAM permission issue)
pulumi state delete "urn:pulumi:production::multicloud-auto-deploy-gcp::gcp:secretmanager/secretVersion:SecretVersion::app-secret-version" \
  --yes || echo "✅ Already clean"

# Refresh state from actual GCP resources
# This resolves ManagedSslCertificate (400) and URLMap (412) conflicts
pulumi refresh --yes --stack production
```

**Why This Works**:
- GCP resources may have drifted from Pulumi state
- `pulumi refresh` compares real GCP state with Pulumi state
- Updates state to match reality without modifying resources
- Prevents "resource already exists" errors during `pulumi up`

**Expected Output**:
```
@ Refreshing update (production)...
@ Refreshing update...
Downloading plugins...
...
✅ Refresh complete (N resources unchanged)
```

### Step 4: Deployment (Main Change Execution)

**File**: `.github/workflows/deploy-gcp.yml`

```bash
pulumi up --yes --stack production
```

**What This Does**:
1. **Preview**: Compares desired state (Pulumi code) vs actual state (GCP)
2. **Plan**: Lists all create/update/delete operations
3. **Execute**: Applies changes (only if `--yes` flag set)

**Expected Resources** (~40-50 unchanged, 0-5 modified):
```
Outputs:
  cdn_https_url: https://www.gcp.ashnova.jp/
  firebase_project_id: ashnova
  function_name: multicloud-auto-deploy-production-api
  ...
```

**Known Issues During Deploy**:
- ⚠️ **ManagedSslCertificate state conflict** → Handled by refresh step
- ⚠️ **URLMap 412 precondition** → Handled by refresh step
- ⚠️ **billing_budget IAM error** → Disabled via `enableBillingBudget: false` flag

**Mitigation**: All known issues have fixes in place. Deploy should proceed smoothly.

### Step 5: Post-Deployment Validation

**File**: `.github/workflows/deploy-gcp.yml`

```bash
# Verify Cloud Function deployment
gcloud functions describe multicloud-auto-deploy-production-api \
  --region asia-northeast1 --gen2

# Verify frontend bucket
gsutil ls gs://ashnova-multicloud-auto-deploy-production-frontend/

# Verify CDN configuration
gcloud compute backend-buckets describe multicloud-auto-deploy-production-cdn-backend
```

**Expected Output**:
```
✅ Cloud Function: ACTIVE
✅ Frontend bucket: Exists, has index.html
✅ Backend bucket: Enabled CDN, HTTPS policy set
```

---

## ⚠️ Risk Assessment

| Risk | Severity | Mitigation |
|------|----------|-----------|
| SSL cert validation failure | 🔴 Critical | `--cert-manager-skip-validation` handled by refresh |
| URLMap precondition conflict | 🔴 Critical | `pulumi refresh` syncs state before `pulumi up` |
| IAM quota error (billing_budget) | 🟡 High | `enableBillingBudget: false` prevents resource creation |
| State divergence | 🟡 High | `pulumi refresh --yes` ensures clean state |
| Production downtime | 🟢 Low | CDN / Cloud Run auto-scale handles updates |

**Overall Risk**: 🟢 **LOW** (all known issues mitigated)

---

## 🚀 Deployment Execution Options

### Option A: Automated (GitHub Actions) — RECOMMENDED ✅

**Trigger**: Manual workflow dispatch or push to `main` branch

**Workflow**: `.github/workflows/deploy-gcp.yml`

```bash
# From GitHub UI:
# 1. Go to: Actions → "Deploy to GCP"
# 2. Click "Run workflow"
# 3. Select environment: "production"
# 4. Click "Run workflow"
```

**Advantages**:
- ✅ Automated credential injection
- ✅ Consistent environment (Ubuntu 24.04)
- ✅ Full audit trail (Actions logs)
- ✅ No local environment setup required

**Timeline**: ~5-10 minutes

---

### Option B: Manual (Local CLI) — NOT RECOMMENDED ⚠️

**Prerequisites**:
```bash
# 1. Set up GCP credentials (service account JSON)
export GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account.json

# 2. Set Pulumi token
export PULUMI_ACCESS_TOKEN=pul-xxxxx...

# 3. Install tools
pip install -r infrastructure/pulumi/gcp/requirements.txt
```

**Execution**:
```bash
cd infrastructure/pulumi/gcp

# 3a. Pre-flight check
bash ../../scripts/gcp-production-preflight.sh

# 3b. Sync state
pulumi refresh --yes --stack production

# 3c. Deploy
pulumi up --yes --stack production
```

**Disadvantages**:
- ⚠️ Credential management complexity
- ⚠️ Local environment may differ from CI
- ⚠️ Manual error handling required
- ❌ Not recommended for production changes

**Timeline**: ~15-20 minutes (including setup)

---

## 📊 Expected Outcomes

### Success Criteria

| Criteria | Expected | Verification |
|----------|----------|--------------|
| **Pulumi up status** | All changes applied (0 failures) | `pulumi stack outputs` |
| **SSL certificate** | ACTIVE (not PROVISIONING) | `gcloud compute ssl-certificates list` |
| **CDN endpoint** | HTTP 200 response | `curl https://www.gcp.ashnova.jp -I` |
| **Cloud Audit Logs** | ADMIN_READ/DATA_READ enabled | `gcloud projects get-iam-policy ashnova` |

### Post-Deployment Checklist

```
□ Pulumi up completes successfully (no 400/412 errors)
□ `pulumi stack outputs` shows all expected outputs
□ SSL certificate status: ACTIVE (in Cloud Console)
□ Frontend accessible: https://www.gcp.ashnova.jp (HTTP 200)
□ API Gateway headers include CORS (if applicable)
□ Cloud Audit Logs recording events (check within 5 min)
□ Alert notifications sent (if alarm email configured)
```

---

## 🔄 Rollback Plan

**If Deployment Fails**:

1. **Immediate**: Check deployment logs in GitHub Actions
   ```
   .github/workflows/deploy-gcp.yml → Run logs
   ```

2. **Diagnose**: Identify specific resource failure
   ```bash
   cd infrastructure/pulumi/gcp
   pulumi stack select production
   pulumi refresh --yes
   ```

3. **Recover**: Revert to last known good state
   ```bash
   # Option 1: Re-run pulumi refresh (safe)
   pulumi refresh --yes --stack production

   # Option 2: Manual resource fix in GCP Console (if needed)
   # Contact GCP support for persistent state issues
   ```

4. **Communicate**: Update [AI_AGENT_06_STATUS_JA.md](../docs/AI_AGENT_06_STATUS_JA.md) with incident details

---

## 📝 Deployment Record

**Status**: 🟡 PENDING (ready to execute)

**Last Updated**: 2026-03-03 Session 2
**Next Review**: After deployment execution

| Deployment # | Date | Status | Notes |
|--------------|------|--------|-------|
| #1 | 2026-03-03 | 🟡 READY | Awaiting manual trigger |

---

## 📞 Support & Escalation

**If Issues Occur**:

1. **GitHub Actions Failures**: Check workflow logs (Actions tab)
2. **GCP API Errors**: Check Cloud Logging (GCP Console)
3. **Pulumi State Issues**: Run `pulumi stack --show-ids` for debugging
4. **SSL Certificate Issues**: Check SSL certificate details in GCP Console

**Escalation Path**:
- Dev Team Lead
- Cloud Infrastructure Owner
- GCP Support (if persistent errors)

---

## ✅ Approval Sign-Off

| Role | Name | Approval | Date |
|------|------|----------|------|
| Code Review | [Pending] | ⏳ Awaiting | — |
| Cloud Admin | [Pending] | ⏳ Awaiting | — |
| Deployment | [Pending] | ⏳ Awaiting | — |

**Ready to Deploy**: After all sign-offs complete
