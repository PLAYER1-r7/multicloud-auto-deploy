# Staging Test Guide

> **Last updated**: 2026-02-23  
> **Applies to**: staging environments on AWS, Azure, GCP

---

## Overview

This guide describes how to test the **landing page** and **SNS application** across all
three cloud staging environments. The test suite covers:

| Layer        | What is tested                                               |
| ------------ | ------------------------------------------------------------ |
| Landing page | CDN delivery, HTML content, HTTPS, cache headers             |
| SNS frontend | React SPA served from CDN (`/sns/`), env-var injection       |
| SNS API      | Public endpoints (health, list posts), auth guard, full CRUD |
| Image upload | Presigned URL generation (S3 / Blob Storage / GCS)           |

---

## Staging Endpoints (2026-02-23)

| Cloud     | CDN URL                                                        | API URL                                                                                       |
| --------- | -------------------------------------------------------------- | --------------------------------------------------------------------------------------------- |
| **AWS**   | `https://d1tf3uumcm4bo1.cloudfront.net`                        | `https://z42qmqdqac.execute-api.ap-northeast-1.amazonaws.com`                                 |
| **Azure** | `https://mcad-staging-d45ihd-dseygrc9c3a3htgj.z01.azurefd.net` | `https://multicloud-auto-deploy-staging-func-d8a2guhfere0etcq.japaneast-01.azurewebsites.net` |
| **GCP**   | `https://www.gcp.ashnova.jp`                                   | `https://multicloud-auto-deploy-staging-api-son5b3ml7a-an.a.run.app`                          |

> **Note**: The Azure API URL (`AZURE_API_URL`) is the Function App base URL **without** the
> `/api/HttpTrigger` path. The function uses a wildcard route `{*route}` so all API paths
> (e.g. `/health`, `/posts`) are served directly at the base URL.

---

## Test Scripts

| Script                          | Purpose                                       |
| ------------------------------- | --------------------------------------------- |
| `scripts/test-staging-all.sh`   | **⭐ Recommended**: orchestrates all 3 clouds |
| `scripts/test-landing-pages.sh` | Landing page (`/`) tests only                 |
| `scripts/test-e2e.sh`           | Lightweight multi-cloud smoke test (v2)       |
| `scripts/test-sns-aws.sh`       | Full AWS-only test suite (authenticated)      |
| `scripts/test-sns-azure.sh`     | Full Azure-only test suite (authenticated)    |
| `scripts/test-sns-gcp.sh`       | Full GCP-only test suite (authenticated)      |

---

## Quick Start (No Authentication Required)

These checks verify connectivity and public endpoints without any login.

### Option A: Quick connectivity check (fastest — ~30s)

```bash
./scripts/test-staging-all.sh --quick
```

This checks:

- CDN landing page (`/`) returns HTTP 200
- SNS app (`/sns/`) returns HTTP 200
- API `/health` returns HTTP 200 with `{"status": "ok"}`

### Option B: Landing page deep test

```bash
./scripts/test-landing-pages.sh
```

Tests per cloud (11 checks each):

- HTTP 200 + response time < 8s
- Content-Type: text/html
- Brand name "Ashnova" present
- Cloud badge (AWS / Azure / GCP) present
- SNS link present
- No `localhost` leak in rendered HTML
- HTTPS transport (where applicable)
- Cache-Control header
- Page size sanity (200B – 2MB)
- No server error markers
- `/sns/` path reachable

### Option C: Lightweight E2E smoke test

```bash
./scripts/test-e2e.sh
```

Public tests per cloud:

- `GET /health` → 200, `.status == "ok"`
- `GET /posts` → 200, `.items` array present
- `POST /posts` without token → 401 (auth guard)

---

## Full Authenticated Tests

Authenticated tests require tokens from each cloud's identity provider.

### Step 1: Obtain tokens

#### AWS — Cognito access token

```bash
# Method A: AWS CLI (requires email/password)
AWS_TOKEN=$(aws cognito-idp initiate-auth \
  --auth-flow USER_PASSWORD_AUTH \
  --client-id 1k41lqkds4oah55ns8iod30dv2 \
  --auth-parameters USERNAME=YOUR_EMAIL,PASSWORD=YOUR_PASSWORD \
  --region ap-northeast-1 \
  --query 'AuthenticationResult.AccessToken' \
  --output text)

# Method B: Browser
# 1. Open https://d1tf3uumcm4bo1.cloudfront.net/sns/
# 2. Log in with your Cognito account
# 3. DevTools → Application → Local Storage → origin → access_token
```

