# GCP Simple-SNS: Fix Report (2026-02-23)

> **Status**: ✅ All 6 issues resolved — simple-sns is fully operational on GCP staging  
> **Commits**: `2385ee4` → `ec5bf05` (develop branch)  
> **Environment**: `https://staging.gcp.ashnova.jp/sns/`

---

## Executive Summary

This report documents 6 independent bugs found and fixed during end-to-end verification of the GCP staging environment on 2026-02-23. The root causes range from missing environment variables to fundamental GCP credential limitations.

| #   | Symptom                                          | Root Cause                                                                          | Status   |
| --- | ------------------------------------------------ | ----------------------------------------------------------------------------------- | -------- |
| G1  | CORS error on `/posts`                           | `CORS_ORIGINS` env var missing `staging.gcp.ashnova.jp`                             | ✅ Fixed |
| G2  | Firebase login blocked ("domain not authorized") | Custom domain not registered in Firebase Auth authorized domains                    | ✅ Fixed |
| G3  | `/limits` returns 404 after login                | Cloud Function deployed with stale code lacking `limits` route                      | ✅ Fixed |
| G4  | `signInWithPopup` COOP warning                   | CDN not sending `Cross-Origin-Opener-Policy` header                                 | ✅ Fixed |
| G5  | `/uploads/presigned-urls` returns 500            | `generate_signed_url()` requires private key; Compute Engine credentials lack it    | ✅ Fixed |
| G6  | Cloud Function build failure                     | `local_backend.py` missing `with self._get_connection()` block (`IndentationError`) | ✅ Fixed |

---

## Bug G1 — CORS Error on API Calls

### Symptom

```
Access to XMLHttpRequest blocked by CORS policy: No 'Access-Control-Allow-Origin' header.
```

All API calls from `https://staging.gcp.ashnova.jp` failed with CORS errors.

### Root Cause

The `CORS_ORIGINS` environment variable on the Cloud Run service only contained the CDN IP address (`34.117.111.182`), not the actual custom domain `staging.gcp.ashnova.jp`.

### Fix

Updated Cloud Run env vars via `gcloud run services update --env-vars-file`. The `--update-env-vars` flag **cannot be used for URL values** (values containing `:` cause parse errors). An env vars YAML file must be used instead.

Also added to `.github/workflows/deploy-gcp.yml`:

```yaml
if [ -n "$CUSTOM_DOMAIN" ]; then
CORS_ORIGINS="${CORS_ORIGINS},https://${CUSTOM_DOMAIN}"
fi
```

**Files**: `.github/workflows/deploy-gcp.yml`  
**Key gotcha**: `gcloud run services update --env-vars-file` **replaces all env vars** — the full set must be included every time.

---

## Bug G2 — Firebase Login "Domain Not Authorized"

### Symptom

Google OAuth popup showed: _"This domain is not authorized to run this operation"_.

### Root Cause

`staging.gcp.ashnova.jp` was not registered in Firebase Auth's authorized domains list. Firebase rejects `signInWithPopup` from unregistered origins.

### Fix

Used the Identity Toolkit Admin v2 API to PATCH the authorized domains:

```bash
curl -s -X PATCH \
  "https://identitytoolkit.googleapis.com/admin/v2/projects/ashnova/config" \
  -H "Authorization: Bearer $(gcloud auth print-access-token)" \
  -H "x-goog-user-project: ashnova" \
  -H "Content-Type: application/json" \
  -d '{"authorizedDomains": ["...", "staging.gcp.ashnova.jp"]}'
```

**Critical**: The header `x-goog-user-project: PROJECT_ID` is **required**. Without it the API returns `403 PERMISSION_DENIED`, even with a valid admin token.

Also added an `Update Firebase Authorized Domains` step to `deploy-gcp.yml` that runs after Pulumi outputs are read, so future deployments auto-register new custom domains.

**Files**: `.github/workflows/deploy-gcp.yml`

---

## Bug G3 — `/limits` Returns 404

### Symptom

After login, `GET /limits` returned `404 Not Found`.

