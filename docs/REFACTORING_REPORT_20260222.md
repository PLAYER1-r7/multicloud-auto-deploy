# Refactoring & Infrastructure Fix Report — 2026-02-22

## Overview

This report documents all infrastructure improvements, CI/CD refactoring, and bug fixes applied
to the `multicloud-auto-deploy` project on February 22, 2026. The changes affect three cloud
providers (AWS, Azure, GCP) across both `main` (production) and `develop` (staging) branches.

---

## 1. Azure Front Door — SPA URL Rewrite Rule

### Problem

React SPA deep-links (`/sns/login`, `/sns/posts`, etc.) returned **HTTP 404** when accessed
directly via Azure Front Door (AFD). AFD was forwarding requests to the backend Function App
instead of rewriting the URL to serve `index.html` from Blob Storage.

### Root Cause

AFD Standard SKU has no native SPA fallback. The only solution is a **RuleSet with a URL Rewrite
Action** that rewrites all non-static-asset requests under `/sns/*` to `/sns/index.html`.

### Solution

Added `spa_rule_set` and `spa_rewrite_rule` to `infrastructure/pulumi/azure/__main__.py`:

```python
spa_rule_set = cdn.RuleSet(
    "spa-rule-set",
    rule_set_name="SpaRuleSet",   # alphanumeric only — Azure requirement
    ...
)

spa_rewrite_rule = cdn.Rule(
    "spa-rewrite-rule",
    rule_name="SpaIndexHtmlRewrite",
    conditions=[
        # Condition 1: URL path starts with /sns/
        cdn.DeliveryRuleRequestUriConditionArgs(...),
        # Condition 2: Accept header contains text/html (browser navigation)
        cdn.DeliveryRuleRequestHeaderConditionArgs(...),
        # Condition 3: URL does NOT end with a static asset extension
        cdn.DeliveryRuleRequestUriConditionArgs(
            parameters=cdn.RequestUriMatchConditionParametersArgs(
                operator="EndsWith",
                negate_condition=True,
                match_values=[
                    ".html", ".js", ".css", ".png", ".svg",
                    ".ico", ".json", ".woff", ".woff2", ".map"
                ],   # exactly 10 values — Azure AFD limit per condition
            )
        ),
    ],
    actions=[
        cdn.DeliveryRuleUrlRewriteActionArgs(
            parameters=cdn.UrlRewriteActionParametersArgs(
                source_pattern="/sns/",
                destination="/sns/index.html",
                preserve_unmatched_path=False,
            )
        )
    ],
)
```

### CI/CD Debug Loop (5 runs)

| Run  | Branch | Error                                             | Fix Applied                                                                                            |
| ---- | ------ | ------------------------------------------------- | ------------------------------------------------------------------------------------------------------ |
| #198 | main   | `ImportError: DeliveryRuleUrlRewriteActionArgs`   | Changed to `UrlRewriteActionArgs`                                                                      |
| #199 | main   | Azure API returned pending operation              | Added `pulumi cancel` step                                                                             |
| #200 | main   | "Stack has pending operation"                     | Added `pulumi stack export \| jq '.deployment.pending_operations = []' \| pulumi stack import --force` |
| #201 | main   | `"Match condition has more than 10 match values"` | Reduced Condition 3 from 14 to 10 values                                                               |
| #202 | main   | —                                                 | **SUCCESS** ✅                                                                                         |

### Key Learnings

- Class name: `UrlRewriteActionArgs` (NOT `DeliveryRuleUrlRewriteActionArgs`)
- RuleSet name: alphanumeric only, no hyphens (e.g. `"SpaRuleSet"`)
- Azure AFD Standard SKU: **maximum 10 match_values per condition**
- Pulumi pending operations must be cleared before the next `pulumi up`

---

## 2. CI/CD Workflow Refactoring

### Problem

Three main deploy workflows (`deploy-aws.yml`, `deploy-azure.yml`, `deploy-gcp.yml`) contained
dead steps from the old `frontend_web` Lambda-based SSR architecture:

- **AWS**: "Update frontend-web Lambda", "Build Frontend", "Deploy Frontend to S3", "Restore Landing Page"
- **Azure**: "Build Frontend", "Deploy Frontend to Storage"
- **GCP**: "Build Frontend", "Deploy Frontend to Cloud Storage", "Restore Landing Page"

These steps were no longer needed because the React SPA is now deployed exclusively by
`deploy-frontend-web-{aws,azure,gcp}.yml` workflows to the `/sns/` subpath.

### Solution

Removed all dead steps in commit `1ae65f5` — **168 lines deleted** across 3 workflow files.

### After State