#### GCP — Firebase ID token

```bash
# Method A: gcloud CLI (uses your logged-in Google account)
GCP_TOKEN=$(gcloud auth print-identity-token)

# Method B: Browser
# 1. Open https://www.gcp.ashnova.jp/sns/
# 2. Log in with Google account
# 3. DevTools → Application → Local Storage → origin → id_token
```

#### Azure — Azure AD ID token

```bash
# Method: Browser only
# 1. Open https://mcad-staging-d45ihd-dseygrc9c3a3htgj.z01.azurefd.net/sns/
# 2. Log in with your Microsoft account
# 3. DevTools → Application → Local Storage → origin → id_token
# 4. Copy the value
AZURE_TOKEN="<paste id_token here>"
```

### Step 2: Run tests

#### All 3 clouds (recommended)

```bash
./scripts/test-staging-all.sh \
  --aws-token   "$AWS_TOKEN" \
  --azure-token "$AZURE_TOKEN" \
  --gcp-token   "$GCP_TOKEN"
```

#### Single cloud

```bash
# AWS only
./scripts/test-sns-aws.sh --token "$AWS_TOKEN"

# Azure only
./scripts/test-sns-azure.sh --token "$AZURE_TOKEN"

# GCP only
./scripts/test-sns-gcp.sh --token "$GCP_TOKEN"
```

#### Verbose output (print response bodies)

```bash
./scripts/test-staging-all.sh \
  --aws-token "$AWS_TOKEN" \
  --gcp-token "$GCP_TOKEN" \
  --verbose
```

#### Keep test posts (skip cleanup)

```bash
./scripts/test-staging-all.sh \
  --aws-token "$AWS_TOKEN" \
  --skip-cleanup
```

---

## What Each Test Script Checks

### `test-sns-aws.sh` (8 sections)

| Section | Tests                                                             |
| ------- | ----------------------------------------------------------------- |
| 1       | CloudFront returns `/`, `/sns/` with HTML (Content-Type check)    |
| 2       | API `/health` → 200, `.status == "ok"`                            |
| 3       | Auth guard: POST without token → 401                              |
| 4       | Authenticated: GET profile, POST/GET/PUT post                     |
| 5       | Presigned URLs: count=2 returned, URL starts with `https://...s3` |
| 6       | Image key validation: 16 keys → 201; 17 keys → 422                |
| 7       | Cleanup: DELETE all created posts                                 |
| 8       | React SPA env-var sanity: no `localhost` in bundle                |

### `test-sns-azure.sh` (6 sections)

| Section | Tests                                                                          |
| ------- | ------------------------------------------------------------------------------ |
| 1       | Front Door returns `/sns/` with React SPA HTML                                 |
| 2       | Function App `/health` → 200, `/posts` → 200 with `.items`                     |
| 3       | AFD SPA deep-link URL Rewrite: `/sns/login`, `/sns/profile`, `/sns/feed` → 200 |
| 4       | Auth guard: POST without token → 401                                           |
| 5       | Authenticated: GET/POST/PUT/DELETE posts, presigned URL                        |
| 6       | Cleanup                                                                        |

### `test-sns-gcp.sh` (7 sections)

| Section | Tests                                                                         |
| ------- | ----------------------------------------------------------------------------- |
| 1       | Cloud CDN returns `/sns/` with React SPA HTML (no SSR artifacts)              |
| 2       | Cloud Run `/health` → 200, `/posts` → 200 with `.items`                       |
| 3       | Auth guard: POST/presigned-urls/profile without token → 401                   |
| 4       | Authenticated: GET profile, POST/GET/PUT post                                 |
| 5       | GCS presigned URLs: count=2, URL starts with `https://storage.googleapis.com` |
| 6       | Image key validation: 16 → 201; 17 → 422                                      |
| 7       | Cleanup                                                                       |

### `test-landing-pages.sh` (11 checks per cloud)

