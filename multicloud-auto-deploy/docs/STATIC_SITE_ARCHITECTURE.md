# Static Site Architecture

> **AI Agent Note**: Design decisions and implementation details for cloud-specific landing pages co-hosted with the SNS React app under a single CDN per cloud. Covers URL structure, path-based routing, cost analysis, and deployment procedures.

---

## Overview

Each cloud hosts **two web properties** under a single CDN endpoint:

| Path    | Content                                   | Source                          |
| ------- | ----------------------------------------- | ------------------------------- |
| `/`     | Cloud-specific landing page (static HTML) | `static-site/{aws,azure,gcp}/`  |
| `/sns/` | SNS React SPA                             | `services/frontend_react/dist/` |

Traffic is separated by **path-based routing** at the CDN layer — no secondary IP address or endpoint is required.

---

## URL Structure

```
AWS   → https://aws.yourdomain.com/        (landing page, AWS-themed)
        https://aws.yourdomain.com/sns/    (SNS app)

Azure → https://azure.yourdomain.com/
        https://azure.yourdomain.com/sns/

GCP   → https://gcp.yourdomain.com/
        https://gcp.yourdomain.com/sns/
```

### Design Options Considered

| Option                                   | Description                                                 | Pros                              | Cons                                                                    |
| ---------------------------------------- | ----------------------------------------------------------- | --------------------------------- | ----------------------------------------------------------------------- |
| **A — Separate subdomains**              | `app.yourdomain.com` (SNS) + `aws.yourdomain.com` (landing) | Clean separation                  | Requires 2 CDN endpoints / 2 IPs per cloud (~$18-25/month extra on GCP) |
| **B — Path routing on one subdomain** ✅ | `aws.yourdomain.com/` (landing) + `aws.yourdomain.com/sns/` | Single CDN, single IP, lower cost | React app must be built with `base="/sns/"`                             |
| **C — One apex domain, path per cloud**  | `yourdomain.com/aws/`, `yourdomain.com/azure/`              | Single domain                     | Doesn't convey cloud-specific branding; no multi-CDN value              |

**Selected: Option B** — path-based routing on cloud-specific subdomains.

---

## Architecture per Cloud

### AWS — CloudFront

```
cdn_ip (CloudFront)
├── /sns/*   →  frontend_bucket (S3)   ← React app (built with base="/sns/")
└── /*       →  landing_bucket  (S3)   ← static-site/aws/index.html
```

**Resources**:

- `cloudfront_distribution_with_landing` — single distribution, two origins
  - Origin `"sns"`: `{project}-{stack}-frontend` S3 bucket (OAI-protected)
  - Origin `"landing"`: `{project}-{stack}-landing` S3 bucket (OAI-protected)
- `ordered_cache_behaviors`: `path_pattern = "/sns/*"` → SNS origin, TTL 3600s
- Default cache behavior: `/` → landing origin, TTL 86400s
- Custom error responses:
  - `404 → /error.html` (landing error page)
  - `403 → 200, /sns/index.html` (React SPA client-side routing fallback)
- Optional custom domain via ACM certificate (`staticSiteDomain` + `staticSiteAcmCertificateArn` config keys)

**IaC file**: `infrastructure/pulumi/aws/__main__.py`

---

### Azure — Front Door

```
Front Door endpoint  (single endpoint)
├── /sns/*   →  frontdoor_origin_group   ← frontend_storage ($web)
└── /*       →  landing_origin_group     ← landing_storage  ($web)
```

**Resources**:

- `frontdoor_profile` — Standard SKU (~$35/month, WAF requires Premium ~$330/month)
- `frontdoor_endpoint` — single endpoint for both routes
- `frontdoor_origin_group` + `frontdoor_origin` — SNS React app (frontend_storage)
- `landing_origin_group` + `landing_origin` — landing page (landing_storage)
- `frontdoor_sns_route` — `patterns_to_match=["/sns/*"]`, depends_on landing_origin
- `frontdoor_route` — `patterns_to_match=["/*"]`, default catch-all (lower priority)
- Optional custom domain via Front Door Managed Certificate (`staticSiteDomain` config key)