| Workflow                        | Responsibility                            |
| ------------------------------- | ----------------------------------------- |
| `deploy-aws.yml`                | Pulumi infra + backend Lambda deploy only |
| `deploy-azure.yml`              | Pulumi infra + Function App deploy only   |
| `deploy-gcp.yml`                | Pulumi infra + Cloud Function deploy only |
| `deploy-frontend-web-aws.yml`   | React SPA → S3 `/sns/` prefix             |
| `deploy-frontend-web-azure.yml` | React SPA → Azure Blob `/sns/` prefix     |
| `deploy-frontend-web-gcp.yml`   | React SPA → GCS `/sns/` prefix            |

---

## 3. AWS Pulumi Dead Code Removal

### Problem

`infrastructure/pulumi/aws/__main__.py` contained 121 lines of dead code from the old
`frontend_web` Lambda architecture. CloudFront `/sns*` now routes directly to S3 (React SPA)
via CloudFront Function `spa-sns-rewrite-{stack}`, making the following resources obsolete:

| Resource           | Pulumi Name                             | Reason Obsolete           |
| ------------------ | --------------------------------------- | ------------------------- |
| Lambda Function    | `frontend-web-function`                 | SSR replaced by React SPA |
| Lambda FunctionUrl | `frontend-web-function-url`             | No longer referenced      |
| CloudFront OAC     | `frontend-web-oac`                      | No Lambda target          |
| Lambda Permission  | `frontend-web-cloudfront-invoke`        | No Lambda                 |
| API GW Integration | `frontend-web-integration`              | Route removed             |
| API GW Route       | `sns-root-route` (`ANY /sns`)           | Route removed             |
| API GW Route       | `sns-proxy-route` (`ANY /sns/{proxy+}`) | Route removed             |
| Lambda Permission  | `frontend-web-apigw-invoke`             | No Lambda                 |
| CloudFront Origin  | `frontend-web` (API GW endpoint)        | No longer needed          |
| Pulumi Export      | `frontend_web_lambda_name`              | Resource removed          |

### Solution

Removed all 10 dead resources in commit `5d2817f` — **121 lines deleted**.

```
infrastructure/pulumi/aws/__main__.py | 121 --
```

---

## 4. Staging Environment Validation & Fixes

After applying production fixes to the `develop` branch (`b222db2`), the staging CI/CD was
triggered. The following issues were found and fixed:

### 4-1. `ModuleNotFoundError: pulumi_azuread` (Azure staging)

**Cause**: `infrastructure/pulumi/azure/requirements.txt` in `develop` was missing
`pulumi-azuread>=6.0.0`. It had been accidentally deleted in a prior commit.

**Fix**: Restored `pulumi-azuread>=6.0.0,<7.0.0` from `main` branch.

---

### 4-2. `ModuleNotFoundError: No module named 'monitoring'` (AWS + Azure)

**Cause**: `monitoring.py` existed in `main` but had never been committed to `develop`.
All three cloud Pulumi stacks (`import monitoring` at the top) failed immediately.

**Fix**: Added `infrastructure/pulumi/{aws,azure,gcp}/monitoring.py` to `develop` branch
(commit `7f4724d`).

---

### 4-3. GCP URLMap `Error 412: Invalid fingerprint`

**Cause**: Pulumi state was out of sync with the actual GCP resource state. GCP requires the
current resource fingerprint to be provided when updating a `URLMap`; a stale Pulumi state
causes a 412 mismatch.

**Fix**: Added a `pulumi refresh --yes --skip-preview` step before `pulumi up` in
`deploy-gcp.yml` (commit `9bc6058`).

---

### 4-4. GCP `uploads-bucket` — `Error 409: bucket already exists`

**Cause**: `gcp/__main__.py` in `develop` did not define `uploads_bucket`. After syncing from
`main` (which does define it), Pulumi tried to create the bucket — but it already existed in
GCP from a previous run, yielding a 409 conflict.

**Fix**: Two-part fix:

1. Synced `infrastructure/pulumi/gcp/__main__.py` from `main` (adds `uploads_bucket` resource
   definition + `pulumi.export`) — commit `4fa611d`.
2. Added a `pulumi import` step in `deploy-gcp.yml` to import the pre-existing bucket into
   Pulumi state before `pulumi up` — commit `30cad90`.

---

### 4-5. GCP `ManagedSslCertificate` — `Error 400: ssl_certificate already in use`

**Cause**: The SSL certificate name included `_ssl_domain_hash`. When the hash value changed
(due to a code diff between `develop` and `main`), Pulumi attempted to replace the certificate.
GCP refused the deletion because the old certificate was still attached to the HTTPS proxy.

**Fix**: Two-part fix:

1. Added `ignore_changes=["name", "managed"]` to `ManagedSslCertificate` resource options in
   `gcp/__main__.py` (commit `fb89b45`).
2. Added a `pulumi import` step for `managed-ssl-cert` in `deploy-gcp.yml` (commit `30cad90`).

