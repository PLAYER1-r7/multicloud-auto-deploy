# 07 — Environment Status

> Parent: [AI_AGENT_GUIDE.md](AI_AGENT_GUIDE.md)  
> Last verified: 2026-02-21 (All 3 clouds: React SPA migration complete + production integration tests 9/9 PASS + custom domain HTTPS fully operational)

---

## Staging Environment Summary

| Cloud     | Landing (`/`) | SNS App (`/sns/`) | API                                       |
| --------- | ------------- | ----------------- | ----------------------------------------- |
| **GCP**   | ✅            | ✅                | ✅ Cloud Run + Firebase Auth (2026-02-21) |
| **AWS**   | ✅            | ✅                | ✅ Lambda (fully operational)             |
| **Azure** | ✅            | ✅                | ✅ Azure Functions                        |

---

## AWS (ap-northeast-1)

```
CDN URL  : https://d1tf3uumcm4bo1.cloudfront.net
API URL  : https://z42qmqdqac.execute-api.ap-northeast-1.amazonaws.com
```

| Resource              | Name / ID                                                             | Status |
| --------------------- | --------------------------------------------------------------------- | ------ |
| CloudFront            | `E1TBH4R432SZBZ`                                                      | ✅     |
| S3 (frontend)         | `multicloud-auto-deploy-staging-frontend`                             | ✅     |
| S3 (images)           | `multicloud-auto-deploy-staging-images` (CORS: \*)                    | ✅     |
| Lambda (API)          | `multicloud-auto-deploy-staging-api` (Python 3.12, 512MB)             | ✅     |
| Lambda (frontend-web) | `multicloud-auto-deploy-staging-frontend-web` (512MB, 30s)            | ✅     |
| API Gateway           | `z42qmqdqac` (HTTP API v2)                                            | ✅     |
| DynamoDB              | `multicloud-auto-deploy-staging-posts` (PAY_PER_REQUEST)              | ✅     |
| Cognito               | Pool `ap-northeast-1_AoDxOvCib` / Client `1k41lqkds4oah55ns8iod30dv2` | ✅     |
| WAF                   | WebACL attached to CloudFront                                         | ✅     |

**Confirmed working (verified 2026-02-20)**:

- Cognito login → `/sns/auth/callback` → session cookie set ✅
- Post feed, create/edit/delete post ✅
- Profile page (nickname, avatar, bio) ✅
- Image upload: S3 presigned URLs, up to 16 files per post ✅
- Logout → Cognito-hosted logout → redirect back to `/sns/` ✅
- CI/CD pipeline: env vars set correctly on every push ✅

**Known limitations**:

- Production stack shares staging resources (independent prod stack not yet deployed).
- WAF rule set not tuned.

---

## Azure (japaneast)

```
CDN URL  : https://mcad-staging-d45ihd-dseygrc9c3a3htgj.z01.azurefd.net
API URL  : https://multicloud-auto-deploy-staging-func-d8a2guhfere0etcq.japaneast-01.azurewebsites.net/api/HttpTrigger
```

| Resource        | Name                                                                  | Status |
| --------------- | --------------------------------------------------------------------- | ------ |
| Front Door      | `multicloud-auto-deploy-staging-fd` / endpoint: `mcad-staging-d45ihd` | ✅     |
| Storage Account | `mcadwebd45ihd`                                                       | ✅     |
| Function App    | `multicloud-auto-deploy-staging-func` (Python 3.12)                   | ✅     |
| Cosmos DB       | `simple-sns-cosmos` (Serverless)                                      | ✅     |
| Resource Group  | `multicloud-auto-deploy-staging-rg`                                   | ✅     |

**Unresolved issues**:

- End-to-end verification of `PUT /posts/{id}` is incomplete.
- WAF not configured (Front Door Standard SKU).

---

## GCP (asia-northeast1)

```
CDN URL          : http://34.117.111.182
API URL          : https://multicloud-auto-deploy-staging-api-son5b3ml7a-an.a.run.app
Frontend Web URL : https://multicloud-auto-deploy-staging-frontend-web-son5b3ml7a-an.a.run.app
```