> **Note on route priority**: In Azure Front Door Standard, more specific patterns (`/sns/*`) take precedence over wildcard (`/*`) naturally. The `frontdoor_sns_route` is created before `frontdoor_route` (`depends_on`) to ensure correct ordering during initial deployment.

**IaC file**: `infrastructure/pulumi/azure/__main__.py`

---

### GCP — Cloud CDN (URL Map + GCS Website Hosting)

```
cdn_ip_address (Global Classic External LB — scheme=EXTERNAL)
└── /*    →  backend_bucket  ← frontend_bucket (GCS website hosting)
                ├─ /          → landing page (index.html at bucket root)
                └─ /sns/*     → SNS React SPA

SPA deep-link behaviour (scheme=EXTERNAL):
  /sns/unknown-path → GCS serves index.html body with HTTP 404
  Cloud CDN forwards the 404 as-is (no status override).
  Browsers render the SPA correctly despite the 404 status.
```

**Resources**:

- `cdn_ip_address` — single Global External IP (~$7.30/month)
- `frontend_bucket` — GCS bucket with `website.not_found_page = "index.html"`; for unknown paths GCS returns the `index.html` body **with HTTP 404 status**
- `backend_bucket` — Cloud CDN backend pointing to `frontend_bucket`; CDN caching enabled for static assets
- `url_map` — `default_service: backend_bucket`; no advanced routing rules (see note below)
- `uploads_bucket` — separate GCS bucket for image uploads (`ashnova-{project}-{stack}-uploads`); the Compute Engine service account has `roles/storage.objectAdmin` on this bucket and `roles/iam.serviceAccountTokenCreator` on itself (required for signed URL generation via IAM signBlob API)
- SSL certificate (`managed_ssl_cert`): covers custom domain when configured

> **SPA Deep-Link Routing — GCP Classic LB limitation**: `defaultCustomErrorResponsePolicy`
> (which would convert GCS 4xx to HTTP 200) is only supported on
> `load_balancing_scheme = "EXTERNAL_MANAGED"` (Global Application Load Balancer).
> The current setup uses the classic `EXTERNAL` scheme to stay within the free-tier
> `BACKEND_BUCKETS` quota. As a result, direct navigation to `/sns/unknown-path` returns
> HTTP 404 with the SPA HTML body — browsers render the page correctly, but HTTP clients
> (e.g., `curl`, Lighthouse, SEO crawlers) see 404. The staging test suite accepts
> `404 + <html>` as a passing SPA fallback check.
>
> **To achieve true HTTP 200**, migrate forwarding rules to `EXTERNAL_MANAGED`
> and re-add `defaultCustomErrorResponsePolicy` to the URL map.
> This is tracked as a future improvement.

> **Design note**: A separate `landing_bucket` + `landing_backend_bucket` was initially used. This was consolidated to a single `backend_bucket` to stay within the GCP `BACKEND_BUCKETS` project quota (limit: 3). Landing page files are deployed to the root of `frontend_bucket`; SNS app files are deployed under the `sns/` prefix of the same bucket.

**IaC file**: `infrastructure/pulumi/gcp/__main__.py`

---

## Cost Analysis

### Per-cloud monthly estimates (Tokyo region)

| Resource                      | AWS                            | Azure                    | GCP                         |
| ----------------------------- | ------------------------------ | ------------------------ | --------------------------- |
| CDN / LB                      | CloudFront ~$1-5 (pay-per-use) | Front Door Standard ~$35 | Global LB IP ~$7.30         |
| Storage                       | S3 ~$0.025/GB                  | Blob ~$0.018/GB          | GCS ~$0.020/GB              |
| SSL cert                      | ACM free                       | Front Door Managed free  | Google Managed free         |
| **Extra cost vs single-site** | ~$0 (same distribution)        | ~$0 (same endpoint)      | ~$0 (same IP, URL Map free) |

### Why path routing saves cost

Previously (Session 2) each cloud had a **separate** CDN and IP for the landing page:

| Cloud | Previous approach           | Extra monthly cost                          |
| ----- | --------------------------- | ------------------------------------------- |
| AWS   | 2nd CloudFront distribution | ~$0 (CloudFront is pay-per-use, negligible) |
| Azure | 2nd Front Door endpoint     | +~$5-10/endpoint                            |
| GCP   | 2nd Global IP + LB          | +~$7.30 (IP) + LB overhead                  |

