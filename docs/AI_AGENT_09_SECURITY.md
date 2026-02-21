# 09 — Security

> Parent: [AI_AGENT_GUIDE.md](AI_AGENT_GUIDE.md)

---

## Current Security Configuration Status

| Feature                   | AWS              | Azure        | GCP               | Notes                                                |
| ------------------------- | ---------------- | ------------ | ----------------- | ---------------------------------------------------- |
| HTTPS enforced            | ✅               | ✅           | ❌                | GCP: HTTP only (needs fixing)                        |
| WAF                       | ❌               | ❌           | ✅ Cloud Armor    | Not configured on AWS / Azure                        |
| Rate limiting             | ❌               | ❌           | ✅ 100req/min/IP  |                                                      |
| SQLi / XSS protection     | ❌               | ❌           | ✅                |                                                      |
| Data encryption (at rest) | ✅ SSE-S3        | ✅ Azure SSE | ✅ Google-managed |                                                      |
| Versioning                | ✅               | ✅           | ✅                |                                                      |
| Access logs               | ✅               | ❌           | ✅                |                                                      |
| Security headers          | ✅ CloudFront RP | ❌           | ❌                | HSTS, CSP, X-Frame-Options                           |
| Soft delete / retention   | ❌               | ✅ 7 days    | ❌                |                                                      |
| CORS config               | ✅               | ✅           | ✅                | `allowedOrigins` is currently `*` (needs tightening) |

---

## Authentication Configuration

### AWS — Amazon Cognito

```
Auto-created by Pulumi:
  - Cognito User Pool
  - User Pool Client
  - User Pool Domain

Lambda environment variables:
  AUTH_PROVIDER=cognito
  COGNITO_USER_POOL_ID=<Pulumi output>
  COGNITO_CLIENT_ID=<Pulumi output>
  AWS_REGION=ap-northeast-1
```

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

## Security Headers (configured on AWS CloudFront)

```
Strict-Transport-Security: max-age=31536000; includeSubDomains
X-Content-Type-Options: nosniff
X-Frame-Options: DENY
X-XSS-Protection: 1; mode=block
Content-Security-Policy: default-src 'self'; ...
Referrer-Policy: strict-origin-when-cross-origin
```

---

## Next Section

→ [10 — Remaining Tasks](AI_AGENT_10_TASKS.md)