| Resource                 | Name / ID                                                         | Status |
| ------------------------ | ----------------------------------------------------------------- | ------ |
| Global IP                | `34.117.111.182`                                                  | ✅     |
| GCS Bucket (frontend)    | `ashnova-multicloud-auto-deploy-staging-frontend`                 | ✅     |
| GCS Bucket (uploads)     | `ashnova-multicloud-auto-deploy-staging-uploads` (public read)    | ✅     |
| Cloud Run (API)          | `multicloud-auto-deploy-staging-api` (Python 3.12)                | ✅     |
| Cloud Run (frontend-web) | `multicloud-auto-deploy-staging-frontend-web` (Docker, port 8080) | ✅     |
| Firestore                | `(default)` — collections: messages, posts                        | ✅     |
| Backend Bucket           | `multicloud-auto-deploy-staging-cdn-backend`                      | ✅     |

**Confirmed working (verified 2026-02-21)**:

- Firebase Google Sign-In → `/sns/auth/callback` → httponly Cookie session ✅
- Post feed, create/edit/delete post ✅
- Image upload: GCS presigned URLs (signed via IAM `signBlob` API), up to 16 files per post ✅
- Uploaded images displayed in post feed ✅
- Firebase ID token auto-refresh (`onIdTokenChanged`) ✅
- Dark theme background SVGs (starfield, ring) rendered correctly ✅

**Fixed issues (2026-02-21)**:

- `GcpBackend` had unimplemented `like_post`/`unlike_post` abstract methods → `TypeError` → `/posts` returned 500
  → Added stub implementations for `like_post`/`unlike_post` (commit `a9bc85e`)
- `frontend-web` Cloud Run `API_BASE_URL` was unset → falling back to localhost:8000
  → Set environment variable via `gcloud run services update`
- Firebase Auth not implemented → Implemented the full Google Sign-In flow (commit `3813577`)
- `x-ms-blob-type` header not registered in GCS CORS → Updated CORS + fixed uploads.js (commits `1cf53b7`, `b5b4de5`)
- GCS presigned URL generation had `content_type` hardcoded as `"image/jpeg"` → Now uses `content_types[index]` correctly (commit `148b7b5`)
- Firebase ID token expiry (401) → Auto-refresh via `onIdTokenChanged` (commit `8110d20`)
- `GCP_SERVICE_ACCOUNT` env var missing in CI/CD → Added to `deploy-gcp.yml` (commit `27b10cc`)
- CSS background SVGs used absolute path `/static/` → Changed to relative path `./` (commit `0ed0805`)
- GCS uploads bucket was private → Granted `allUsers:objectViewer` + added IAMBinding to Pulumi definition (commit `0ed0805`)

**Remaining issues**:

- HTTPS not configured for CDN (HTTP only). Requires `TargetHttpsProxy` + managed SSL certificate.
- SPA deep links via CDN return HTTP 404 (Cloud Run URL works correctly in browsers).

---

## Quick Connectivity Check Commands

```bash
# GCP
curl -s http://34.117.111.182/ | head -3
curl -s https://multicloud-auto-deploy-staging-api-son5b3ml7a-an.a.run.app/health

# AWS
curl -I https://d1tf3uumcm4bo1.cloudfront.net/
curl -s https://z42qmqdqac.execute-api.ap-northeast-1.amazonaws.com/health

# Azure
curl -I https://mcad-staging-d45ihd-dseygrc9c3a3htgj.z01.azurefd.net/
curl -s "https://multicloud-auto-deploy-staging-func-d8a2guhfere0etcq.japaneast-01.azurewebsites.net/api/HttpTrigger/health"
```

---

## Production Environment

> Production has its own independent Pulumi stack (deployed). Resources are separate from staging.  
> Frontend is served as **React SPA** (Vite build) from object storage via CDN — `frontend_web` (Python SSR) is no longer used in production.
> Full migration report: [REACT_SPA_MIGRATION_REPORT.md](REACT_SPA_MIGRATION_REPORT.md)

