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
  ├─ [Azure] Front Door ──► Blob Storage $web (React SPA: landing + SNS pages)  ← static
  │                          ※ SPA RuleSet が /sns/ を /sns/index.html にリライト
  │         Azure Functions func ──► Cosmos DB (Serverless)
  │
  └─ [GCP]   Cloud LB ──► GCS (React SPA: landing + SNS pages)  ← static
                           ※ 404 fallback が SPA ルーティングを担う
             Cloud Run api ──► Firestore
```

> **Production**: AWS/Azure/GCP いずれも React SPA を静的ストレージから配信済み (2026-02-21)。
>
> **Staging** ⚠️: CDN ルーティングが未修正のため `/sns/*` が旧 Python SSR (`frontend_web`) を向いている。
> `scripts/fix-staging-routing.sh` で修正可能。詳細は [AI_AGENT_07_STATUS.md](AI_AGENT_07_STATUS.md)。

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

| Content       | AWS                            | Azure                                   | GCP                               |
| ------------- | ------------------------------ | --------------------------------------- | --------------------------------- |
| Landing pages | `s3://bucket/`                 | `$web/`                                 | `gs://bucket/`                    |
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

```
Front Door (multicloud-auto-deploy-staging-fd)
  endpoint: mcad-staging-d45ihd
  └── /*  → origin: Blob Storage $web  (React SPA: landing + SNS pages)
              mcadwebd45ihd.z11.web.core.windows.net
              ├─ SPA RuleSet が /sns/ → /sns/index.html にリライト
              └─ /sns/assets/* は長期キャッシュ (immutable)

⚠️ **Staging** のみ: AFD に旧 /sns/* → Azure Functions frontend-web ルートが残存。
           `scripts/fix-staging-routing.sh` で削除必要。

Azure Functions: multicloud-auto-deploy-{staging|production}-func  ← backend API
  | HTTP Trigger: /{*route}
  └── Cosmos DB (Serverless): simple-sns / items
  └── Azure Blob Storage: images コンテナー
```

**Resource Group**: `multicloud-auto-deploy-staging-rg` (japaneast)

---

## GCP Architecture Detail

```
Global IP: 34.117.111.182
  └── HTTP/HTTPS Forwarding Rule
        └── URL Map
              └── /* (default)  → Backend Bucket  → GCS: ashnova-multicloud-auto-deploy-{env}-frontend
                                                        (React SPA: landing + SNS pages)
                                                        (/sns/ などは GCS 404 fallback → index.html)

⚠️ **Staging** のみ: URL Map に旧 /sns/* → Cloud Run frontend-web の pathRule が残存。
           `scripts/fix-staging-routing.sh` で削除必要。

Cloud Run: multicloud-auto-deploy-{staging|production}-api  (Backend API)
  └── Firestore (default)
       ← posts / profiles コレクション
  └── GCS: ashnova-multicloud-auto-deploy-{env}-uploads (presigned URL upload)
```

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