See [Quick Start](#option-b-landing-page-deep-test) section above.

### `test-e2e.sh` (v2)

Lightweight smoke test with a consolidated table output. Covers 8 test points per cloud.

---

## Environment Variable Overrides

All scripts support URL overrides via environment variables:

| Variable        | Default                                                                                       | Used by                              |
| --------------- | --------------------------------------------------------------------------------------------- | ------------------------------------ |
| `AWS_CF_URL`    | `https://d1tf3uumcm4bo1.cloudfront.net`                                                       | test-staging-all, test-landing-pages |
| `AWS_API_URL`   | `https://z42qmqdqac.execute-api.ap-northeast-1.amazonaws.com`                                 | test-staging-all, test-e2e           |
| `AZURE_FD_URL`  | `https://mcad-staging-d45ihd-dseygrc9c3a3htgj.z01.azurefd.net`                                | test-staging-all, test-landing-pages |
| `AZURE_API_URL` | `https://multicloud-auto-deploy-staging-func-d8a2guhfere0etcq.japaneast-01.azurewebsites.net` | test-staging-all, test-e2e           |
| `GCP_CDN_URL`   | `https://www.gcp.ashnova.jp`                                                                  | test-staging-all, test-landing-pages |
| `GCP_API_URL`   | `https://multicloud-auto-deploy-staging-api-son5b3ml7a-an.a.run.app`                          | test-staging-all, test-e2e           |

Example — test production URLs instead of staging:

```bash
AWS_CF_URL=https://www.aws.ashnova.jp \
AWS_API_URL=https://qkzypr32af.execute-api.ap-northeast-1.amazonaws.com \
GCP_CDN_URL=https://www.gcp.ashnova.jp \
GCP_API_URL=https://multicloud-auto-deploy-production-api-son5b3ml7a-an.a.run.app \
./scripts/test-landing-pages.sh
```

---

## Troubleshooting

### `GET /health` fails (HTTP 000 / timeout)

1. Check if the Cloud Run / Lambda / Function App is stopped:

   ```bash
   # GCP
   gcloud run services describe multicloud-auto-deploy-staging-api \
     --region asia-northeast1 --project ashnova \
     --format="value(status.conditions[0].status)"

   # AWS
   aws lambda get-function-configuration \
     --function-name multicloud-auto-deploy-staging-api \
     --region ap-northeast-1 --query State

   # Azure
   az functionapp show \
     --name multicloud-auto-deploy-staging-func \
     --resource-group multicloud-auto-deploy-staging-rg \
     --query state
   ```

2. See [AI_AGENT_08_RUNBOOKS.md](AI_AGENT_08_RUNBOOKS.md) for redeploy procedures.

### `POST /posts` returns 401 even with a valid token

- **AWS**: Token may have expired (1h). Re-run the `aws cognito-idp initiate-auth` command.
- **GCP**: Firebase ID tokens expire in 1 hour. Re-run `gcloud auth print-identity-token`.
- **Azure**: Azure AD tokens expire in 1h. Re-extract from browser DevTools.
- Check that `AUTH_DISABLED=false` is set on the deployment (do **not** set to `true` in staging).

### `POST /uploads/presigned-urls` returns 500

- **GCP**: The `GCP_SERVICE_ACCOUNT` environment variable must be set on Cloud Run.
  See [GCP_SNS_FIX_REPORT_20260223.md](GCP_SNS_FIX_REPORT_20260223.md) (issue G5).
- **AWS**: Verify that the Lambda execution role has `s3:PutObject` on the images bucket.
- **Azure**: Verify that the Function App has the `AZURE_STORAGE_CONNECTION_STRING` env var set.

### `/sns/` returns non-HTML or SSR artifacts

- The React SPA may not have been built/deployed to the storage bucket.
- Verify that the CI/CD pipeline ran after the last `develop` push:
  ```bash
  gh run list --workflow deploy-aws.yml --limit 3
  gh run list --workflow deploy-gcp.yml --limit 3
  gh run list --workflow deploy-azure.yml --limit 3
  ```
- See [AI_AGENT_06_CICD.md](AI_AGENT_06_CICD.md) for deployment details.

### Chrome で「保護されていない通信」警告が表示される

**症状**: `https://staging.aws.ashnova.jp/` にアクセスすると Chrome のアドレスバーに「保護されていない通信」と表示される。

**調査チェックリスト** (サーバーサイドが正常かどうか確認する):

```bash
# 1. CSP ヘッダーが配信されているか確認
curl -sI https://staging.aws.ashnova.jp/ | grep -i content-security
# 期待値: content-security-policy: upgrade-insecure-requests

# 2. HSTS が設定されているか確認
curl -sI https://staging.aws.ashnova.jp/ | grep -i strict-transport
# 期待値: strict-transport-security: max-age=31536000; includeSubDomains

# 3. HTTP→HTTPS リダイレクトが機能しているか確認
curl -sI http://staging.aws.ashnova.jp/ | grep -iE "http/|location"
# 期待値: HTTP/1.1 301  +  Location: https://staging.aws.ashnova.jp/

# 4. S3 HTTP 直接アクセスが遮断されているか確認 (403 が正常)
curl -sI http://multicloud-auto-deploy-staging-frontend.s3-website-ap-northeast-1.amazonaws.com/
# 期待値: HTTP/1.1 403 Forbidden
```

**原因の切り分け**:

| DevTools > Security タブの表示 | 原因 | 対処 |
| ------------------------------- | ---- | ---- |
| `chrome-exte...` が Secure origins に表示されている | Chrome 拡張機能が証明書エラーのあるリソースを注入している | 拡張機能を1つずつオフにして特定 |
| "You have recently allowed content with certificate errors" | 過去にブラウザがこのサイトで証明書エラーを「許可」した記録が残っている | 下記の「ブラウザキャッシュクリア手順」参照 |
| Mixed Content の `http://` URLが表示される | サーバーサイドに http:// リソースが残っている | JS バンドル・API レスポンス・DBを調査 |

**ブラウザキャッシュのクリア手順** ("recently allowed certificate errors" の場合):

1. `chrome://settings/content/siteDetails?site=https%3A%2F%2Fstaging.aws.ashnova.jp` を開く
2. 「権限をリセット」と「データを消去」を実行
3. **ブラウザを完全に再起動** (タブを閉じるだけでは不十分 — メモリキャッシュが残る)
4. `https://staging.aws.ashnova.jp/` に再アクセス

> **重要**: サイトデータを消去しただけでは解消しない場合がある。Chrome はこの許可状態をメモリにキャッシュするため、ブラウザ再起動が必要。

**シークレットモードで警告が消える場合**: サーバーサイドは正常。ブラウザの状態 (拡張機能またはキャッシュ) が原因。

### GCP CDN returns the old React SPA after a redeploy

GCS objects are served via Cloud CDN with cache TTL. Force invalidation:

```bash
gcloud compute url-maps invalidate-cdn-cache multicloud-auto-deploy-staging-lb \
  --path "/*" --project=ashnova --async
```

See [GCP_SNS_FIX_REPORT_20260223.md](GCP_SNS_FIX_REPORT_20260223.md) (issue G3).

### Azure `/sns/deep-link` returns 404

The Front Door Rule Set rewrites `/sns/*` → `/sns/index.html`. If this fails:

1. Open Azure Portal → Front Door → Rule Sets → check the rewrite rule.
2. Verify the Rule Set is associated with the route.

---

## CI/CD Integration

The test scripts can be wired into GitHub Actions as a post-deploy verification step:

```yaml
- name: Run staging smoke tests (public)
  run: |
    ./scripts/test-staging-all.sh --quick

- name: Run full staging tests (authenticated)
  if: secrets.AWS_TEST_TOKEN != ''
  env:
    AWS_TOKEN: ${{ secrets.AWS_TEST_TOKEN }}
    AZURE_TOKEN: ${{ secrets.AZURE_TEST_TOKEN }}
    GCP_TOKEN: ${{ secrets.GCP_TEST_TOKEN }}
  run: |
    ./scripts/test-staging-all.sh \
      --aws-token   "$AWS_TOKEN" \
      --azure-token "$AZURE_TOKEN" \
      --gcp-token   "$GCP_TOKEN"
```

---

## Related Documents

| Document                                                         | Description                                   |
| ---------------------------------------------------------------- | --------------------------------------------- |
| [AI_AGENT_07_STATUS.md](AI_AGENT_07_STATUS.md)                   | Current health of all 3 environments          |
| [AI_AGENT_04_API.md](AI_AGENT_04_API.md)                         | API endpoint spec and request/response schema |
| [AI_AGENT_08_RUNBOOKS.md](AI_AGENT_08_RUNBOOKS.md)               | Step-by-step deploy / redeploy procedures     |
| [GCP_SNS_FIX_REPORT_20260223.md](GCP_SNS_FIX_REPORT_20260223.md) | GCP bug fixes (G1–G6)                         |
| [AWS_SNS_FIX_REPORT_20260222.md](AWS_SNS_FIX_REPORT_20260222.md) | AWS fixes (12 bugs)                           |
| [AZURE_SNS_FIX_REPORT.md](AZURE_SNS_FIX_REPORT.md)               | Azure fixes                                   |