---

## 5. Final Staging CI/CD Results

All three clouds successfully deployed after the above fixes:

| Cloud | Run ID      | Branch  | Result         |
| ----- | ----------- | ------- | -------------- |
| AWS   | 22269437380 | develop | ✅ **success** |
| Azure | 22269437373 | develop | ✅ **success** |
| GCP   | 22269943597 | develop | ✅ **success** |

---

## 6. Commits Summary

### `main` branch

| Commit    | Description                                                        | Impact                     |
| --------- | ------------------------------------------------------------------ | -------------------------- |
| `48799f8` | feat(azure): replace AFD route with SPA URL Rewrite RuleSet        | Azure SPA routing fixed    |
| `bb6f57c` | fix(azure): use `UrlRewriteActionArgs`                             | Python import error fixed  |
| `06e7d08` | fix(azure): use alphanumeric-only RuleSet name                     | AFD API rejection fixed    |
| `b0eb56a` | fix(ci): add `pulumi cancel` + state import step                   | Pending operations cleared |
| `0f653fc` | fix(azure): reduce AFD Rule match_values to 10                     | AFD 10-value limit obeyed  |
| `1ae65f5` | refactor(ci): remove dead frontend-web Lambda steps                | 168 lines removed          |
| `5d2817f` | refactor(infra): remove dead `frontend_web_lambda` from AWS Pulumi | 121 lines removed          |

### `develop` branch (staging fixes)

| Commit    | Description                                                            |
| --------- | ---------------------------------------------------------------------- |
| `b222db2` | sync(staging): apply main refactoring — requirements.txt, workflows    |
| `7f4724d` | fix(staging): add monitoring.py for all 3 clouds                       |
| `9bc6058` | fix(gcp): add `pulumi refresh` before up                               |
| `ab16c77` | fix(gcp): remove uploads-bucket from Pulumi state (superseded)         |
| `4fa611d` | fix(gcp): sync `gcp/__main__.py` from main (uploads_bucket + Firebase) |
| `30cad90` | fix(gcp): import uploads-bucket + ManagedSslCert to Pulumi state       |
| `fb89b45` | fix(gcp): `ignore_changes` on ManagedSslCertificate name+managed       |

---

## 7. Architecture After Changes

```
Browser
  │
  ├─── /                    → CDN (landing page — static HTML)
  │
  └─── /sns/*
        ├── AWS:   CloudFront → S3 /sns/index.html  (CF Function rewrite)
        ├── Azure: Front Door → Blob Storage /sns/index.html  (SpaRuleSet rewrite)
        └── GCP:   Cloud CDN → GCS /sns/index.html  (URL Map path rule)

/api/*  → API Gateway (AWS) / Function App (Azure) / Cloud Functions (GCP)
```

### Key Architecture Decisions

- **React SPA static deployment**: All three clouds serve the React app from object storage
  (S3 / Azure Blob / GCS) with CDN in front. No SSR Lambda required.
- **SPA routing**: Each CDN rewrites unmatched paths under `/sns/*` to `/sns/index.html` so
  client-side routing works correctly on direct URL access and page refresh.
- **Backend separation**: The FastAPI backend is deployed independently via its own Pulumi
  resources and CI/CD steps, decoupled from the frontend.
- **Infrastructure as Code**: All CDN, DNS, SSL, storage, and compute resources are managed
  by Pulumi (Python). Zero manual resource creation required.

---

## 8. Files Changed

| File                                           | Change Type                                    | Lines    |
| ---------------------------------------------- | ---------------------------------------------- | -------- |
| `infrastructure/pulumi/azure/__main__.py`      | Added SpaRuleSet + URL Rewrite                 | +80      |
| `infrastructure/pulumi/aws/__main__.py`        | Removed dead Lambda resources                  | -121     |
| `infrastructure/pulumi/gcp/__main__.py`        | Added uploads_bucket, Firebase, ignore_changes | +264/-23 |
| `infrastructure/pulumi/aws/monitoring.py`      | Added (synced from main)                       | +358     |
| `infrastructure/pulumi/azure/monitoring.py`    | Added (synced from main)                       | +358     |
| `infrastructure/pulumi/gcp/monitoring.py`      | Added (synced from main)                       | +358     |
| `infrastructure/pulumi/azure/requirements.txt` | Restored pulumi-azuread                        | +1       |
| `.github/workflows/deploy-aws.yml`             | Removed dead Lambda/S3 steps                   | -60      |
| `.github/workflows/deploy-azure.yml`           | Removed dead storage step, added pulumi cancel | -20/+15  |
| `.github/workflows/deploy-gcp.yml`             | Removed dead GCS steps, added refresh + import | -30/+35  |

---

_Generated: 2026-02-22 | Branches: main (production), develop (staging)_
