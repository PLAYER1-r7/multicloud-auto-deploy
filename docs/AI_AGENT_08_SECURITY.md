# 08 — Security

> Part III — Operations | Parent: [AI_AGENT_GUIDE.md](AI_AGENT_GUIDE.md)

---

## Current Security Configuration Status

| Feature                   | AWS                    | Azure        | GCP               | Notes                                                         |
| ------------------------- | ---------------------- | ------------ | ----------------- | ------------------------------------------------------------- |
| HTTPS enforced            | ✅                     | ✅           | ❌                | GCP: HTTP only (needs fixing)                                 |
| WAF                       | ✅ WebACL (CloudFront) | ❌           | ✅ Cloud Armor    | Azure: not configured                                         |
| Rate limiting             | ❌                     | ❌           | ✅ 100req/min/IP  |                                                               |
| SQLi / XSS protection     | ❌                     | ❌           | ✅                |                                                               |
| Data encryption (at rest) | ✅ SSE-S3              | ✅ Azure SSE | ✅ Google-managed |                                                               |
| Versioning                | ✅                     | ✅           | ✅                |                                                               |
| Access logs               | ✅                     | ❌           | ✅                |                                                               |
| Security headers          | ✅ CloudFront RHP      | ❌           | ❌                | HSTS/CSP(upgrade-insecure-requests)/X-Frame/X-Content/Referrer/XSS (2026-02-23) |
| Soft delete / retention   | ❌                     | ✅ 7 days    | ❌                |                                                               |
| CORS config               | ✅                     | ✅           | ✅                | `allowedOrigins` は現在 `*` (要絞り込み)                      |

---

## Authentication Configuration

### AWS — Amazon Cognito

```
Auto-created by Pulumi:
  - Cognito User Pool
  - User Pool Client (allowed_oauth_flows=["code"] のみ — implicit 廃止)
  - User Pool Domain

Lambda environment variables:
  AUTH_PROVIDER=cognito
  COGNITO_USER_POOL_ID=<Pulumi output>
  COGNITO_CLIENT_ID=<Pulumi output>
  AWS_REGION=ap-northeast-1
```

**OAuth フロー: PKCE (Proof Key for Code Exchange)** — 2026-02-23 実装

| 項目 | 内容 |
| ---- | ---- |
| フロー | Authorization Code + PKCE (S256) |
| `response_type` | `code` (implicit `token` は廃止) |
| code_verifier | 256-bit ランダム、sessionStorage に保存 |
| code_challenge | SHA-256(verifier) → Base64URL |
| トークン交換 | ブラウザから `POST /oauth2/token` (code_verifier 付き) |
| 利点 | URLフラグメントへのトークン漏洩が完全に排除される |

> **注意**: `implicit` フローは Cognito UserPoolClient の `allowed_oauth_flows` から削除済み。
> 古い implicit フロー URL (`response_type=token`) でアクセスすると Cognito がエラーを返す。

### Azure — Azure AD

```
Auto-created by Pulumi:
  - Azure AD Application (pulumi-azuread)
  - Service Principal
  - OAuth2 Permission Scope (API.Access)
  - Redirect URIs

Functions environment variables:
  AUTH_PROVIDER=azure
  AZURE_TENANT_ID=<Pulumi output "azure_ad_tenant_id">
  AZURE_CLIENT_ID=<Pulumi output "azure_ad_client_id">
```

### GCP — Firebase Auth