### Production Endpoints

| Cloud     | CDN / Endpoint                                            | API Endpoint                                                                                     | Distribution ID        |
| --------- | --------------------------------------------------------- | ------------------------------------------------------------------------------------------------ | ---------------------- |
| **AWS**   | `d1qob7569mn5nw.cloudfront.net` / `www.aws.ashnova.jp`    | `https://qkzypr32af.execute-api.ap-northeast-1.amazonaws.com`                                    | E214XONKTXJEJD         |
| **Azure** | `mcad-production-diev0w-f9ekdmehb0bga5aw.z01.azurefd.net` | `https://multicloud-auto-deploy-production-func-cfdne7ecbngnh0d0.japaneast-01.azurewebsites.net` | mcad-production-diev0w |
| **GCP**   | `www.gcp.ashnova.jp`                                      | `https://multicloud-auto-deploy-production-api-son5b3ml7a-an.a.run.app`                          | -                      |

**AWS Production SNS App** (`https://www.aws.ashnova.jp/sns/`):

| Item             | Value                                                                      |
| ---------------- | -------------------------------------------------------------------------- |
| Frontend         | React SPA — S3 `multicloud-auto-deploy-production-frontend/sns/`           |
| CF Function      | `spa-sns-rewrite-production` (LIVE) — rewrites `/sns/` → `/sns/index.html` |
| Lambda (API)     | `multicloud-auto-deploy-production-api`                                    |
| API_BASE_URL     | `https://qkzypr32af.execute-api.ap-northeast-1.amazonaws.com`              |
| Cognito Pool     | `ap-northeast-1_50La963P2`                                                 |
| Cognito Client   | `4h3b285v1a9746sqhukk5k3a7i`                                               |
| Cognito Redirect | `https://www.aws.ashnova.jp/sns/auth/callback`                             |
| DynamoDB         | `multicloud-auto-deploy-production-posts`                                  |

### Custom Domain Status (ashnova.jp) — 2026-02-21

| Cloud     | URL                          | Status                                                                                                                                                   |
| --------- | ---------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **AWS**   | https://www.aws.ashnova.jp   | ✅ **Fully operational** (HTTP/2 200, ACM cert `914b86b1` + CloudFront alias set directly — details: [AWS_HTTPS_FIX_REPORT.md](AWS_HTTPS_FIX_REPORT.md)) |
| **Azure** | https://www.azure.ashnova.jp | ✅ **Fully operational** (HTTPS 200, DigiCert/GeoTrust managed cert, AFD route active)                                                                   |
| **GCP**   | https://www.gcp.ashnova.jp   | ✅ **Fully operational** (HTTPS 200, TLS cert active via ACTIVE cert `ashnova-production-cert-c41311`)                                                   |

#### Completed Work (2026-02-21)