**Total savings**: ~$12-17/month by using path routing on the existing CDN.

---

## React App Configuration

The SNS React app is built with a non-root base path so all asset URLs resolve correctly under `/sns/`:

```typescript
// services/frontend_react/vite.config.ts
export default defineConfig({
  plugins: [react()],
  base: process.env.VITE_BASE_PATH ?? "/sns/",
});
```

| Scenario                               | Command                        |
| -------------------------------------- | ------------------------------ |
| Production build (deployed to `/sns/`) | `npm run build`                |
| Local development (root path)          | `VITE_BASE_PATH=/ npm run dev` |

---

## Static Site Files

Cloud-specific HTML files are stored in separate subdirectories:

```
static-site/
├── aws/
│   ├── index.html    # AWS-themed (orange #FF9900, dark #232F3E)
│   └── error.html
├── azure/
│   ├── index.html    # Azure-themed (blue #0078D4, dark #050F1C)
│   └── error.html
└── gcp/
    ├── index.html    # GCP-themed (Google 4-color palette, dark #0D1117)
    └── error.html
```

Each page highlights the cloud provider's branding, services, and links to `/sns/` for the SNS demo app.

---

## Deployment

### 1. Build the React app

The API URL is baked into the JavaScript bundle at build time via `VITE_API_URL`. **Each cloud requires a separate build** — do not share the same build artifact across clouds.

```bash
cd services/frontend_react
npm install
```

| Target           | Build command                                                                                                               |
| ---------------- | --------------------------------------------------------------------------------------------------------------------------- |
| AWS staging      | `VITE_API_URL=https://z42qmqdqac.execute-api.ap-northeast-1.amazonaws.com npm run build`                                    |
| AWS production   | `VITE_API_URL=https://qkzypr32af.execute-api.ap-northeast-1.amazonaws.com npm run build`                                    |
| Azure staging    | `VITE_API_URL=https://multicloud-auto-deploy-staging-func-d8a2guhfere0etcq.japaneast-01.azurewebsites.net npm run build`    |
| Azure production | `VITE_API_URL=https://multicloud-auto-deploy-production-func-cfdne7ecbngnh0d0.japaneast-01.azurewebsites.net npm run build` |
| GCP staging      | `VITE_API_URL=https://mcad-staging-api-son5b3ml7a-an.a.run.app npm run build`                                               |
| GCP production   | `VITE_API_URL=https://mcad-production-api-son5b3ml7a-an.a.run.app npm run build`                                            |

All builds output to `dist/` with `base="/sns/"` (asset URLs prefixed with `/sns/assets/`). See [`.env.example`](../../services/frontend_react/.env.example) for the full API URL reference.

### 2. Deploy infrastructure (first time)

```bash
# AWS
cd infrastructure/pulumi/aws
pulumi stack select staging
pulumi up

# Azure
cd infrastructure/pulumi/azure
pulumi stack select staging
pulumi up

# GCP
cd infrastructure/pulumi/gcp
pulumi stack select staging
pulumi up
```

### 3. Upload landing pages

```bash
# Deploy to all clouds
./scripts/deploy-static-site.sh staging all

# Deploy to a specific cloud
./scripts/deploy-static-site.sh staging aws
./scripts/deploy-static-site.sh staging azure
./scripts/deploy-static-site.sh staging gcp
```

### 4. Upload SNS React app

Build for the target cloud first (see step 1), then upload:

```bash
# AWS (staging)
VITE_API_URL=https://z42qmqdqac.execute-api.ap-northeast-1.amazonaws.com npm run build
aws s3 sync dist/ s3://multicloud-auto-deploy-staging-frontend/sns/ \
  --delete --cache-control "max-age=3600" --exclude "*.map"
aws cloudfront create-invalidation --distribution-id <CF_ID> --paths "/sns/*"

# Azure (staging)
VITE_API_URL=https://multicloud-auto-deploy-staging-func-d8a2guhfere0etcq.japaneast-01.azurewebsites.net npm run build
az storage blob upload-batch \
  --account-name mcadwebd45ihd \
  --destination '$web/sns' \
  --source dist/ --overwrite

# GCP (staging)
VITE_API_URL=https://mcad-staging-api-son5b3ml7a-an.a.run.app npm run build
gsutil -m -h "Cache-Control:public, max-age=3600" cp -r dist/* gs://ashnova-multicloud-auto-deploy-staging-frontend/sns/
```

