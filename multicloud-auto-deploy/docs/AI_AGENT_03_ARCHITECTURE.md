# 03 — Architecture

> Parent: [AI_AGENT_GUIDE.md](AI_AGENT_GUIDE.md)

---

## System Overview

```
User
  │
  ├─ [AWS]   CloudFront ──► S3 (landing + SNS app)
  │         API Gateway v2 ──► Lambda (Python 3.12) ──► DynamoDB
  │
  ├─ [Azure] Front Door ──► Blob Storage $web (landing + SNS app)
  │         Azure Functions ──► Cosmos DB (Serverless)
  │
  └─ [GCP]   Cloud CDN (IP: 34.117.111.182) ──► GCS (landing + SNS app)
             Cloud Run ──► Firestore
```

---

## Storage Path Structure (shared across all 3 clouds)

```
bucket-root/
├── index.html          ← landing page
├── error.html
├── aws/
├── azure/
├── gcp/
└── sns/               ← React SNS app (Vite build, base="/sns/")
    ├── index.html
    └── assets/
        ├── index-*.js
        └── index-*.css
```

**CI deploy destinations**:

| Content       | AWS                | Azure       | GCP                |
| ------------- | ------------------ | ----------- | ------------------ |
| Landing pages | `s3://bucket/`     | `$web/`     | `gs://bucket/`     |
| SNS React app | `s3://bucket/sns/` | `$web/sns/` | `gs://bucket/sns/` |

---

## AWS Architecture Detail

```
CloudFront (E1TBH4R432SZBZ)
  ├── /sns/* → S3: multicloud-auto-deploy-staging-frontend/sns/
  └── /*     → S3: multicloud-auto-deploy-staging-frontend/  (landing)

API Gateway v2 HTTP (z42qmqdqac)
  └── $default → Lambda: multicloud-auto-deploy-staging-api
                  └── DynamoDB: simple-sns-messages (PAY_PER_REQUEST)
```

**Lambda Layer**: `multicloud-auto-deploy-staging-dependencies`  
— Contains only FastAPI / Mangum / JWT dependencies; boto3 is included in the Lambda runtime.  
— App code (~78 KB) and Layer (~8-10 MB) are deployed separately.

---

## Azure Architecture Detail

```
Front Door (multicloud-auto-deploy-staging-fd)
  endpoint: mcad-staging-d45ihd
  ├── /sns/* → origin: mcadwebd45ihd.z11.web.core.windows.net ($web/sns/)
  └── /*     → origin: mcadwebd45ihd.z11.web.core.windows.net ($web/)

Azure Functions: multicloud-auto-deploy-staging-func
  └── HTTP Trigger: /api/HttpTrigger
        └── Cosmos DB: simple-sns-cosmos (Serverless)
```

**Resource Group**: `multicloud-auto-deploy-staging-rg` (japaneast)  
**WAF**: Not configured (Standard SKU; can be added with Premium SKU)

---

## GCP Architecture Detail

```
Global IP: 34.117.111.182
  └── HTTP Forwarding Rule
        └── URL Map (default)
              └── Backend Bucket: multicloud-auto-deploy-staging-cdn-backend
                    └── GCS: ashnova-multicloud-auto-deploy-staging-frontend
                          ├── / → index.html (landing)
                          └── /sns/ → sns/index.html

Cloud Run: multicloud-auto-deploy-staging-api  (API)
  └── Firestore (default) — collections: messages, posts
  └── GCS: ashnova-multicloud-auto-deploy-staging-uploads (presigned URL upload/image display)

Cloud Run: multicloud-auto-deploy-staging-frontend-web  (SSR Frontend)
  URL: https://multicloud-auto-deploy-staging-frontend-web-son5b3ml7a-an.a.run.app
  └── FastAPI + Jinja2 templates (Auth: Firebase Google Sign-In)
  └── Proxies API requests to multicloud-auto-deploy-staging-api
```

**Note**: GCP uses a Classic External LB (`EXTERNAL` scheme).  
SPA deep links return HTTP 404 with an HTML body (works in browsers, returns 404 in curl).  
True HTTP 200 responses require migration to `EXTERNAL_MANAGED` (not yet implemented).

---

## Backend Cloud Auto-Detection Logic

```python
# services/api/app/config.py
# Can be set explicitly via CLOUD_PROVIDER env var, or auto-detected:
AWS_EXECUTION_ENV   present → "aws"
WEBSITE_INSTANCE_ID present → "azure"
K_SERVICE           present → "gcp"
otherwise                   → "local"
```

---

## Authentication Flow

```
API Backend (services/api):
  Client
    → Authorization: Bearer <JWT>
    → FastAPI auth.py (when AUTH_DISABLED=false)
         → jwt_verifier.py
              AWS:   Cognito JWKS endpoint validation
              Azure: Azure AD JWKS validation
              GCP:   Firebase Auth JWKS validation
         → validation OK → routes/*

GCP frontend-web (services/frontend_web) — separate httponly Cookie flow:
  Browser → /sns/login
    → Firebase Google Sign-In popup (Firebase SDK v10.8.0)
    → POST /sns/session { token: <Firebase ID token> }
    → FastAPI verifies token → set httponly session cookie
    → onIdTokenChanged → auto-refresh session cookie on token expiry
```

Staging: `AUTH_DISABLED=false` (was accidentally set to `true` in the past — now fixed)

---

## Security Configuration Status

| Feature          | AWS              | Azure             | GCP                         |
| ---------------- | ---------------- | ----------------- | --------------------------- |
| HTTPS enforced   | ✅ CloudFront    | ✅ Front Door     | ❌ HTTP only (needs fixing) |
| WAF              | ❌ Not set       | ❌ Not set (TODO) | ✅ Cloud Armor              |
| Data encryption  | ✅ SSE-S3        | ✅ Azure SSE      | ✅ Google-managed           |
| Versioning       | ✅               | ✅                | ✅                          |
| Access logs      | ✅               | ❌                | ✅                          |
| Security headers | ✅ CloudFront RP | ❌                | ❌                          |

---

## Next Section

→ [04 — API & Data Model](AI_AGENT_04_API.md)