| Cloud | Work                                                                                | Result                                                                                                                                                                                                  |
| ----- | ----------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| AWS   | ACM certificate verification                                                        | ✅ Confirmed cert `914b86b1` for `www.aws.ashnova.jp` (expires 2027-03-12) ISSUED                                                                                                                       |
| AWS   | Set alias + ACM cert directly via `aws cloudfront update-distribution` (2026-02-21) | ✅ Set alias `www.aws.ashnova.jp` + cert `914b86b1` on Distribution `E214XONKTXJEJD` → resolved `NET::ERR_CERT_COMMON_NAME_INVALID` → HTTP/2 200 operational                                            |
| AWS   | Fix Production `frontend-web` Lambda environment variables (2026-02-21)             | ✅ Fixed `API_BASE_URL` empty→`localhost:8000` fallback (cause: `deploy-frontend-web-aws.yml` depended on secrets; production secrets not set) → updated CI/CD to use Pulumi outputs (commit `fd1f422`) |
| Azure | `az afd custom-domain create` + route attach                                        | ✅ DNS Approved → Managed Cert Succeeded (GeoTrust, 2026-02-21 – 2026-08-21)                                                                                                                            |
| Azure | AFD route disable→enable toggle                                                     | ✅ Triggered deployment to edge nodes → HTTPS 200 operational                                                                                                                                           |
| Azure | `az afd custom-domain update` (cert edge deploy)                                    | ✅ `CN=www.azure.ashnova.jp` cert distributed to AFD POP                                                                                                                                                |
| Azure | Set `frontend-web` Function App environment variables                               | ✅ API_BASE_URL, AUTH_PROVIDER, AZURE_TENANT_ID, AZURE_CLIENT_ID, etc. configured                                                                                                                       |
| Azure | Add Azure AD app redirect URI                                                       | ✅ Added `https://www.azure.ashnova.jp/sns/auth/callback`                                                                                                                                               |
| GCP   | `pulumi up --stack production` (SSL cert creation)                                  | ✅ cert `multicloud-auto-deploy-production-ssl-cert-3ee2c3ce` PROVISIONING                                                                                                                              |
| GCP   | Add ACTIVE cert `ashnova-production-cert-c41311`                                    | ✅ Added to HTTPS proxy → `https://www.gcp.ashnova.jp` HTTPS operational immediately                                                                                                                    |
| GCP   | Update Firebase authorized domains                                                  | ✅ Added `www.gcp.ashnova.jp` to Firebase Auth authorized domains                                                                                                                                       |

#### Remaining Work

- **GCP**: Once `multicloud-auto-deploy-production-ssl-cert-3ee2c3ce` becomes ACTIVE, `ashnova-production-cert-c41311` can be removed from the proxy

```bash
# Check GCP SSL cert status
gcloud compute ssl-certificates describe multicloud-auto-deploy-production-ssl-cert-3ee2c3ce \
  --global --format="value(managed.status)"
# Once ACTIVE:
gcloud compute target-https-proxies update multicloud-auto-deploy-production-cdn-https-proxy \
  --global \
  --ssl-certificates=multicloud-auto-deploy-production-ssl-cert-3ee2c3ce
```

#### All-Cloud Test Results (final check 2026-02-21)

```
test-cloud-env.sh production → PASS: 14, FAIL: 0, WARN: 3 (all POST 401 = expected auth guard)
test-azure-sns.sh            → PASS: 10, FAIL: 0 (www.azure.ashnova.jp dedicated tests)
test-gcp-sns.sh              → PASS: 10, FAIL: 0 (www.gcp.ashnova.jp dedicated tests)
```

#### React SPA Migration Test Results (2026-02-21)

```
AWS API Health:   ✅  HTTP 200  status=ok  provider=aws
AWS API CRUD:     ✅  POST→GET(7 msgs)→DELETE 200
AWS React SPA:    ✅  HTTP 200  vite.svg, /sns/assets/index-CNhWHZ0v.js

Azure API Health: ✅  HTTP 200  status=ok  provider=azure
Azure API CRUD:   ✅  POST→GET(3 msgs)→DELETE 200
Azure React SPA:  ✅  HTTP 200  vite.svg, /sns/assets/index-D99WuiGj.js

GCP API Health:   ✅  HTTP 200  status=ok  provider=gcp
GCP API CRUD:     ✅  POST→GET(20 msgs)→DELETE 200
GCP React SPA:    ✅  HTTP 200  vite.svg, /sns/assets/index-eZZwVqtD.js

Result: 9/9 passed 🎉
```

---

## AWS Management Console Links