> Replace `staging` → `production` values as needed. Refer to build step 1 for all API URL values.

---

## Custom Domain Setup

### Step-by-step per cloud

#### AWS

```bash
# 1. Request ACM certificate (must be us-east-1 for CloudFront)
aws acm request-certificate \
  --domain-name aws.yourdomain.com \
  --validation-method DNS \
  --region us-east-1

# 2. Set Pulumi config
cd infrastructure/pulumi/aws
pulumi config set staticSiteDomain aws.yourdomain.com
pulumi config set staticSiteAcmCertificateArn arn:aws:acm:us-east-1:ACCOUNT:certificate/ID
pulumi up

# 3. DNS: CNAME aws.yourdomain.com → <landing_cloudfront_domain output>
```

URLs after setup:

- `https://aws.yourdomain.com/` — landing page
- `https://aws.yourdomain.com/sns/` — SNS app

#### Azure

```bash
# 1. Set Pulumi config
cd infrastructure/pulumi/azure
pulumi config set staticSiteDomain azure.yourdomain.com
pulumi up

# 2. DNS: CNAME azure.yourdomain.com → <frontdoor_hostname output>
# Front Door Managed Certificate is provisioned automatically.
```

#### GCP

```bash
# 1. Set Pulumi config (both keys for unified SSL cert)
cd infrastructure/pulumi/gcp
pulumi config set customDomain gcp.yourdomain.com
pulumi config set staticSiteDomain gcp.yourdomain.com
pulumi up

# 2. DNS: A record gcp.yourdomain.com → <cdn_ip_address output>
# Google Managed SSL certificate takes 10-60 minutes after DNS propagates.
```

---

## Pulumi Output Reference

### AWS

| Output key               | Description                                         |
| ------------------------ | --------------------------------------------------- |
| `landing_bucket_name`    | S3 bucket for landing page files                    |
| `landing_cloudfront_id`  | CloudFront distribution ID (for cache invalidation) |
| `landing_cloudfront_url` | CloudFront HTTPS URL (`/` = landing)                |
| `sns_url`                | SNS app URL (`/sns/`)                               |
| `landing_custom_domain`  | Custom domain (if configured)                       |
| `sns_custom_url`         | SNS app URL on custom domain                        |

### Azure

| Output key                | Description                                |
| ------------------------- | ------------------------------------------ |
| `landing_storage_name`    | Blob Storage account for landing page      |
| `landing_frontdoor_url`   | Front Door HTTPS URL (`/` = landing)       |
| `sns_url`                 | SNS app URL (`/sns/`)                      |
| `frontdoor_endpoint_name` | Front Door endpoint name (for cache purge) |
| `landing_custom_domain`   | Custom domain (if configured)              |
| `sns_custom_url`          | SNS app URL on custom domain               |

### GCP

| Output key                  | Description                                                                  |
| --------------------------- | ---------------------------------------------------------------------------- |
| `landing_bucket`            | GCS bucket where landing page files are deployed (same as `frontend_bucket`) |
| `cdn_ip_address`            | Global LB IP address                                                         |
| `landing_url`               | Landing page URL (`http://<ip>/`)                                            |
| `sns_url`                   | SNS app URL (`http://<ip>/sns/`)                                             |
| `landing_custom_domain`     | Custom domain (if configured)                                                |
| `landing_custom_domain_url` | Custom domain HTTPS URL                                                      |
| `sns_custom_url`            | SNS app URL on custom domain                                                 |

> **Note**: `landing_bucket` and `frontend_bucket` resolve to the same GCS bucket. Landing page files (`index.html`, `error.html`) are deployed to the bucket root; SNS app files are deployed under the `sns/` prefix.

---

## Troubleshooting

### CORS error / app calls wrong cloud's API

Symptom: Browser console shows `No 'Access-Control-Allow-Origin' header` or requests go to a different cloud's API endpoint.

**Cause**: The API URL is embedded at build time. If `VITE_API_URL` was not set during `npm run build`, the fallback value in `src/api/client.ts` is used for all clouds.