### Root Cause

The deployed Cloud Function was running stale code that predated the `limits` route addition. The function source had not been rebuilt and redeployed after the route was added.

### Fix — Cloud Function Rebuild Procedure

The dev container runs on **aarch64**, but Cloud Functions requires **linux/amd64** Python packages. Always build with Docker:

```bash
# Step 1: Build linux/amd64 packages
mkdir -p /tmp/deploy_gcp/.deployment
docker run --rm --platform linux/amd64 \
  -v /tmp/deploy_gcp:/out \
  python:3.12-slim \
  bash -c "pip install --no-cache-dir --target /out/.deployment \
           -r /out/requirements-gcp.txt -q"

# Step 2: Copy app code (must include main.py — see G6)
cp -r services/api/app /tmp/deploy_gcp/.deployment/
cp services/api/function.py /tmp/deploy_gcp/.deployment/main.py  # ← Cloud Build requires main.py
cp services/api/function.py /tmp/deploy_gcp/.deployment/function.py

# Step 3: Zip (exclude __pycache__ from app/ only)
cd /tmp/deploy_gcp/.deployment
find . -name "__pycache__" -path "*/app/*" -exec rm -rf {} + 2>/dev/null
zip -r9q /tmp/deploy_gcp/function-source.zip .

# Step 4: Upload (delete stale tracker files first if resuming)
rm -f ~/.config/gcloud/surface_data/storage/tracker_files/*
gcloud storage cp /tmp/deploy_gcp/function-source.zip \
  gs://ashnova-multicloud-auto-deploy-staging-function-source/function-source.zip

# Step 5: Deploy
gcloud functions deploy multicloud-auto-deploy-staging-api \
  --gen2 --region=asia-northeast1 --runtime=python312 \
  --source=gs://ashnova-multicloud-auto-deploy-staging-function-source/function-source.zip \
  --entry-point=handler --project=ashnova --quiet
```

**Key gotcha**: Cloud Build requires `main.py` to exist in the zip, even when `--entry-point` specifies a different function. Without it: `Build failed: missing main.py`.

---

## Bug G4 — `signInWithPopup` COOP Warning

### Symptom

```
Cross-Origin-Opener-Policy policy would block the window.closed call.
```

Firebase `signInWithPopup` repeatedly polled `popup.closed` but was blocked by COOP. Login still succeeded but generated continuous console warnings.

### Root Cause

Google's OAuth page sets `Cross-Origin-Opener-Policy: same-origin`. When the parent page has no COOP header, browsers block cross-origin window references — including `popup.closed`. The parent page must set `same-origin-allow-popups` to permit this check.

### Fix

Added custom response header to the CDN backend bucket:

```bash
gcloud compute backend-buckets update multicloud-auto-deploy-staging-cdn-backend \
  --custom-response-header 'Cross-Origin-Opener-Policy:same-origin-allow-popups'
gcloud compute url-maps invalidate-cdn-cache \
  multicloud-auto-deploy-staging-cdn-urlmap-v2 --path "/*"
```

Also updated Pulumi code to persist this across future deployments:

```python
# infrastructure/pulumi/gcp/__main__.py
backend_bucket_kwargs = {
    ...
    "custom_response_headers": [
        "Cross-Origin-Opener-Policy: same-origin-allow-popups",
    ],
}
```

