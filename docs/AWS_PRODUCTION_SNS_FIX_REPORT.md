# AWS Production Simple-SNS: Fix Report (2026-02-21)

> **Status**: ✅ All issues resolved — simple-sns is fully operational on AWS production
> **Commits**: `fd1f422` `8188682` (main branch)
> **Environment**: `https://www.aws.ashnova.jp/sns/`

---

## Executive Summary

Opening the AWS Production SNS app returned the following error:

```
HTTPConnectionPool(host='localhost', port=8000): Max retries exceeded with url:
/posts?limit=20 (Caused by NewConnectionError("HTTPConnection(host='localhost',
port=8000): Failed to establish a new connection: [Errno 111] Connection refused"))
```

This report documents two independent bugs that caused the Production `frontend-web`
Lambda to fall back to `http://localhost:8000` instead of the real API Gateway URL.
Both root causes have been identified, fixed, and deployed.

| #   | Symptom                                                          | Root Cause                                                                                      | Commit    | Status   |
| --- | ---------------------------------------------------------------- | ----------------------------------------------------------------------------------------------- | --------- | -------- |
| 1   | All API calls hit `http://localhost:8000` → `Connection refused` | Production `frontend-web` Lambda had `API_BASE_URL=""` — CI/CD relied on an unset GitHub Secret | `fd1f422` | ✅ Fixed |
| 2   | `COGNITO_REDIRECT_URI` used CloudFront domain, not custom domain | CI/CD set redirect URI to `cloudfront_domain` while Cognito App Client only allows `ashnova.jp` | `fd1f422` | ✅ Fixed |

---

## Bug 1 — `API_BASE_URL` Was Empty in Production, Causing localhost Fallback

### Symptom

Every page load in the Production SNS app (`https://www.aws.ashnova.jp/sns/`) failed
with a Python `NewConnectionError` to `localhost:8000`.

### Root Cause

[`services/frontend_web/app/config.py`](../services/frontend_web/app/config.py) defines
the fallback for `api_base_url` as:

```python
api_base_url: str = "http://localhost:8000"
```

When `API_BASE_URL` is empty (`""`), Pydantic treats it as a falsy string and the
app internally falls back to `http://localhost:8000`.

The production `frontend-web` Lambda (`multicloud-auto-deploy-production-frontend-web`)
had the following environment variables at the time of the incident:

```json
{
  "API_BASE_URL": "",
  "STAGE_NAME": "sns",
  "COGNITO_DOMAIN": "",
  "AUTH_DISABLED": "false",
  "COGNITO_REDIRECT_URI": "",
  "AUTH_PROVIDER": "aws",
  "COGNITO_CLIENT_ID": ""
}
```

All the critical runtime values were empty.

### Why Were They Empty?

`.github/workflows/deploy-frontend-web-aws.yml` was setting the Lambda environment by
reading values from **GitHub Secrets**:

```yaml
- name: Deploy to Lambda
  run: |
    API_URL="${{ secrets.API_GATEWAY_ENDPOINT }}"
    ...
    "API_BASE_URL": "${API_URL}",         # ← empty string when secret is unset
    "COGNITO_DOMAIN": "${{ secrets.COGNITO_DOMAIN }}",
    "COGNITO_CLIENT_ID": "${{ secrets.COGNITO_CLIENT_ID }}",
```

The secrets `API_GATEWAY_ENDPOINT`, `COGNITO_DOMAIN`, `COGNITO_CLIENT_ID`, and
`FRONTEND_WEB_REDIRECT_URI` were **never configured** in the `production`
GitHub Actions environment. When a secret is absent, GitHub Actions substitutes an
empty string — silently overwriting the Lambda's previously working values.

This is the same class of bug as **Bug 1** in [AWS_SNS_FIX_REPORT.md](AWS_SNS_FIX_REPORT.md)
(staging), but affecting the Production environment separately.

### Fix

**Immediate**: Manually updated the Lambda's environment variables via AWS CLI with the
correct values from the Production Pulumi stack:

```bash
aws lambda update-function-configuration \
  --function-name multicloud-auto-deploy-production-frontend-web \
  --region ap-northeast-1 \
  --environment '{
    "Variables": {
      "ENVIRONMENT": "production",
      "AUTH_PROVIDER": "aws",
      "AUTH_DISABLED": "false",
      "STAGE_NAME": "sns",
      "API_BASE_URL": "https://qkzypr32af.execute-api.ap-northeast-1.amazonaws.com",
      "COGNITO_CLIENT_ID": "4h3b285v1a9746sqhukk5k3a7i",
      "COGNITO_DOMAIN": "multicloud-auto-deploy-production.auth.ap-northeast-1.amazoncognito.com",
      "COGNITO_REDIRECT_URI": "https://www.aws.ashnova.jp/sns/auth/callback",
      "COGNITO_LOGOUT_URI": "https://www.aws.ashnova.jp/sns/"
    }
  }'
```

**Permanent** (commit `fd1f422`): Rewrote `deploy-frontend-web-aws.yml` to obtain all
values from **Pulumi stack outputs** instead of GitHub Secrets. Pulumi is the
authoritative source and always has the correct values for every environment.

```yaml
# BEFORE (❌ relies on manually-managed secrets that may be absent)
API_URL="${{ secrets.API_GATEWAY_ENDPOINT }}"

# AFTER (✅ reads from the Pulumi stack for the matching environment)
- name: Get Pulumi Outputs
  id: pulumi_outputs
  run: |
    pulumi stack select "${{ steps.env.outputs.env_name }}"
    echo "api_gateway_endpoint=$(pulumi stack output api_gateway_endpoint)" >> $GITHUB_OUTPUT
    echo "cloudfront_domain=$(pulumi stack output cloudfront_domain)"       >> $GITHUB_OUTPUT
    echo "custom_domain=$(pulumi stack output custom_domain 2>/dev/null || echo '')" >> $GITHUB_OUTPUT
    echo "cognito_client_id=$(pulumi stack output cognito_client_id)"       >> $GITHUB_OUTPUT
    echo "cognito_domain=$(pulumi stack output cognito_domain)"             >> $GITHUB_OUTPUT
  env:
    PULUMI_ACCESS_TOKEN: ${{ secrets.PULUMI_ACCESS_TOKEN }}
```