**Fix**: Rebuild for the specific cloud with the correct `VITE_API_URL` (see build step 1 table), then re-upload:

```bash
# Example: fix AWS staging
cd services/frontend_react
VITE_API_URL=https://z42qmqdqac.execute-api.ap-northeast-1.amazonaws.com npm run build
aws s3 sync dist/ s3://multicloud-auto-deploy-staging-frontend/sns/ \
  --delete --cache-control "max-age=3600" --exclude "*.map"
aws cloudfront create-invalidation --distribution-id E1QOH6Q2H25MY8 --paths "/sns/*"
```

To verify the correct API URL is bundled:

```bash
# Check what API URL is embedded in the deployed JS bundle
curl -s https://<cloudfront-domain>/sns/ | grep -o '"[^"]*\.js"'
# Then fetch the JS and grep for the API domain
curl -s https://<cloudfront-domain>/sns/assets/<bundle>.js | grep -o 'execute-api[^"]*\|run\.app[^"]*\|azurewebsites[^"]*'
```

### React app shows blank page at `/sns/`

The app was likely built without the correct base path. Verify:

```bash
# Check that dist/index.html references /sns/ assets, not /
head -5 services/frontend_react/dist/index.html
# Should contain: src="/sns/assets/..."
```

If not, rebuild:

```bash
cd services/frontend_react && npm run build
```

### GCP: `/sns/` returns landing page content

Verify that the frontend build was deployed to the `sns/` prefix of the frontend bucket:

```bash
gcloud storage ls gs://ashnova-multicloud-auto-deploy-staging-frontend/sns/
# Should list index.html and assets/
```

If not, rebuild:

```bash
cd services/frontend_react && npm run build
# Re-run deploy workflow or copy dist/ to gs://.../sns/
```

### GCP: `/sns/unknown-path` returns 404 (SPA deep-link behaviour)

**This is expected behaviour with the Classic External LB** (`load_balancing_scheme = "EXTERNAL"`).

GCS serves the `not_found_page` (`index.html`) with an HTTP 404 status. Cloud CDN
forwards the 404 without modifying the status code because `defaultCustomErrorResponsePolicy`
(which would override 4xx → 200) is only supported on `EXTERNAL_MANAGED` load balancers.

**Behaviour summary**:
| Client | Result |
|--------|--------|
| Browser (React Router) | Renders SPA correctly — `index.html` is returned |
| `curl` / HTTP clients | Sees HTTP 404, body is SPA HTML |
| SEO crawlers | May flag deep links as 404 (not ideal for production) |

**Staging test**: `test-staging-sns.sh` accepts both HTTP 200 and `404 + <html>` as a
passing SPA fallback result.

**To fix properly** (future improvement):
1. Change `load_balancing_scheme` in Pulumi forwarding rules to `"EXTERNAL_MANAGED"`
2. Re-add to the URL Map:
   ```python
   default_custom_error_response_policy=gcp.compute.URLMapDefaultCustomErrorResponsePolicyArgs(
       error_service=backend_bucket.self_link,
       error_response_rules=[gcp.compute.URLMapDefaultCustomErrorResponsePolicyErrorResponseRuleArgs(
           match_response_codes=["4xx"],
           path="/sns/index.html",
           override_response_code=200,
       )],
   )
   ```
3. Run `pulumi up` and verify with `curl -o /dev/null -s -w "%{http_code}" http://<ip>/sns/unknown-path`

### Azure: `/sns/` route not working

Front Door route conflicts can occur when both routes target the same endpoint. Check:

```bash
az afd route list \
  --resource-group <rg> \
  --profile-name <project>-<stack>-fd \
  --endpoint-name <endpoint>
# Should show two routes: one for /sns/* and one for /*
```

### AWS: Deep links under `/sns/` return 403

The CloudFront distribution includes a custom error response mapping `403 → /sns/index.html` (HTTP 200) for SPA client-side routing. If this is not working, verify the `custom_error_responses` block in the Pulumi output:

```bash
cd infrastructure/pulumi/aws
pulumi stack output | grep cloudfront
aws cloudfront get-distribution --id <ID> \
  --query 'Distribution.DistributionConfig.CustomErrorResponses'
```