**Note**: This warning cannot be fully eliminated — it is generated by the Firebase SDK itself when polling `window.closed`. Setting `same-origin-allow-popups` reduces the warning significantly but does not remove it entirely (the Google OAuth page's own COOP policy still causes one warning on popup open). Login works correctly regardless.

---

## Bug G5 — `/uploads/presigned-urls` Returns 500

### Symptom

```
POST /uploads/presigned-urls → 500 Internal Server Error
Access-Control-Allow-Origin header absent (CORS error follows from the 500)
```

### Root Cause

```
AttributeError: you need a private key to sign credentials.
the credentials you are currently using
<class 'google.auth.compute_engine.credentials.Credentials'> just contains a token.
```

Cloud Functions / Cloud Run instances authenticate via the **Compute Engine metadata server**. The resulting credentials contain only an access token — no private key. The standard `blob.generate_signed_url()` call requires a private key to sign the URL locally, which fails.

### Fix

Pass `service_account_email` and `access_token` directly to `generate_signed_url`. This triggers the **IAM `signBlob` API** path in the GCS library instead of local signing:

```python
# services/api/app/backends/gcp_backend.py
credentials, _ = google.auth.default()
auth_request = google.auth.transport.requests.Request()
credentials.refresh(auth_request)
access_token = credentials.token
sa_email = settings.gcp_service_account  # GCP_SERVICE_ACCOUNT env var

upload_url = blob.generate_signed_url(
    version="v4",
    expiration=timedelta(seconds=settings.presigned_url_expiry),
    method="PUT",
    content_type=ct,
    service_account_email=sa_email,   # ← key addition
    access_token=access_token,         # ← key addition
)
```

### Required IAM Permission

The Cloud Function's service account must have `iam.serviceAccounts.signBlob`. Grant:

```bash
gcloud projects add-iam-policy-binding ashnova \
  --member="serviceAccount:COMPUTE_SA_EMAIL" \
  --role="roles/iam.serviceAccountTokenCreator"
```

This is already present in `infrastructure/pulumi/gcp/__main__.py` as `compute-sa-token-creator`.

### Required Env Var

`GCP_SERVICE_ACCOUNT` must be set on the Cloud Run service. Verify:

```bash
gcloud functions describe multicloud-auto-deploy-staging-api \
  --gen2 --region=asia-northeast1 \
  --format="yaml(serviceConfig.environmentVariables)"
```

---

## Bug G6 — Cloud Function Build Failure (IndentationError)

### Symptom

```
Build failed: Error compiling './app/backends/local_backend.py'...
IndentationError: unindent does not match any outer indentation level (line 324)
```

### Root Cause

The `delete_post` method in `local_backend.py` was missing its `with self._get_connection() as conn:` context manager block. The method body was indented as if inside a `with` block, but the block itself was absent.

### Fix

Restored the full `delete_post` method structure:

```python
def delete_post(self, post_id: str, user: UserInfo) -> dict:
    """投稿を削除"""
    with self._get_connection() as conn:
        from sqlalchemy import text
        check_query = text("SELECT user_id FROM posts WHERE id = :post_id")
        ...
```

Always verify Python syntax before packaging:

```bash
python3 -m py_compile services/api/app/backends/local_backend.py && echo OK
```

---

## Infrastructure Topology (Reference)

| Resource               | Name                                                                 |
| ---------------------- | -------------------------------------------------------------------- |
| Cloud Function (Gen 2) | `multicloud-auto-deploy-staging-api`                                 |
| Cloud Run URL          | `https://multicloud-auto-deploy-staging-api-son5b3ml7a-an.a.run.app` |
| CDN URL map            | `multicloud-auto-deploy-staging-cdn-urlmap-v2`                       |
| CDN backend bucket     | `multicloud-auto-deploy-staging-cdn-backend`                         |
| Frontend GCS bucket    | `ashnova-multicloud-auto-deploy-staging-frontend`                    |
| Uploads GCS bucket     | `ashnova-multicloud-auto-deploy-staging-uploads`                     |
| Function source bucket | `ashnova-multicloud-auto-deploy-staging-function-source`             |
| Firebase / GCP project | `ashnova`                                                            |
| Region                 | `asia-northeast1`                                                    |
| Compute SA             | `899621454670-compute@developer.gserviceaccount.com`                 |

---

## GCS Uploads Bucket CORS (Reference)

```json
[
  {
    "maxAgeSeconds": 3600,
    "method": ["GET", "HEAD", "PUT", "OPTIONS"],
    "origin": ["*"],
    "responseHeader": [
      "Content-Type",
      "Authorization",
      "X-Requested-With",
      "x-ms-blob-type"
    ]
  }
]
```

PUT from browser (presigned URL upload) works without additional changes.
