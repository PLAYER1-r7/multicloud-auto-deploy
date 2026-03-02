# 11 — バグ・修正レポート

> **目的**: 3つのクラウド環境全体における既知バグと修正の統合インデックス。
> 繰り返して現れる問題をデバッグするときや、変更をデプロイする前に、このドキュメントを参照します。

---

## 概要

| 日付       | レポート                                                                            | クラウド      | バグ数  | ステータス   |
| ---------- | ----------------------------------------------------------------------------------- | ------------- | ------- | ------------ |
| 2026-02-20 | [AWS SNS Fix (staging)](#1-aws-sns-fix-report-2026-02-20)                           | AWS           | 4       | ✅ All fixed |
| 2026-02-21 | [AWS HTTPS Fix (production)](#2-aws-production-https-fix-2026-02-21)                | AWS           | 1       | ✅ Fixed     |
| 2026-02-21 | [AWS Production SNS Fix](#3-aws-production-sns-fix-2026-02-21)                      | AWS           | 2       | ✅ All fixed |
| 2026-02-21 | [React SPA Migration & CDN Fix](#4-react-spa-migration--cdn-routing-fix-2026-02-21) | AWS/Azure/GCP | 3 CDN   | ✅ All fixed |
| 2026-02-21 | [Azure SNS Fix (503/404 + AFD 502)](#5-azure-sns-fix-2026-02-21)                    | Azure         | 5+1     | ✅ All fixed |
| 2026-02-22 | [AWS SNS Fix (staging, 12 bugs)](#6-aws-sns-fix-report-2026-02-22)                  | AWS           | 12      | ✅ All fixed |
| 2026-02-22 | [SNS Fix (AWS+Azure combined)](#7-aws--azure-combined-sns-fix-2026-02-22)           | AWS/Azure     | 10      | ✅ All fixed |
| 2026-02-22 | [Refactoring & Infra Fix](#8-refactoring--infrastructure-fix-2026-02-22)            | All           | 5 infra | ✅ All fixed |
| 2026-02-23 | [GCP SNS Fix (staging)](#9-gcp-sns-fix-report-2026-02-23)                           | GCP           | 6       | ✅ All fixed |
| 2026-02-27 | [OCR Formula Merge Bugs](#10-ocr-formula-merge-bugs-2026-02-27)                     | API           | 3       | ✅ All fixed |

---

## 目次

1. [AWS SNS 修正（2026-02-20）](#1-aws-sns-修正レポート2026-02-20)
2. [AWS 本番 HTTPS 修正（2026-02-21）](#2-aws-production-https-fix-2026-02-21)
3. [AWS 本番 SNS 修正（2026-02-21）](#3-aws-production-sns-fix-2026-02-21)
4. [React SPA マイグレーション・CDN ルーティング修正（2026-02-21）](#4-react-spa-migration--cdn-routing-fix-2026-02-21)
5. [Azure SNS 修正（2026-02-21）](#5-azure-sns-fix-2026-02-21)
6. [AWS SNS 修正 12 バグ（2026-02-22）](#6-aws-sns-fix-report-2026-02-22)
7. [AWS + Azure 統合 SNS 修正（2026-02-22）](#7-aws--azure-combined-sns-fix-2026-02-22)
8. [リファクタリング・インフラ修正（2026-02-22）](#8-refactoring--infrastructure-fix-2026-02-22)
9. [GCP SNS 修正（2026-02-23）](#9-gcp-sns-fix-report-2026-02-23)
10. [OCR 数式マージバグ（2026-02-27）](#10-ocr-formula-merge-bugs-2026-02-27)

---

## 1. AWS SNS 修正レポート（2026-02-20）

**Environment**: `https://d1tf3uumcm4bo1.cloudfront.net/sns/` (staging)
**Branch**: develop — commits `c5a261c` → `4d2bce0`
**Source**: [AWS_SNS_FIX_REPORT.md](AWS_SNS_FIX_REPORT.md)

| #   | Symptom                                                                     | Root Cause                                                                                                                                           | Files Changed                               |
| --- | --------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------- |
| 1   | Profile page: "Sign in to see profile details", API base = `localhost:8000` | CI/CD overwrote Lambda env vars with empty strings on every push; `ResourceConflictException` silently skipped code update                           | `.github/workflows/deploy-aws.yml`          |
| 2   | CI/CD fixes had no effect                                                   | Edits were applied to `multicloud-auto-deploy/.github/workflows/` (subdirectory copy) — GitHub Actions reads only the repo-root `.github/workflows/` | `.github/workflows/deploy-aws.yml`          |
| 3   | Logout redirected to `/login` → HTTP 404                                    | `auth.py` hardcoded `/login` fallback; root cause was Bug 1 (missing Cognito env vars)                                                               | `services/frontend_web/app/routers/auth.py` |
| 4   | `POST /uploads` → 502 Bad Gateway                                           | `UploadUrlsRequest.count le=10` and `CreatePostBody.imageKeys max_length=10`; frontend allows 16                                                     | `services/api/app/models.py`                |

### Key Fixes

```yaml
# Bug 1 — deploy-aws.yml: added aws lambda wait before code update
- name: Update frontend-web Lambda
  run: |
    aws lambda wait function-updated --function-name $FN
    aws lambda update-function-configuration \
      --function-name multicloud-auto-deploy-staging-frontend-web \
      --environment "Variables={AUTH_DISABLED=false, API_BASE_URL=$API_ENDPOINT, ...}"
    aws lambda wait function-updated --function-name $FN
```

```python
# Bug 4 — models.py: raised limits 10 → 16
count: int = Field(..., ge=1, le=16)
image_keys: Optional[list[str]] = Field(None, alias="imageKeys", max_length=16)
```

### Key Lesson

> **Always edit `.github/workflows/` at the repo root.** The subdirectory copy at `multicloud-auto-deploy/.github/workflows/` is ignored by GitHub Actions.

---

## 2. AWS Production HTTPS Fix (2026-02-21)

**Environment**: `https://www.aws.ashnova.jp` (production)
**CloudFront Distribution**: `E214XONKTXJEJD` (`d1qob7569mn5nw.cloudfront.net`)
**Source**: [AWS_HTTPS_FIX_REPORT.md](AWS_HTTPS_FIX_REPORT.md)

### Symptom

```
NET::ERR_CERT_COMMON_NAME_INVALID — Your connection is not private
```

### Root Cause

CloudFront distribution `E214XONKTXJEJD` had no custom domain alias or ACM certificate configured.
`pulumi/aws/__main__.py` reads `config.get("customDomain")` — since the Pulumi config values were never set, the `else` branch always ran `cloudfront_default_certificate=True`.

| Setting             | Broken                               | Fixed                                                     |
| ------------------- | ------------------------------------ | --------------------------------------------------------- |
| `Aliases`           | `Quantity: 0`                        | `["www.aws.ashnova.jp"]`                                  |
| `ViewerCertificate` | `CloudFrontDefaultCertificate: true` | ACM `914b86b1` (`www.aws.ashnova.jp`, expires 2027-03-12) |

### Fix (Immediate)

Applied via `aws cloudfront update-distribution --id E214XONKTXJEJD`.

### Fix (Permanent — run before every `pulumi up --stack production`)

```bash
cd infrastructure/pulumi/aws
pulumi stack select production
pulumi config set customDomain www.aws.ashnova.jp
pulumi config set acmCertificateArn arn:aws:acm:us-east-1:278280499340:certificate/914b86b1-4c10-4354-91cf-19c4460dcde5
pulumi up --stack production
```

> **Warning**: Without setting these config values, `pulumi up` reverts CloudFront to `CloudFrontDefaultCertificate: true`, reproducing the HTTPS error.

---

## 3. AWS Production SNS Fix (2026-02-21)

**Environment**: `https://www.aws.ashnova.jp/sns/` (production)
**Branch**: main — commits `fd1f422` `8188682`
**Source**: [AWS_PRODUCTION_SNS_FIX_REPORT.md](AWS_PRODUCTION_SNS_FIX_REPORT.md)

| #   | Symptom                                                 | Root Cause                                                                                         | Fix                                                                                     |
| --- | ------------------------------------------------------- | -------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------- |
| 1   | All API calls hit `localhost:8000` → Connection refused | `API_BASE_URL=""` — CI/CD read from GitHub Secrets never configured for `production` env           | Rewrote workflow to use Pulumi stack outputs instead of Secrets                         |
| 2   | Cognito login redirect URL rejected                     | `COGNITO_REDIRECT_URI` used CloudFront domain; Cognito App Client only allows `www.aws.ashnova.jp` | Derive `SITE_DOMAIN` from `custom_domain` Pulumi output, fall back to CloudFront domain |

### Root Cause Detail — Bug 1

```yaml
# BEFORE (❌ empty string when secret is unset — silently overwrites Lambda env)
API_URL="${{ secrets.API_GATEWAY_ENDPOINT }}"

# AFTER (✅ always correct — reads from Pulumi stack)
- name: Get Pulumi Outputs
  run: |
    pulumi stack select "${{ steps.env.outputs.env_name }}"
    echo "api_gateway_endpoint=$(pulumi stack output api_gateway_endpoint)" >> $GITHUB_OUTPUT
```

Guard clause added to abort deployment if outputs are empty:

```bash
if [[ -z "$API_URL" || -z "$CF_DOMAIN" || -z "$CLIENT_ID" ]]; then
  echo "❌ Critical Pulumi outputs are empty. Aborting."
  exit 1
fi
```

### Root Cause Detail — Bug 2

```bash
# BEFORE (❌ CloudFront domain not registered in Cognito App Client)
COGNITO_REDIRECT_URI="https://${CLOUDFRONT_DOMAIN}/sns/auth/callback"

# AFTER (✅ uses custom domain when available)
CUSTOM_DOMAIN="${{ steps.pulumi_outputs.outputs.custom_domain }}"
SITE_DOMAIN="${CUSTOM_DOMAIN:-$CF_DOMAIN}"
COGNITO_REDIRECT_URI="https://${SITE_DOMAIN}/sns/auth/callback"
```

### Key Lessons

1. **Never use GitHub Secrets as source of truth for infrastructure values.** Use Pulumi outputs directly.
2. **Production and staging have separate Pulumi stacks** with different API Gateway IDs, Cognito pools, and custom domains.
3. **Empty string `""` in Pydantic settings is NOT the same as absent.** An empty `API_BASE_URL` does not fall back to the default — it is used as-is.

---

## 4. React SPA Migration & CDN Routing Fix (2026-02-21)

**Environment**: production (all 3 clouds)
**Branch**: main — commits `6aff4ac` `d7df295`
**Source**: [REACT_SPA_MIGRATION_REPORT.md](REACT_SPA_MIGRATION_REPORT.md)

### Background

Frontend migrated from Python/Reflex SSR (`frontend_web`) to static React SPA (`frontend_react`).
After migration CI/CD succeeded but all 3 clouds' CDNs still routed `/sns*` to the old Python origin.

### CDN Routing Bugs Fixed

| Cloud | CDN Resource                                 | Old Origin (wrong)                                 | New Origin (correct)                                   |
| ----- | -------------------------------------------- | -------------------------------------------------- | ------------------------------------------------------ |
| AWS   | CloudFront `E214XONKTXJEJD` `/sns*` behavior | API Gateway → Lambda SSR                           | S3 bucket `multicloud-auto-deploy-production-frontend` |
| Azure | AFD route `production-sns-route`             | `frontend-web-origin-group` (deleted Function App) | Blob Storage origin group                              |
| GCP   | URL map `/sns/*` path rule                   | `frontend-web-backend` (Cloud Run NEG)             | Removed — falls to default GCS backend                 |

### AWS Additional Bug — S3 directory index

After switching CloudFront `/sns*` to S3, accessing `/sns/` returned the landing page root `index.html` (S3 has no directory-index capability).

**Fix**: Created CloudFront Function `spa-sns-rewrite-{stack}`:

```javascript
function handler(event) {
  var request = event.request;
  var uri = request.uri;
  if (uri === "/sns" || uri === "/sns/") {
    request.uri = "/sns/index.html";
  }
  return request;
}
```

Associated with the `/sns*` cache behavior in `infrastructure/pulumi/aws/__main__.py`.

### CI/CD Workflow Changes

| Workflow                        | Old                         | New                                                                  |
| ------------------------------- | --------------------------- | -------------------------------------------------------------------- |
| `deploy-frontend-web-aws.yml`   | Docker image → Lambda       | `npm run build`, sync to `s3://<bucket>/sns/`, invalidate CloudFront |
| `deploy-frontend-web-azure.yml` | Docker image → Function App | `npm run build`, upload to Azure Blob `$web/sns/`, purge AFD cache   |
| `deploy-frontend-web-gcp.yml`   | Docker image → Cloud Run    | `npm run build`, copy to GCS `sns/` prefix, invalidate CDN           |

### Cache-Control Pattern (AWS/GCP)

```yaml
# Hashed assets — 1-year immutable cache
aws s3 sync dist/assets/ s3://${BUCKET}/sns/assets/ \
  --cache-control "public, max-age=31536000, immutable"
# index.html — no cache (always fetch latest)
aws s3 cp dist/index.html s3://${BUCKET}/sns/index.html \
  --cache-control "no-cache, no-store, must-revalidate"
```

---

## 5. Azure SNS Fix (2026-02-21)

**Environment**: Azure staging + production
**Source**: [AZURE_SNS_FIX_REPORT.md](AZURE_SNS_FIX_REPORT.md)

### Part A — 503/404 Initial Setup Bugs

| #   | Symptom                              | Root Cause                                                                                                 | Fix                                                                         |
| --- | ------------------------------------ | ---------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------- |
| A1  | All endpoints 503                    | `host.json` extra closing brace (invalid JSON)                                                             | Fixed JSON; added `extensionBundle`                                         |
| A2  | Functions list empty, host healthy   | `WEBSITE_RUN_FROM_PACKAGE` with external SAS URL doesn't register Python v2 functions on Consumption Linux | Switched to `az functionapp deployment source config-zip` (Kudu ZIP deploy) |
| A3  | `ModuleNotFoundError: pydantic_core` | Dev container is `aarch64`; Azure Functions runs `x86_64` — `.so` binaries incompatible                    | Build with `docker run --platform linux/amd64 python:3.12-slim`             |
| A4  | Static files / templates 404         | Relative paths like `StaticFiles(directory="app/static")` fail when CWD is not guaranteed                  | Use `os.path.dirname(os.path.abspath(__file__))` for absolute paths         |
| A5  | Functions not invoked via ASGI       | `AsgiMiddleware.handle()` (sync) used                                                                      | Switched to manual async ASGI conversion                                    |

### Part B — AFD 502 Intermittent Errors (Production)

**Symptom**: `www.azure.ashnova.jp/sns/health` returns HTTP 502 ~50% of requests; direct Function App access succeeds 100%.

**Root Cause**: Dynamic Consumption (Y1) instances are periodically recycled. AFD Standard cannot detect TCP disconnect during recycling — stale connections in the pool return 502 instantly.

**Fix**: Migrated production Function App from Dynamic Consumption (Y1) → **FC1 FlexConsumption** with `maximumInstanceCount=1` + `alwaysReady http=1`. Result: 0/20 failures after migration.

```bash
# Create FlexConsumption Function App (NOT --consumption-plan-location)
az functionapp create \
  --name multicloud-auto-deploy-production-frontend-web-v2 \
  --flexconsumption-location japaneast \
  --runtime python --runtime-version 3.12 ...
az functionapp scale config set --maximum-instance-count 1 ...
az functionapp scale config always-ready set --settings "http=1" ...
```

### Key Rules for Azure Deployment

- **Always build with `--platform linux/amd64 python:3.11-slim`** — Dev Container is aarch64; `.so` binaries are incompatible
- **`SCM_DO_BUILD_DURING_DEPLOYMENT` is NOT supported on Flex Consumption** — always deploy pre-built ZIP
- **Do NOT use external SAS URL in `WEBSITE_RUN_FROM_PACKAGE`** on Consumption Linux — Python v2 functions are not registered
- **CORS must be configured at platform level** (`az functionapp cors add`) — Python code CORS headers are ignored because Kestrel handles OPTIONS before the Python runtime
- **Blob Storage CORS is independent from Function App CORS** — must configure separately for SAS URL direct uploads
- **`--consumption-plan-location` creates Dynamic Y1** (causes stale TCP with AFD) — use `--flexconsumption-location` for production

---

## 6. AWS SNS Fix Report (2026-02-22)

**Environment**: `https://d1tf3uumcm4bo1.cloudfront.net/sns/` (staging)
**Branch**: develop — commits `9b4d37c` → `8c84a15`
**Source**: [AWS_SNS_FIX_REPORT_20260222.md](AWS_SNS_FIX_REPORT_20260222.md)

| #   | Symptom                                   | Root Cause                                                                                       | Files                                           |
| --- | ----------------------------------------- | ------------------------------------------------------------------------------------------------ | ----------------------------------------------- |
| 1   | Profile GET/PUT → 500                     | `aws_backend.py` used wrong DynamoDB field names (`userId` instead of `PK`, `eamil` typo)        | `backends/aws_backend.py`                       |
| 2   | Login redirects to CloudFront domain      | `auth.ts` hardcoded CloudFront origin URL                                                        | `frontend_react/src/config/auth.ts`             |
| 3   | Cognito hosted UI → `/error` page         | `--supported-identity-providers` missing from CI/CD `update-user-pool-client`                    | `.github/workflows/deploy-frontend-web-aws.yml` |
| 4   | `POST /uploads/presigned-urls` → 422      | `count le=10` too low; `contentTypes` field missing from model                                   | `models.py`, `routes/uploads.py`                |
| 5   | `GET /profile` → 401                      | JWT verifier checked `at_hash` without companion access_token; Cognito access_token has no `aud` | `jwt_verifier.py`                               |
| 6   | `POST /posts` → 422                       | `imageKeys max_length=10`; frontend uploads 13 images                                            | `models.py`                                     |
| 7   | Images not displaying                     | S3 private bucket — raw S3 keys returned instead of presigned GET URLs on read                   | `backends/aws_backend.py`                       |
| 8   | Nickname missing from post list           | `create_post()` didn't fetch nickname from PROFILES table                                        | `backends/aws_backend.py`                       |
| 9   | `GET /posts/{post_id}` → 405              | Endpoint not implemented in any backend                                                          | `backends/*.py`, `routes/posts.py`              |
| 10  | No server-side image count enforcement    | Limit was frontend-only                                                                          | `config.py`, `routes/limits.py`, `PostForm.tsx` |
| 11  | MIME type error on JS assets (blank page) | Vite built with `base="/"` but site deployed at `/sns/`                                          | `vite.config.ts`, CloudFront error pages        |
| 12  | "認証設定が不完全です" login error        | `VITE_AUTH_PROVIDER` not set; defaulted to `"none"`                                              | `.env.aws.staging` (new file)                   |

### Key Technical Points

```python
# Bug 5 — disable at_hash check when using id_token standalone
verify_at_hash: False
# Make aud verification conditional (Cognito access_token has no aud)
if "aud" in token_claims: verify_aud(...)
```

```python
# Bug 7 — store raw keys, generate presigned URLs at read time
def _key_to_presigned_url(self, key: str) -> str: ...  # 1-hour expiry
# DynamoDB: imageKeys (raw S3 keys) — NOT imageUrls
```

```bash
# Bug 11 — build with correct base path for sub-path deployment
VITE_BASE_PATH=/sns/ npm run build
# CloudFront custom error pages → /sns/index.html (NOT /index.html)
```

---

## 7. AWS + Azure Combined SNS Fix (2026-02-22)

**Environment**: AWS staging + Azure staging
**Branch**: develop
**Source**: [SNS_FIX_REPORT_20260222.md](SNS_FIX_REPORT_20260222.md)

### AWS Bug — Cognito `unauthorized_client`

**Symptom**: Cognito hosted UI returns `error=unauthorized_client` after login click.

**Root Cause**:

- `AllowedOAuthFlows` was missing `implicit`
- `CallbackURLs` did not include the staging domain `staging.aws.ashnova.jp`

**Fix** (`infrastructure/pulumi/aws/simple-sns/__main__.py`):

```python
allowed_o_auth_flows=["code", "implicit"]
callback_urls=[
    "https://www.aws.ashnova.jp/sns/auth/callback",
    "https://staging.aws.ashnova.jp/sns/auth/callback",  # added
    "http://localhost:5173/sns/auth/callback",
]
```

### Azure Bugs Fixed

| #   | Symptom                                        | Root Cause                                                                    | Fix                                                                            |
| --- | ---------------------------------------------- | ----------------------------------------------------------------------------- | ------------------------------------------------------------------------------ |
| 1   | Login redirects to FrontDoor internal hostname | Azure AD `redirect_uri` lacked custom domain                                  | Re-registered with `staging.azure.ashnova.jp`                                  |
| 2   | SVG images 404                                 | `upload-batch` placed SVGs at `$web/sns/` but CSS references `./assets/`      | Copy `dist/*.svg` to `$web/sns/assets/` in CI/CD                               |
| 3   | All API endpoints 404                          | Azure Functions default `routePrefix: "api"` → actual path `/api/limits`      | Added `"routePrefix": ""` to `services/api/host.json`                          |
| 4   | API CORS errors                                | Kestrel processes OPTIONS before Python runtime; platform CORS not configured | `az functionapp cors add --allowed-origins "https://staging.azure.ashnova.jp"` |
| 5   | Image upload CORS errors                       | Blob Storage CORS is independent from Function App CORS                       | `az storage cors add` on Blob Storage account                                  |
| 6   | Logout blocks after sign-out                   | `post_logout_redirect_uri=/sns/` not in AD app `redirect_uris`                | Added `/sns/` to `az ad app update --web-redirect-uris`                        |
| 7   | 503 all endpoints after deploy                 | aarch64 `.so` binaries used (Dev Container is ARM); wrong Python version      | Use `docker run --platform linux/amd64 python:3.11-slim`                       |
| 8   | Nickname missing from posts                    | `_item_to_post` missing `nickname` field; `create_post` not fetching profile  | Added `nickname=item.get("nickname")` and profile fetch in `create_post`       |

### CI/CD Changes (Azure)

| Step                       | Change                                                                |
| -------------------------- | --------------------------------------------------------------------- |
| Python package build       | `docker run --platform linux/amd64 python:3.11-slim pip install`      |
| Platform CORS              | `az rest PUT` with full `allowedOrigins` array                        |
| Blob Storage CORS          | `az storage cors add` with FrontDoor host + custom domain + localhost |
| AD redirect_uris           | `az ad app update --web-redirect-uris` after Pulumi deploy            |
| SVG assets                 | Copy `dist/*.svg` to `$web/sns/assets/` after `upload-batch`          |
| Remove `.so` deletion step | Was deleting required C extension binaries                            |

---

## 8. Refactoring & Infrastructure Fix (2026-02-22)

**Branch**: main (production) + develop (staging)
**Source**: [REFACTORING_REPORT_20260222.md](REFACTORING_REPORT_20260222.md)

### 8-1. Azure Front Door — SPA URL Rewrite Rule

**Problem**: React SPA deep-links (`/sns/login`, etc.) returned HTTP 404. AFD was forwarding to the backend instead of serving `index.html`.

**Fix**: Added `SpaRuleSet` + `SpaIndexHtmlRewrite` rule to `infrastructure/pulumi/azure/__main__.py`. Rewrites all non-static-asset browser requests under `/sns/*` to `/sns/index.html`.

**AFD Constraints**:

- RuleSet name must be **alphanumeric only** (no hyphens) — e.g. `"SpaRuleSet"`
- **Maximum 10 `match_values` per condition** (Azure AFD Standard SKU limit)
- Pulumi class name: `UrlRewriteActionArgs` (NOT `DeliveryRuleUrlRewriteActionArgs`)
- Pulumi pending operations must be cleared before next `pulumi up`:
  ```bash
  pulumi stack export | jq '.deployment.pending_operations = []' | pulumi stack import --force
  ```

### 8-2. CI/CD Workflow Cleanup

Removed 168 lines of dead steps from `deploy-aws.yml`, `deploy-azure.yml`, `deploy-gcp.yml` (old `frontend_web` Lambda/Function App build/deploy steps; React SPA now deployed exclusively by `deploy-frontend-web-*.yml`).

### 8-3. AWS Pulumi Dead Code Removal

Removed 10 dead resources (121 lines) from `infrastructure/pulumi/aws/__main__.py`:

- `frontend-web-function` Lambda, FunctionUrl, OAC, Permissions
- API GW routes `ANY /sns` and `ANY /sns/{proxy+}`
- CloudFront `frontend-web` origin (API GW endpoint)

### 8-4. Staging Bug: `ModuleNotFoundError: pulumi_azuread`

**Cause**: `infrastructure/pulumi/azure/requirements.txt` was missing `pulumi-azuread>=6.0.0` (accidentally deleted in a prior commit).
**Fix**: Restored from `main` branch.

### 8-5. Staging Bug: `ModuleNotFoundError: monitoring`

**Cause**: `monitoring.py` existed in `main` but had never been committed to `develop`.
**Fix**: Added `infrastructure/pulumi/{aws,azure,gcp}/monitoring.py` to `develop`.

### 8-6. GCP: `Error 412: Invalid fingerprint` on URLMap

**Cause**: Pulumi state out of sync with actual GCP resource state (fingerprint mismatch).
**Fix**: Added `pulumi refresh --yes --skip-preview` before `pulumi up` in `deploy-gcp.yml`.

### 8-7. GCP: `Error 409: bucket already exists`

**Cause**: `gcp/__main__.py` in `develop` didn't define `uploads_bucket`; after syncing from `main`, Pulumi tried to create a bucket that already existed.
**Fix**: Added `pulumi import` step in `deploy-gcp.yml` to import pre-existing bucket before `pulumi up`.

### 8-8. GCP: `Error 400: ssl_certificate already in use`

**Cause**: SSL certificate name included a hash that changed between `develop` and `main`, causing Pulumi to try replacing it while the old cert was still attached.
**Fix**: Added `ignore_changes=["name", "managed"]` to `ManagedSslCertificate` in `gcp/__main__.py` + `pulumi import` for existing cert.

---

## 9. GCP SNS Fix Report (2026-02-23)

**Environment**: `https://staging.gcp.ashnova.jp/sns/` (staging)
**Branch**: develop — commits `2385ee4` → `ec5bf05`
**Source**: [GCP_SNS_FIX_REPORT_20260223.md](GCP_SNS_FIX_REPORT_20260223.md)

| #   | Symptom                                | Root Cause                                                                        | Fix                                                                                |
| --- | -------------------------------------- | --------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------- |
| G1  | CORS error on `/posts`                 | `CORS_ORIGINS` missing `staging.gcp.ashnova.jp`                                   | Added custom domain to `CORS_ORIGINS` via `--env-vars-file`                        |
| G2  | Firebase login "domain not authorized" | Custom domain not registered in Firebase Auth authorized domains                  | PATCH Identity Toolkit Admin v2 API; added auto-register step to `deploy-gcp.yml`  |
| G3  | `/limits` → 404 after login            | Cloud Function deployed with stale code lacking `limits` route                    | Rebuilt with Docker `linux/amd64` and redeployed                                   |
| G4  | `signInWithPopup` COOP warning         | CDN not sending `Cross-Origin-Opener-Policy` header                               | Added `Cross-Origin-Opener-Policy: same-origin-allow-popups` to CDN backend bucket |
| G5  | `/uploads/presigned-urls` → 500        | `generate_signed_url()` requires private key; Compute Engine credentials lack it  | Use `service_account_email` + `access_token` to trigger IAM `signBlob` API path    |
| G6  | Cloud Function build failure           | `local_backend.py` missing `with self._get_connection()` block (IndentationError) | Restored `delete_post` method with correct `with` block                            |

### Key Technical Points

#### G2 — Firebase Auth Domain Registration

```bash
# x-goog-user-project header is REQUIRED — without it, API returns 403 PERMISSION_DENIED
curl -s -X PATCH \
  "https://identitytoolkit.googleapis.com/admin/v2/projects/ashnova/config" \
  -H "Authorization: Bearer $(gcloud auth print-access-token)" \
  -H "x-goog-user-project: ashnova" \
  -d '{"authorizedDomains": ["...", "staging.gcp.ashnova.jp"]}'
```

#### G3 — Cloud Function Rebuild (aarch64 → linux/amd64)

```bash
docker run --rm --platform linux/amd64 -v /tmp/deploy_gcp:/out python:3.12-slim \
  bash -c "pip install --target /out/.deployment -r /out/requirements-gcp.txt -q"
# CRITICAL: Copy main.py — Cloud Build requires it even if --entry-point differs
cp services/api/function.py /tmp/deploy_gcp/.deployment/main.py
```

#### G5 — GCS Presigned URLs from Compute Engine Credentials

```python
# Standard generate_signed_url() fails — Compute Engine credentials have no private key
# Solution: pass service_account_email + access_token to trigger IAM signBlob API
credentials.refresh(google.auth.transport.requests.Request())
blob.generate_signed_url(
    version="v4",
    service_account_email=settings.gcp_service_account,  # GCP_SERVICE_ACCOUNT env var
    access_token=credentials.token,
)
# Required IAM role: roles/iam.serviceAccountTokenCreator on the Compute SA
```

#### G1 Gotcha — `--update-env-vars` Cannot Be Used for URLs

```bash
# ❌ Fails — values with ':' cause parse errors
gcloud run services update --update-env-vars "CORS_ORIGINS=https://..."

# ✅ Use --env-vars-file (YAML) instead — replaces ALL env vars, include the full set
gcloud run services update --env-vars-file env.yaml
```

---

## 10. OCR Formula Merge Bugs (2026-02-27)

**Service**: `services/api/app/services/` (API — all clouds)
**Branch**: develop — commits `608f98f` `4fa3394` `cc0956b`
**Source**: [OCR_FORMULA_MERGE_REPORT.md](OCR_FORMULA_MERGE_REPORT.md)

### Background

`prebuilt-read` reproduces Japanese text faithfully but breaks formulas into ASCII fragments.
`prebuilt-layout + FORMULAS` extracts accurate LaTeX but may miss Japanese text.
A 2-pass merge strategy was implemented to combine both passes.

| #   | Symptom                                                             | Root Cause                                                                                    | Fix (commit)                                                                                                                            |
| --- | ------------------------------------------------------------------- | --------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------- |
| 1   | Display formulas silently missing from `azure_di_merged` output     | On polygon match failure, unmatched display formulas were discarded                           | Lowered overlap threshold 0.5→0.3; added Point-object polygon support; safety net appends unmatched display formulas at end (`608f98f`) |
| 2   | `TypeError: Object of type bytes is not JSON serializable`          | Azure DI SDK (some versions) returns `polygon`, `content`, `value`, `kind` as `bytes` type    | Added `isinstance(x, (bytes, bytearray))` guards in both `_ocr_read_pass` and `_ocr_layout_formulas_pass` (`4fa3394`)                   |
| 3   | All polygons None after Bug 2 fix → formulas always appended at end | Bug 2 fix set bytes polygons to None; SDK returns polygons only as bytes in some environments | Added heuristic formula-region detection as fallback match (`cc0956b`)                                                                  |

### Heuristic Formula Region Detection (fallback for Bug 3)

When polygon data is unavailable, `_find_formula_regions()` detects formula blocks by:

- No CJK characters in the line
- Line ≤ 80 chars
- At least one strong math signal: `[\\∞∫∑∏√]|lim|log|sin|cos|tan` or 2+ consecutive operators

### Merge Strategy (final)

```
Pass 1: Y-polygon overlap ≥ 30%  → inline replace
Pass 2: _find_formula_regions() pairing with unmatched display formulas
Safety net: still-unmatched display formulas appended as [display] at end
Inline formulas: always appended as [inline]
```

### Known Minor Issues

| Issue                            | Detail                                                             |
| -------------------------------- | ------------------------------------------------------------------ |
| `ェ>0` instead of `x>0`          | CJK lookalike OCR misread — post-processing normalization needed   |
| `[display] \quad` false positive | `_has_formula_signal` overly broad — `\quad` should be blacklisted |
| `1/2` → `112`                    | Fraction OCR misread — no fix yet                                  |

---

_Last updated: 2026-02-27_
