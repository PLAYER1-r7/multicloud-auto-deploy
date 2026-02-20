# Environment Status Report

Last updated: 2026-02-20

---

## Summary

All three cloud staging environments are fully operational. The landing page is served at the CDN root
(`/`) and the React SNS app is served under the `/sns/` path on every cloud.

| Cloud | Landing Page (`/`) | SNS App (`/sns/`) | API |
|-------|-------------------|-------------------|-----|
| GCP   | ✅ `http://34.117.111.182/` | ✅ `http://34.117.111.182/sns/` | ✅ Cloud Run |
| AWS   | ✅ `https://d1tf3uumcm4bo1.cloudfront.net/` | ✅ `https://d1tf3uumcm4bo1.cloudfront.net/sns/` | ⚠️ Lambda (500) |
| Azure | ✅ `https://mcad-staging-d45ihd-dseygrc9c3a3htgj.z01.azurefd.net/` | ✅ `https://mcad-staging-d45ihd-dseygrc9c3a3htgj.z01.azurefd.net/sns/` | ✅ Azure Functions |

---

## Staging Environment Details

### GCP

| Component      | Value |
|----------------|-------|
| CDN IP         | `34.117.111.182` (Classic External HTTP Load Balancer) |
| Storage Bucket | `ashnova-multicloud-auto-deploy-staging-frontend` |
| API            | `https://multicloud-auto-deploy-staging-api-son5b3ml7a-an.a.run.app` |
| Project        | `ashnova` |
| Region         | `asia-northeast1` |

### AWS

| Component       | Value |
|-----------------|-------|
| CloudFront URL  | `https://d1tf3uumcm4bo1.cloudfront.net` |
| Distribution ID | `E1TBH4R432SZBZ` |
| S3 Bucket       | `multicloud-auto-deploy-staging-frontend` |
| API             | `https://z42qmqdqac.execute-api.ap-northeast-1.amazonaws.com` |
| Region          | `ap-northeast-1` |

### Azure

| Component       | Value |
|-----------------|-------|
| Front Door URL  | `https://mcad-staging-d45ihd-dseygrc9c3a3htgj.z01.azurefd.net` |
| Profile         | `multicloud-auto-deploy-staging-fd` |
| Endpoint        | `mcad-staging-d45ihd` |
| Storage Account | `mcadwebd45ihd` (origin: `mcadwebd45ihd.z11.web.core.windows.net`) |
| Function App    | `multicloud-auto-deploy-staging-func` |
| API             | `https://multicloud-auto-deploy-staging-func-d8a2guhfere0etcq.japaneast-01.azurewebsites.net/api/HttpTrigger` |
| Resource Group  | `multicloud-auto-deploy-staging-rg` |
| Region          | `japaneast` |

---

## CI/CD Status (2026-02-20)

| Workflow                     | Branch  | Status     | HEAD      |
|------------------------------|---------|------------|-----------|
| Deploy Frontend to GCP       | develop | ✅ success | `591ce0b` |
| Deploy Frontend to AWS       | develop | ✅ success | `591ce0b` |
| Deploy Frontend to Azure     | develop | ✅ success | `591ce0b` |
| Deploy Landing Page to GCP   | develop | ✅ success | `591ce0b` |
| Deploy Landing Page to AWS   | develop | ✅ success | `591ce0b` |
| Deploy Landing Page to Azure | develop | ✅ success | `591ce0b` |

---

## Bucket / Storage Layout

All three clouds share the same directory structure within their respective storage buckets:

```
bucket-root/
├── index.html          ← Landing page ("Ashnova - マルチクラウド静的サイト")
├── error.html          ← Error page
├── aws/                ← Cloud-specific static asset directories
├── azure/
├── gcp/
└── sns/                ← React SNS application (Vite build output)
    ├── index.html      ←   Content-Type: text/html; charset=utf-8
    ├── vite.svg
    └── assets/
        ├── index-*.js
        └── index-*.css
```

---

## Issues Fixed — 2026-02-20

### Fix 1 — Wrong workflow files were being edited

**Commit:** `c347727`

**Problem:**
The repository contains GitHub Actions workflows at two locations:
- `.github/workflows/` — the **actual** path GitHub Actions reads
- `multicloud-auto-deploy/.github/workflows/` — a subdirectory copy that CI ignores

All prior fixes had been applied exclusively to the subdirectory copy. CI continued using the
unmodified root-level files, producing a confusing state where `git show` and `cat` showed the
correct content while CI logs showed old values.

**Discovery:**
Compared blob SHAs using `git cat-file` (local object store) against the GitHub Contents API
(`GET /repos/.../contents/.github/workflows/...?ref=<sha>`). The SHAs differed, confirming that
CI was reading a different file from the one being edited.

**Fix:**
Applied all corrections to the six workflow files under `.github/workflows/` (root level) and kept
the subdirectory copies in sync.

---

### Fix 2 — CI authentication failures for landing page deployments

