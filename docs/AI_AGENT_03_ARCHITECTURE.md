# 03 — Architecture

> Parent: [AI_AGENT_GUIDE.md](AI_AGENT_GUIDE.md)

---

## System Overview

```
User
  │
  ├─ [AWS]   CloudFront ──► S3 (React SPA: landing + SNS pages)  ← static
  │         API Gateway v2 ──► Lambda (Python 3.12) ──► DynamoDB
  │
  ├─ [Azure] Front Door ─┬─ /sns/* ──► Azure Functions frontend-web (Python FastAPI)
  │                       └─ /*     ──► Blob Storage $web (landing)
  │         Azure Functions func ──► Cosmos DB (Serverless)
  │
  └─ [GCP]   Cloud LB ─┬─ /sns/* ──► Cloud Run frontend-web (Python FastAPI + Jinja2)
                        └─ /*     ──► GCS (landing)
             Cloud Run api ──► Firestore
```

> ⚠️ **Frontend architecture inconsistency**: AWS uses a React SPA (static S3) for the SNS
> pages, while Azure and GCP still serve the SNS app from a Python FastAPI server
> (`services/frontend_web`). The original plan was Python-on-Lambda for both frontend and
> backend, but Lambda cannot render HTML. AWS was migrated to React first;
> Azure and GCP remain on the server-side Python implementation.

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

| Content       | AWS                | Azure       | GCP                |
| ------------- | ------------------ | ----------- | ------------------ |
| Landing pages | `s3://bucket/`     | `$web/`     | `gs://bucket/`     |
| SNS pages     | `s3://bucket/sns/` (React SPA) | Azure Functions `frontend-web` (Python) | Cloud Run `frontend-web` (Python) |

> Azure と GCP の SNS ページは静的ファイルではなく Python サーバーが動的に生成する。

---

## AWS Architecture Detail

```
CloudFront (E1TBH4R432SZBZ / staging, E214XONKTXJEJD / production)
  ├── /sns/* → API Gateway → Lambda: frontend-web  (SNS API: auth, posts, etc.)
  └── /*     → S3: multicloud-auto-deploy-{env}-frontend/  (React SPA + landing)

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

Lambda: multicloud-auto-deploy-{env}-frontend-web  [legacy — Python SSR, superseded by S3/React]
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

> ⚠️ **Not yet migrated to React**: frontend is served by Python FastAPI on Azure Functions.
> See System Overview note above.

```
Front Door (multicloud-auto-deploy-staging-fd)
  endpoint: mcad-staging-d45ihd
  ├── /sns/*  → origin: Azure Functions frontend-web  (Python FastAPI, SNS pages)
  │               multicloud-auto-deploy-staging-frontend-web-v2.azurewebsites.net
  └── /*      → origin: Blob Storage $web  (landing pages only)
                  mcadwebd45ihd.z11.web.core.windows.net

Azure Functions frontend-web (FC1 FlexConsumption)  ← serves /sns/* pages
  └── HTTP Trigger: /{*route}
        ← FastAPI (custom ASGI bridge, no Mangum) + Jinja2 / API responses
        ← STAGE_NAME=sns, API_BASE_URL=<func endpoint>

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

> ⚠️ **Not yet migrated to React**: frontend is served by Python FastAPI on Cloud Run.
> See System Overview note above.

```
Global IP: 34.117.111.182
  └── HTTP Forwarding Rule
        └── URL Map
              ├── /sns/* → Backend Service → Cloud Run: frontend-web  (Python FastAPI, SNS pages)
              └── /*     → Backend Bucket  → GCS: ashnova-multicloud-auto-deploy-staging-frontend
                                                    (landing pages only)

Cloud Run: multicloud-auto-deploy-staging-frontend-web  (SNS Frontend — Python SSR)
  URL: https://multicloud-auto-deploy-staging-frontend-web-son5b3ml7a-an.a.run.app
  └── FastAPI + Jinja2 templates (Auth: Firebase Google Sign-In)
  └── Proxies API requests to multicloud-auto-deploy-staging-api

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

→ [04 — API & Data Model](AI_AGENT_04_API.md)