- [API Gateway](https://ap-northeast-1.console.aws.amazon.com/apigateway)
- [Lambda](https://ap-northeast-1.console.aws.amazon.com/lambda)
- [S3 Bucket](https://s3.console.aws.amazon.com/s3/buckets/multicloud-auto-deploy-staging-frontend)
- [CloudFront](https://console.aws.amazon.com/cloudfront/v3/home#/distributions/E1TBH4R432SZBZ)

## Azure Portal Links

- [Resource Group](https://portal.azure.com/#@/resource/subscriptions/29031d24-d41a-4f97-8362-46b40129a7e8/resourceGroups/multicloud-auto-deploy-staging-rg)
- [Function Apps](https://portal.azure.com/#view/HubsExtension/BrowseResource/resourceType/Microsoft.Web%2Fsites)
- [Front Door](https://portal.azure.com/#view/HubsExtension/BrowseResource/resourceType/Microsoft.Cdn%2Fprofiles)

## GCP Console Links

- [Cloud Run](https://console.cloud.google.com/run?project=ashnova)
- [Cloud Storage](https://console.cloud.google.com/storage/browser?project=ashnova)
- [Firestore](https://console.cloud.google.com/firestore/data?project=ashnova)

---

## FinOps — GCP Unused Static IP Address Audit (2026-02-21)

> Audit performed in response to GCP FinOps findings. All static IP addresses in project `ashnova` were reviewed.

### All IP Addresses

```bash
gcloud compute addresses list --project=ashnova \
  --format="table(name,address,status,addressType,users.list())"
```

| Name                                       | IP Address     | Status          | Created    | Used by                             |
| ------------------------------------------ | -------------- | --------------- | ---------- | ----------------------------------- |
| `multicloud-auto-deploy-production-cdn-ip` | 34.8.38.222    | ✅ IN_USE       | —          | Production CDN (Forwarding Rule ×2) |
| `multicloud-auto-deploy-staging-cdn-ip`    | 34.117.111.182 | ✅ IN_USE       | —          | Staging CDN (Forwarding Rule ×2)    |
| `ashnova-production-ip-c41311`             | 34.54.250.208  | ⚠️ **RESERVED** | 2026-02-11 | None                                |
| `multicloud-frontend-ip`                   | 34.120.43.83   | ⚠️ **RESERVED** | 2026-02-14 | None                                |
| `simple-sns-frontend-ip`                   | 34.149.225.173 | ⚠️ **RESERVED** | 2026-01-30 | None                                |

### Background on Unused IPs

| Name                           | Estimated History                                                                                                                                                             |
| ------------------------------ | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `simple-sns-frontend-ip`       | Created in early project days (when the project was named `simple-sns`, 2026-01-30). Not referenced in Pulumi code or any Forwarding Rule.                                    |
| `ashnova-production-ip-c41311` | Created for Production CDN (as indicated by the Pulumi suffix `c41311`, 2026-02-11), but later replaced by `multicloud-auto-deploy-production-cdn-ip` and became unnecessary. |
| `multicloud-frontend-ip`       | Created 2026-02-14. No references found anywhere in the codebase or documentation. Assumed to have been reserved experimentally and abandoned.                                |

> **Note**: All three are unlinked from any Pulumi code or Forwarding Rule and can be released immediately.

### Release Commands

```bash
gcloud compute addresses delete ashnova-production-ip-c41311 --global --project=ashnova --quiet
gcloud compute addresses delete multicloud-frontend-ip          --global --project=ashnova --quiet
gcloud compute addresses delete simple-sns-frontend-ip          --global --project=ashnova --quiet
```

> ⚠️ Deletion is irreversible. Confirm each IP has no associated resources via `gcloud compute addresses describe <name> --global` before executing.

---

## FinOps — GCP Unused Cloud Storage Bucket Audit (2026-02-21)

> Conducted as a follow-up to the static IP audit. Legacy Terraform-era buckets and a broken Cloud Function were identified.

### All Buckets (Project: ashnova)

| Bucket Name                                                              | Size      | Verdict       | Notes                                                                           |
| ------------------------------------------------------------------------ | --------- | ------------- | ------------------------------------------------------------------------------- |
| `ashnova-multicloud-auto-deploy-production-frontend`                     | —         | ✅ Active     | Managed by Pulumi                                                               |
| `ashnova-multicloud-auto-deploy-production-function-source`              | 5 MB      | ✅ Active     | Managed by Pulumi                                                               |
| `ashnova-multicloud-auto-deploy-production-uploads`                      | —         | ✅ Active     | Managed by Pulumi                                                               |
| `ashnova-multicloud-auto-deploy-staging-frontend`                        | —         | ✅ Active     | Managed by Pulumi                                                               |
| `ashnova-multicloud-auto-deploy-staging-function-source`                 | 5 MB      | ✅ Active     | Managed by Pulumi                                                               |
| `ashnova-multicloud-auto-deploy-staging-landing`                         | 8 KB      | ✅ Active     | Managed by Pulumi                                                               |
| `ashnova-multicloud-auto-deploy-staging-uploads`                         | —         | ✅ Active     | Managed by Pulumi                                                               |
| `ashnova.firebasestorage.app`                                            | —         | ✅ Keep       | Firebase system-managed                                                         |
| `ashnova_cloudbuild`                                                     | —         | ✅ Keep       | Cloud Build system-managed                                                      |
| `gcf-v2-sources-899621454670-asia-northeast1`                            | 433 MB    | ✅ Keep       | Source for active Cloud Function v2                                             |
| `gcf-v2-uploads-899621454670.asia-northeast1.cloudfunctions.appspot.com` | —         | ✅ Keep       | Cloud Functions upload staging                                                  |
| `ashnova-staging-frontend`                                               | **empty** | 🗑️ **Delete** | Terraform legacy. Replaced by `ashnova-multicloud-auto-deploy-staging-frontend` |
| `ashnova-staging-function-source`                                        | **65 MB** | 🗑️ **Delete** | Terraform legacy. Contains old zip from 2026-02-14                              |
| `multicloud-auto-deploy-tfstate`                                         | **empty** | 🗑️ **Delete** | Old Terraform state bucket. Empty.                                              |
| `multicloud-auto-deploy-tfstate-gcp`                                     | **6 KB**  | 🗑️ **Delete** | Holds only the Terraform state for the two buckets above                        |

### Background on Deletable Buckets

| Bucket Name                          | Estimated History                                                                                                                                                                     |
| ------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `ashnova-staging-frontend`           | Frontend bucket from the old Terraform config (`ashnova-staging-*` naming). Fully migrated to `ashnova-multicloud-auto-deploy-staging-frontend` (Pulumi-managed). Empty.              |
| `ashnova-staging-function-source`    | Cloud Function source bucket from the same Terraform config. Contains a stale 65 MB zip from 2026-02-14. Replaced by `ashnova-multicloud-auto-deploy-staging-function-source` (5 MB). |
| `multicloud-auto-deploy-tfstate`     | Created as a candidate for AWS Terraform state bucket, never used. Empty.                                                                                                             |
| `multicloud-auto-deploy-tfstate-gcp` | Holds the Terraform state for the `ashnova-staging-*` two buckets. No `.tf` files exist in the codebase. Delete all four as a set.                                                    |

### Bonus: Broken Cloud Function (related resource)

| Resource                               | State      | Details                                                                                                                                                           |
| -------------------------------------- | ---------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `mcad-staging-api` (Cloud Function v2) | **FAILED** | `Cloud Run service not found` error. The Cloud Run service was deleted but the Function definition remains. No references in Pulumi/current code. Safe to delete. |

### Delete Commands

```bash
# Delete 4 buckets (including contents) — delete tfstate-gcp last
gcloud storage rm --recursive gs://ashnova-staging-frontend           --project=ashnova
gcloud storage rm --recursive gs://ashnova-staging-function-source    --project=ashnova
gcloud storage rm --recursive gs://multicloud-auto-deploy-tfstate     --project=ashnova
gcloud storage rm --recursive gs://multicloud-auto-deploy-tfstate-gcp --project=ashnova

# Also delete the broken Cloud Function
gcloud functions delete mcad-staging-api \
  --region=asia-northeast1 --project=ashnova --v2 --quiet
```

> ⚠️ `multicloud-auto-deploy-tfstate-gcp` contains the Terraform state for `ashnova-staging-frontend` and `ashnova-staging-function-source`. Delete all four buckets as a set.

---

## Next Section

→ [08 — Runbooks](AI_AGENT_08_RUNBOOKS.md)