```
Auto-created by Pulumi:
  - Firebase Auth project configuration
  - Firebase Auth Google Sign-In provider enabled

Cloud Run (API) environment variables:
  AUTH_PROVIDER=firebase
  GCP_PROJECT_ID=ashnova
  GCP_SERVICE_ACCOUNT=899621454670-compute@developer.gserviceaccount.com
  (uses impersonated_credentials to generate GCS presigned URLs via IAM signBlob API)

Cloud Run (frontend-web) environment variables:
  AUTH_PROVIDER=firebase
  AUTH_DISABLED=false
  FIREBASE_API_KEY=<GitHub Secret: FIREBASE_API_KEY>
  FIREBASE_AUTH_DOMAIN=<GitHub Secret: FIREBASE_AUTH_DOMAIN>
  FIREBASE_PROJECT_ID=ashnova
  FIREBASE_APP_ID=<GitHub Secret: FIREBASE_APP_ID>

Firebase authorized domain:
  multicloud-auto-deploy-staging-frontend-web-son5b3ml7a-an.a.run.app

Token refresh:
  `onIdTokenChanged` in home.html auto-refreshes the token (and re-issues the session cookie)
```

---

## IAM Least-Privilege Policies

### AWS Lambda execution role

```json
{
  "Version": "2012-10-17",
  "Statement": [
    { "Effect": "Allow", "Action": ["logs:*"], "Resource": "arn:aws:logs:*" },
    {
      "Effect": "Allow",
      "Action": [
        "dynamodb:GetItem",
        "dynamodb:PutItem",
        "dynamodb:UpdateItem",
        "dynamodb:DeleteItem",
        "dynamodb:Scan",
        "dynamodb:Query"
      ],
      "Resource": "arn:aws:dynamodb:*:*:table/simple-sns-messages*"
    },
    {
      "Effect": "Allow",
      "Action": ["s3:GetObject", "s3:PutObject", "s3:DeleteObject"],
      "Resource": "arn:aws:s3:::*uploads*"
    },
    {
      "Effect": "Allow",
      "Action": ["secretsmanager:GetSecretValue"],
      "Resource": "*"
    }
  ]
}
```

### Azure Service Principal (pulumi-deploy)

- Role: `Contributor` (subscription scope)
- Storage Blob Data Contributor: `mcadweb*` Storage Account

### GCP — Service account (github-actions-deploy)

- Role: `roles/editor`
- Additional: `roles/storage.objectAdmin` (uploads bucket, for presigned URL signing)
- Additional: `roles/iam.serviceAccountTokenCreator` (to impersonate Compute Engine SA for `signBlob` API)

> **Note**: GCS uploads bucket (`ashnova-multicloud-auto-deploy-staging-uploads`) is intentionally public (`allUsers:objectViewer`) to allow direct image display in browsers. Do NOT apply this to the frontend bucket.

---

## Secret Management

| Cloud | Service         | Primary use                      |
| ----- | --------------- | -------------------------------- |
| AWS   | Secrets Manager | DB credentials, API keys         |
| Azure | Key Vault       | Connection strings, certificates |
| GCP   | Secret Manager  | Service account keys             |
| CI/CD | GitHub Secrets  | Cloud provider credentials       |

---

## Unresolved Security Issues (by priority)

1. **GCP HTTPS** (high priority)  
   Requires adding `TargetHttpsProxy` + Google Managed SSL Certificate.  
   ※ カスタムドメイン (`www.gcp.ashnova.jp`) は HTTPS 済み (production のみ)

2. **Azure WAF** (high priority)  
   Upgrade Front Door to Premium SKU, or configure WAF Policy compatible with Standard SKU.

3. **Tighten CORS** (medium priority)  
   Restrict `allowedOrigins` to actual domain names (currently `"*"`).  
   Pulumi config: `pulumi config set allowedOrigins "https://aws.example.com"`

4. **GCP SSL certificate placeholder** (medium priority)  
   The GCP Pulumi stack still has `example.com` as a placeholder. Replace with the real domain.

5. **Add AWS WAF** (low priority)  
   Add WAF v2 + managed rules + rate limiting to CloudFront. Additional cost applies.

---

## Security Headers (AWS CloudFront — 確認済み 2026-02-23)

> Pulumi リソース: `aws.cloudfront.ResponseHeadersPolicy` (`multicloud-auto-deploy-{stack}-security-headers`)
> `default_cache_behavior` + `/sns*` ordered_cache_behavior 両方に適用。

