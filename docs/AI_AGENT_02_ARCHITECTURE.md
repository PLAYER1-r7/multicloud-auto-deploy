# 02 — Architecture

> Part II — Architecture & Design | Parent: [AI_AGENT_GUIDE.md](AI_AGENT_GUIDE.md)

---

## System Overview

```
User
  │
  ├─ [AWS]   CloudFront ──► S3 (React SPA: landing + SNS pages)  ← static
  │         API Gateway v2 ──▶ Lambda (Python 3.13) ──▶ DynamoDB
  │
  ├─ [Azure] Front Door ─┬─ /sns/* ──► Blob Storage $web/sns/  (React SPA ← static)
  │                       └─ /*     ──► Blob Storage $web (landing ← static)
  │         Azure Functions func ──► Cosmos DB (Serverless)
  │
  └─ [GCP]   Cloud CDN ─┬─ /sns/* ──► GCS bucket /sns/  (React SPA ← static)
                        └─ /*     ──► GCS (landing ← static)
             Cloud Run api ──► Firestore
```

> **Frontend architecture**: All 3 clouds now serve the SNS app as a **static React SPA**
> deployed to object storage (S3 / Blob Storage / GCS) and served via CDN. The Python
> `services/frontend_web` SSR service is **superseded** and no longer in the CDN path.
> React SPA workflows: `deploy-frontend-web-{aws,azure,gcp}.yml`
> SPA routing (rewrite `/sns/*` → `/sns/index.html`):
>
> - AWS: CloudFront Function `spa-sns-rewrite-{stack}`
> - Azure: AFD RuleSet `SpaRuleSet` + URL Rewrite action
> - GCP: CDN backend bucket serves GCS; `/sns/*` path rule removed from URL map (falls through to GCS)

---

## Storage Path Structure

```
bucket-root/
├── index.html          ← landing page
├── error.html
├── aws/
├── azure/
├── gcp/
└── sns/               ← React SNS app (AWS only — Vite build, base="/sns/")
    ├── index.html
    └── assets/
        ├── index-*.js
        └── index-*.css
```

**CI deploy destinations**:

| Content       | AWS                            | Azure                   | GCP                            |
| ------------- | ------------------------------ | ----------------------- | ------------------------------ |
| Landing pages | `s3://bucket/`                 | `$web/`                 | `gs://bucket/`                 |
| SNS pages     | `s3://bucket/sns/` (React SPA) | `$web/sns/` (React SPA) | `gs://bucket/sns/` (React SPA) |

All 3 clouds now serve the SNS app as a static React SPA. CDN handles SPA routing:

- **AWS**: CloudFront Function rewrites `/sns` and `/sns/` → `/sns/index.html`
- **Azure**: AFD `SpaRuleSet` URL Rewrite rewrites `/sns/*` (non-asset) → `/sns/index.html`
- **GCP**: GCS serves `sns/index.html` as default; deep links require CDN-level handling (SPA routing partially handled by browser history API)

---

## AWS Architecture Detail