A **guard clause** was also added to abort the deployment if any critical output is
empty, preventing silent overwrites:

```bash
if [[ -z "$API_URL" || -z "$CF_DOMAIN" || -z "$CLIENT_ID" ]]; then
  echo "❌ Critical Pulumi outputs are empty. Aborting."
  exit 1
fi
```

Additionally, `aws lambda wait function-updated` steps were added before both
`update-function-code` and `update-function-configuration` to prevent
`ResourceConflictException` (the same race condition documented in staging Bug 1).

---

## Bug 2 — `COGNITO_REDIRECT_URI` Used CloudFront Domain Instead of Custom Domain

### Symptom

Even with APIs returning correctly, a login attempt would fail at the Cognito
redirect phase because the callback URL was not registered in the Cognito App Client.

### Root Cause

The original CI/CD step (in both `deploy-aws.yml` and `deploy-frontend-web-aws.yml`)
constructed the Cognito redirect URIs using `cloudfront_domain`:

```bash
COGNITO_REDIRECT_URI="https://${CLOUDFRONT_DOMAIN}/sns/auth/callback"
```

The Production Cognito App Client (`4h3b285v1a9746sqhukk5k3a7i`) only has the custom
domain registered as an allowed callback URL:

```json
"CallbackURLs": [
  "http://localhost:8080/callback",
  "https://localhost:8080/callback",
  "https://www.aws.ashnova.jp/sns/auth/callback"
]
```

The CloudFront domain `d1qob7569mn5nw.cloudfront.net` was **not** in the allowed list,
so any redirect from Cognito would be rejected.

### Fix

Both workflows now derive `SITE_DOMAIN` from the `custom_domain` Pulumi output,
falling back to `cloudfront_domain` when no custom domain is configured (e.g., staging):

```bash
CUSTOM_DOMAIN="${{ steps.pulumi_outputs.outputs.custom_domain }}"
SITE_DOMAIN="${CUSTOM_DOMAIN:-$CF_DOMAIN}"
# → "www.aws.ashnova.jp" in production, "d1tf3uumcm4bo1.cloudfront.net" in staging

"COGNITO_REDIRECT_URI": "https://${SITE_DOMAIN}/sns/auth/callback",
"COGNITO_LOGOUT_URI":   "https://${SITE_DOMAIN}/sns/"
```

`deploy-aws.yml` was also updated to include the custom domain in `CORS_ORIGINS`:

```bash
if [[ -n "$CUSTOM_DOMAIN" ]]; then
  CORS_ORIGINS="https://${CLOUDFRONT_DOMAIN},https://${CUSTOM_DOMAIN},http://localhost:5173"
else
  CORS_ORIGINS="https://${CLOUDFRONT_DOMAIN},http://localhost:5173"
fi
```

---

## Production Environment Reference

| Resource                   | Value                                                         |
| -------------------------- | ------------------------------------------------------------- |
| CloudFront Distribution    | `E214XONKTXJEJD` — `d1qob7569mn5nw.cloudfront.net`            |
| Custom Domain (Production) | `www.aws.ashnova.jp`                                          |
| API Gateway (Production)   | `https://qkzypr32af.execute-api.ap-northeast-1.amazonaws.com` |
| Lambda (API)               | `multicloud-auto-deploy-production-api`                       |
| Lambda (frontend-web)      | `multicloud-auto-deploy-production-frontend-web`              |
| Cognito User Pool          | `ap-northeast-1_50La963P2`                                    |
| Cognito App Client         | `4h3b285v1a9746sqhukk5k3a7i`                                  |
| DynamoDB Table             | `multicloud-auto-deploy-production-posts`                     |
| Pulumi Stack               | `production` (org: `ashnova`)                                 |

---

## Files Changed

| File                                            | Change                                                                         |
| ----------------------------------------------- | ------------------------------------------------------------------------------ |
| `.github/workflows/deploy-frontend-web-aws.yml` | Replaced Secret-based env vars with Pulumi outputs; added wait steps and guard |
| `.github/workflows/deploy-aws.yml`              | Added `custom_domain` output; use `SITE_DOMAIN` for Cognito URIs and CORS      |

---

## Lessons Learned

1. **Never use GitHub Secrets as the source of truth for infrastructure values.**  
   Secrets must be manually kept in sync with the actual infrastructure state, which
   is error-prone. Pulumi state is always up-to-date and should be used directly.

2. **Production and staging may have different resources.**  
   This project has separate Pulumi stacks (`staging`, `production`) with different
   API Gateway IDs, Cognito User Pools, and custom domains. A workflow that only
   works for staging (using a staging-preconfigured secret) will silently fail for
   production.

3. **Custom domains must be the authoritative source for Cognito callback URLs.**  
   Always derive `COGNITO_REDIRECT_URI` from the domain that is registered in the
   Cognito App Client — not from the CDN's auto-generated domain.

4. **Empty strings are a silent failure mode in Pydantic settings.**  
   `api_base_url: str = "http://localhost:8000"` is only used as a default when the
   environment variable is **absent**. An empty string `""` set by CI still overwrites
   the default and becomes the effective value, causing the app to call `""` which
   Pydantic's `clean_api_base_url()` strips to `""`, falling through to `localhost`.
   Add a validation guard in CI to catch this early.