```
Strict-Transport-Security: max-age=31536000; includeSubDomains
Content-Security-Policy: upgrade-insecure-requests
X-Content-Type-Options: nosniff
X-Frame-Options: SAMEORIGIN
X-XSS-Protection: 1; mode=block
Referrer-Policy: strict-origin-when-cross-origin
```

**`upgrade-insecure-requests` の効果**:
- ブラウザが `http://` サブリソース (画像・スクリプト・CSS) を自動的に `https://` にアップグレード
- Mixed Content による「保護されていない通信」警告を防止
- HSTS と合わせて二重の HTTPS 強制を実現

**検証コマンド**:

```bash
curl -sI https://staging.aws.ashnova.jp/ | grep -iE 'strict-transport|content-security|x-content|x-frame|referrer'
# 期待値:
# strict-transport-security: max-age=31536000; includeSubDomains
# content-security-policy: upgrade-insecure-requests
# x-content-type-options: nosniff
# x-frame-options: SAMEORIGIN
# referrer-policy: strict-origin-when-cross-origin
```

---

## S3 セキュリティ (AWS — フロントエンドバケット)

**設定済み (2026-02-23)**:

```python
# infrastructure/pulumi/aws/__main__.py
BucketPublicAccessBlock(
    block_public_acls=True,
    ignore_public_acls=True,
    block_public_policy=True,
    restrict_public_buckets=True,
)
```

| 項目 | 状態 |
| ---- | ---- |
| S3 HTTP ウェブサイトエンドポイント | 403 Forbidden (パブリックアクセス完全遮断) |
| バケットポリシー | OAI (`aws:SourceArn: CloudFront`) のみ許可 |
| CloudFront 経由 HTTPS | 200 OK |

**API の HTTP URL スルー防止 (`aws_backend.py`)**:

```python
# _resolve_image_urls: http:// URL はスキップして Mixed Content を防ぐ
if k.startswith("https://"):
    result.append(k)           # そのまま使用
elif k.startswith("http://"):
    logger.warning("Skipping insecure HTTP image URL")  # スキップ
else:
    result.append(self._key_to_presigned_url(k))  # S3キー → presigned HTTPS URL
```

---

## Azure CORS Configuration (Critical — Read Before Touching Azure)

Azure Functions (Flex Consumption) has **two independent CORS layers** that must both be
configured correctly. Setting CORS in Python/FastAPI code has no effect.

### Layer 1 — Function App platform CORS (controls API requests)

Kestrel (.NET HTTP server) intercepts all `OPTIONS` preflight requests before the Python
runtime. Configure via Azure CLI:

```bash
# Remove wildcard first (wildcards suppress per-origin rules)
az functionapp cors remove \
  --resource-group "$RESOURCE_GROUP" \
  --name "$FUNCTION_APP_NAME" \
  --allowed-origins '*'

# Add specific origins
az functionapp cors add \
  --resource-group "$RESOURCE_GROUP" \
  --name "$FUNCTION_APP_NAME" \
  --allowed-origins "https://your.domain.com"
```

### Layer 2 — Blob Storage CORS (controls image uploads via SAS URL)

Image uploads go directly from the browser to Blob Storage via SAS PUT URL — they do NOT
pass through the Function App. Blob Storage CORS is completely independent:

```bash
az storage cors clear --account-name "$STORAGE_ACCOUNT" --services b
az storage cors add \
  --account-name "$STORAGE_ACCOUNT" \
  --services b \
  --methods GET POST PUT DELETE OPTIONS \
  --origins "https://your.domain.com" \
  --allowed-headers "*" \
  --exposed-headers "*" \
  --max-age 3600
```

### Summary

```
Browser → Function App  API calls (GET/POST/PUT/DELETE)
  ⇒ Configured via: az functionapp cors add

Browser → Blob Storage  Image uploads (SAS URL PUT)
  ⇒ Configured via: az storage cors add --services b
```

---

## Next Section

→ [09 — Remaining Tasks](AI_AGENT_09_TASKS.md)