```
CloudFront (E1TBH4R432SZBZ / staging, E214XONKTXJEJD / production)
  ├── /sns/* → S3: multicloud-auto-deploy-{env}-frontend/sns/  (React SPA)
  │            CloudFront Function `spa-sns-rewrite-{stack}` rewrites /sns → /sns/index.html
  └── /*     → S3: multicloud-auto-deploy-{env}-frontend/  (landing pages)

S3: multicloud-auto-deploy-{env}-frontend
  ├── index.html        ← React SPA entrypoint (Vite build)
  ├── assets/           ← JS / CSS bundles
  └── (landing, aws/, azure/, gcp/ pages)

API Gateway v2 HTTP (z42qmqdqac / staging)
  └── $default → Lambda: multicloud-auto-deploy-{env}-api  (backend)
                  └── DynamoDB: multicloud-auto-deploy-{env}-posts (PAY_PER_REQUEST)
                       ← Single Table Design (PK/SK)
                       ← POSTS パーティション: 投稿データ (GSI: postId / userId / createdAt)
                       ← PROFILES パーティション: ユーザープロフィール
                  └── S3: multicloud-auto-deploy-{env}-images (画像アップロード)
                       ← IMAGES_BUCKET_NAME 環境変数で参照

Lambda: multicloud-auto-deploy-{env}-frontend-web  [REMOVED — Python SSR superseded by React SPA]
  Dead code removed 2026-02-22. CloudFront `/sns/*` now routes directly to S3.
  See: REFACTORING_REPORT_20260222.md § 3
```

**Note**: `frontend-web` Lambda は当初 Python で SNS 画面を SSR するために作られたが、
React + S3 へ移行済み。Lambda 自体は削除されていない場合があるが、CloudFront の
`/sns/*` behavior は現在 API Gateway（バックエンド API）を向いている。

**Lambda Layer**: `multicloud-auto-deploy-staging-dependencies`
— Contains only FastAPI / Mangum / JWT dependencies; boto3 is included in the Lambda runtime.
— App code (~78 KB) and Layer (~8-10 MB) are deployed separately.

**主要環境変数**: `POSTS_TABLE_NAME`, `IMAGES_BUCKET_NAME`, `COGNITO_USER_POOL_ID`
**Observability**: AWS Lambda Powertools (Logger / Tracer / Metrics) — `SimpleSNS` namespace

---

## Azure Architecture Detail

> ✅ **Migrated to React SPA**: SNS pages are now served from Blob Storage (static files).
> The Python `frontend_web` Azure Function is superseded by `deploy-frontend-web-azure.yml`.

```
Front Door (multicloud-auto-deploy-staging-fd)
  endpoint: mcad-staging-d45ihd
  ├── /sns/*  → origin: Blob Storage $web/sns/  (React SPA — static HTML/JS/CSS)
  │               SpaRuleSet rewrites /sns/* → /sns/index.html (SPA routing)
  └── /*      → origin: Blob Storage $web  (landing pages only)
                  mcadwebd45ihd.z11.web.core.windows.net

Azure Functions frontend-web (FC1 FlexConsumption)  [LEGACY — no longer in CDN path]
  └── Still deployed; superseded by React SPA in Blob Storage
     Production: multicloud-auto-deploy-production-frontend-web-v2 (alwaysReady http=1)

Azure Functions: multicloud-auto-deploy-staging-func (Flex Consumption)  ← backend API
  └── HTTP Trigger: /{*route}  (function name: HttpTrigger)
        │  ← FastAPI (Mangum-less, カスタム ASGI ブリッジ) にフォワード
        └── Cosmos DB (Serverless)
             ← DB: simple-sns  /  Container: items
             ← 環境変数: COSMOS_DB_ENDPOINT / COSMOS_DB_KEY
             ← COSMOS_DB_DATABASE (default: simple-sns)
             ← COSMOS_DB_CONTAINER (default: items)
        └── Azure Blob Storage: images コンテナー (画像アップロード)
             ← AZURE_STORAGE_ACCOUNT_NAME / AZURE_STORAGE_ACCOUNT_KEY / AZURE_STORAGE_CONTAINER
```

**Resource Group**: `multicloud-auto-deploy-staging-rg` (japaneast)
**WAF**: Not configured (Standard SKU; can be added with Premium SKU)

---

## GCP Architecture Detail

> ✅ **Migrated to React SPA**: SNS pages are now served from GCS (static files) via Cloud CDN.
> The `/sns/*` path rule pointing to Cloud Run `frontend-web` has been removed from the URL map.

```
Global IP: 34.117.111.182
  └── HTTP Forwarding Rule
        └── URL Map
              └── /* (default) → Backend Bucket → GCS: ashnova-multicloud-auto-deploy-staging-frontend
                               (React SPA at /sns/ + landing at /)
              Note: /sns/* path rule removed (2026-02-22) — falls through to GCS default

Cloud Run: multicloud-auto-deploy-staging-frontend-web  [LEGACY — no longer in CDN path]
  URL: https://multicloud-auto-deploy-staging-frontend-web-899621454670.asia-northeast1.run.app
  └── Still deployed but CDN does NOT route requests here anymore
  CDN custom response header: Cross-Origin-Opener-Policy: same-origin-allow-popups

Cloud Run: multicloud-auto-deploy-staging-api  (Backend API)
  └── Firestore (default)
       ← posts コレクション: 投稿データ  (GCP_POSTS_COLLECTION 、default: posts)
       ← profiles コレクション: ユーザープロフィール  (GCP_PROFILES_COLLECTION、default: profiles)
  └── GCS: ashnova-multicloud-auto-deploy-staging-uploads (presigned URL upload/image display)
       ← GCP_STORAGE_BUCKET 環境変数で参照
```

**Note**: GCP uses a Classic External LB (`EXTERNAL` scheme).
URL Map path-based routing (`/sns/*` → Cloud Run) requires `EXTERNAL_MANAGED`; currently may fall back to GCS for all paths — needs verification.

---

## API Routes

| Router prefix    | 主なエンドポイント                      | 認証       |
| ---------------- | --------------------------------------- | ---------- |
| `/posts`         | GET/POST/PUT/DELETE (投稿 CRUD)         | 必要       |
| `/uploads`       | POST (presigned URL 発行)               | 必要       |
| `/profile`       | GET/PUT (プロフィール取得・更新)        | 必要       |
| `/api/messages/` | 旧フロントエンド互換エイリアス (legacy) | オプション |

旧フロントエンドとの後方互換のため `/api/messages/` エイリアスは維持されているが、新規実装は `/posts` を使用する。

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

→ [03 — API & Data Model](AI_AGENT_03_API.md)