**Commits:** `1e465e1`, `c347727`

**Problem:**
`deploy-landing-gcp.yml` specified `workload_identity_provider` and `deploy-landing-aws.yml`
specified `role-to-assume`. Neither secret was configured in the repository's Actions secrets,
causing immediate authentication failures.

**Fix:**
Aligned both workflows with the authentication method already used by the working frontend workflows:

| Workflow | Old (broken) | New (working) |
|----------|--------------|---------------|
| `deploy-landing-gcp.yml` | `workload_identity_provider` (secret not set) | `credentials_json: ${{ secrets.GCP_CREDENTIALS }}` |
| `deploy-landing-aws.yml` | `role-to-assume` (secret not set) | `aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}` + `aws-secret-access-key` |

---

### Fix 3 — React SNS app overwrote the landing page at CDN root

**Commits:** `a585f22`, `c347727`, `982c0d5`

**Problem:**
`deploy-frontend-*.yml` synced the Vite `dist/` output directly to the storage bucket root.
Every frontend CI run replaced the landing page `index.html` with the React app's `index.html`.
Additionally, the `deploy-landing-*.yml` workflows deployed to a *separate* bucket that was not
connected to any CDN, so the landing page was never publicly reachable.

**Fix:**
1. Changed all frontend workflows to deploy to the `sns/` prefix:

   | Cloud | Old | New |
   |-------|-----|-----|
   | GCP   | `gs://bucket/` | `gs://bucket/sns/` |
   | AWS   | `s3://bucket/` | `s3://bucket/sns/` |
   | Azure | `$web/` | `$web/sns/` |

2. Changed all landing page workflows to target the CDN-connected frontend bucket:

   | Cloud | Old bucket | New bucket |
   |-------|------------|------------|
   | GCP   | `...-staging-landing` | `...-staging-frontend` |
   | AWS   | `...-staging-landing` | `...-staging-frontend` |
   | Azure | `mcadlanding752` | `mcadwebd45ihd` (see Fix 6) |

3. Set `base: '/sns/'` in `services/frontend_react/vite.config.ts` so all asset URLs in the
   React bundle are rooted at `/sns/` (e.g. `/sns/assets/index-abc.js`).

---

### Fix 4 — AUTH_DISABLED=true in staging for AWS and Azure

**Commit:** `6699586`

**Problem:**
AWS and Azure backend deployment workflows had a conditional block that was intended to enable auth
only in production, but the condition was inverted — it set `AUTH_DISABLED=true` in staging.
GCP was not affected because it had a separate, correct configuration.

**Fix:**
Removed the conditional entirely and always set `AUTH_DISABLED=false` with the appropriate
`AUTH_PROVIDER` value for each cloud.

---

### Fix 5 — Landing page SNS link pointed to `:8080` on CDN hostnames

**Commit:** `0c485b7`

**Problem:**
`static-site/index.html` contained JavaScript that unconditionally appended `:8080` to the
current hostname to build the SNS app URL. On CDN hostnames such as
`d1tf3uumcm4bo1.cloudfront.net`, this produced the invalid URL
`https://d1tf3uumcm4bo1.cloudfront.net:8080`, which browsers cannot resolve.

**Fix:**
Replaced the single-path logic with three-environment detection:

```javascript
const isLocal = hostname === 'localhost' || hostname === '127.0.0.1';
const isDevContainer = hostname.includes('preview') || hostname.includes('github.dev')
                    || hostname.includes('codespaces') || hostname.includes('app.github.dev');

if (isLocal) {
    // Docker Compose: each service runs on a dedicated port
    snsLink.href = `${protocol}//${hostname}:8080`;
    apiDocsLink.href = `${protocol}//${hostname}:8000/docs`;
} else if (isDevContainer) {
    // VS Code / Codespaces: port numbers are encoded in the forwarding URL
    snsLink.href = `${protocol}//${hostname.replace(/-(5173|3000)\./, '-8080.')}`;
    apiDocsLink.href = `${protocol}//${hostname.replace(/-(5173|3000)\./, '-8000.')}/docs`;
} else {
    // Staging / Production CDN: SNS app is on the same origin under /sns/
    snsLink.href = '/sns/';
    apiDocsLink.href = '/sns/#/api-docs';
}
```

---

### Fix 6 — Azure deployments targeting the wrong storage account

**Commit:** `f1c7834`

**Problem:**
Azure Front Door's origin was configured against `mcadwebd45ihd.z11.web.core.windows.net`, but
all Azure workflow files set `AZURE_STORAGE_ACCOUNT: mcadstaticweb752`. Files were being uploaded
to a storage account that Front Door never served, so the CDN continued to return stale content
regardless of how many times the workflows ran or caches were purged.

**Discovery:**
Ran `az afd origin list` to inspect the actual Front Door origin hostname and compared it against
the `AZURE_STORAGE_ACCOUNT` value in the workflow environment variables.

**Fix:**
Updated `AZURE_STORAGE_ACCOUNT` in all four affected workflow files:

```
mcadstaticweb752  →  mcadwebd45ihd
```

Files updated:
- `.github/workflows/deploy-frontend-azure.yml`
- `.github/workflows/deploy-landing-azure.yml`
- `multicloud-auto-deploy/.github/workflows/deploy-frontend-azure.yml`
- `multicloud-auto-deploy/.github/workflows/deploy-landing-azure.yml`

---

### Fix 7 — AWS `/sns/` caused a file download instead of rendering the app

**Commit:** `591ce0b`

**Problem:**
Clicking the SNS link on the AWS landing page triggered a browser file download dialog.
Inspecting the CloudFront response revealed `content-type: binary/octet-stream` for `sns/index.html`.

**Root cause:**
`aws s3 sync` does not infer `Content-Type: text/html` for `.html` files produced by a Vite build.
Without an explicit content-type, S3 stores them as `application/octet-stream`, and CloudFront
forwards that header verbatim, causing browsers to download rather than render the response.

**Immediate fix (manual):**
```bash
aws s3 cp s3://bucket/sns/index.html s3://bucket/sns/index.html \
  --metadata-directive REPLACE \
  --content-type "text/html; charset=utf-8" \
  --cache-control "public, max-age=300, must-revalidate"
```

**Permanent fix (workflow):**
Split the single `aws s3 sync` command into two passes:

```yaml
# Pass 1: JS/CSS/images — S3 reliably detects these content types
aws s3 sync dist/ s3://$S3_BUCKET/sns/ \
  --delete \
  --cache-control "public, max-age=3600" \
  --exclude "*.html"

# Pass 2: HTML files — must be explicit to avoid binary/octet-stream
aws s3 sync dist/ s3://$S3_BUCKET/sns/ \
  --content-type "text/html; charset=utf-8" \
  --cache-control "public, max-age=300, must-revalidate" \
  --exclude "*" --include "*.html"
```

---

### Fix 8 — AWS CloudFront returned 403 for `/sns/` (missing directory index)

**Manual infrastructure change (not in a commit)**

**Problem:**
Accessing `/sns/` returned a 403 error. S3 does not serve `index.html` automatically for
directory-style paths, and CloudFront's "Default Root Object" setting only applies to the root `/`.

**Fix:**
Created a CloudFront Function (`staging-directory-index`) and attached it as a `viewer-request`
handler to distribution `E1TBH4R432SZBZ`. The function rewrites URI paths ending in `/` or with
no file extension to append `index.html`:

```javascript
function handler(event) {
    var uri = event.request.uri;
    if (uri.endsWith('/')) {
        event.request.uri += 'index.html';
    } else if (!uri.includes('.', uri.lastIndexOf('/'))) {
        event.request.uri += '/index.html';
    }
    return event.request;
}
```

---

## Known Remaining Issues

| Issue | Cloud | Severity | Notes |
|-------|-------|----------|-------|
| `GET /api/messages/` returns 500 | AWS | Medium | Lambda Layer (`mangum`) not attached. See [AWS_LAMBDA_LAYER_STRATEGY.md](./AWS_LAMBDA_LAYER_STRATEGY.md) |
| Production environment not deployed | All | Low | `main` branch not yet verified |

---

## Related Documents

- [Static Site Architecture](./STATIC_SITE_ARCHITECTURE.md)
- [AWS Lambda Layer Strategy](./AWS_LAMBDA_LAYER_STRATEGY.md)
- [CDN Setup](./CDN_SETUP.md)
- [CI/CD Setup](./CICD_SETUP.md)
- [Endpoints Reference](./ENDPOINTS.md)
- [Troubleshooting](./TROUBLESHOOTING.md)

---

## Change Log

| Date | Commit | Description |
|------|--------|-------------|
| 2026-02-20 | `591ce0b` | fix(aws): explicit `text/html` content-type in s3 sync to prevent file download |
| 2026-02-20 | `f1c7834` | fix(azure): deploy to `mcadwebd45ihd` — the actual Front Door origin |
| 2026-02-20 | `0c485b7` | fix(landing): environment-aware SNS link URL (local / dev-container / CDN) |
| 2026-02-20 | `982c0d5` | fix(frontend): set `base: /sns/` in vite.config; add CDN invalidation to workflows |
| 2026-02-20 | `c347727` | fix(ci): correct root-level workflows — auth, bucket names, `sns/` prefix |
| 2026-02-20 | `1e465e1` | fix(ci): use `credentials_json` / `access-key-id` auth in landing page workflows |
| 2026-02-20 | `a585f22` | fix(frontend): deploy React app to `sns/` prefix; landing page at bucket root |
| 2026-02-20 | `6699586` | fix(aws,azure): always set `AUTH_DISABLED=false` in staging |
| 2026-02-17 | —        | Initial environment status documented |
