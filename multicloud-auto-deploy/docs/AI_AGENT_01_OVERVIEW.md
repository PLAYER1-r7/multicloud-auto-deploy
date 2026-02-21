# 01 — Project Overview

> Parent: [AI_AGENT_GUIDE.md](AI_AGENT_GUIDE.md)

---

## What This Project Is

**multicloud-auto-deploy** is a platform that deploys the **same full-stack application** (an SNS-style messaging app) simultaneously to **AWS, Azure, and GCP** via fully automated CI/CD pipelines.

- Frontend: React 18 + Vite + TypeScript + Tailwind CSS
- Backend: FastAPI (Python 3.12) — Lambda / Azure Functions / Cloud Run
- Database: DynamoDB / Cosmos DB / Firestore (shared logical schema)
- IaC: Pulumi Python SDK
- CI/CD: GitHub Actions

---

## Live Endpoints (staging, 2026-02-21)

### AWS (ap-northeast-1)

| Purpose           | URL                                                                                      |
| ----------------- | ---------------------------------------------------------------------------------------- |
| CDN (CloudFront)  | `https://d1tf3uumcm4bo1.cloudfront.net`                                                  |
| API (API Gateway) | `https://z42qmqdqac.execute-api.ap-northeast-1.amazonaws.com`                            |
| S3 direct         | `http://multicloud-auto-deploy-staging-frontend.s3-website-ap-northeast-1.amazonaws.com` |

### Azure (japaneast)

| Purpose          | URL                                                                                                           |
| ---------------- | ------------------------------------------------------------------------------------------------------------- |
| CDN (Front Door) | `https://mcad-staging-d45ihd-dseygrc9c3a3htgj.z01.azurefd.net`                                                |
| API (Functions)  | `https://multicloud-auto-deploy-staging-func-d8a2guhfere0etcq.japaneast-01.azurewebsites.net/api/HttpTrigger` |
| Blob direct      | `https://mcadwebd45ihd.z11.web.core.windows.net`                                                              |

### GCP (asia-northeast1)

| Purpose                      | URL                                                                                         |
| ---------------------------- | ------------------------------------------------------------------------------------------- |
| CDN (Cloud CDN)              | `http://34.117.111.182`                                                                     |
| API (Cloud Run)              | `https://multicloud-auto-deploy-staging-api-son5b3ml7a-an.a.run.app`                        |
| Web Frontend (Cloud Run)     | `https://multicloud-auto-deploy-staging-frontend-web-son5b3ml7a-an.a.run.app`               |
| GCS direct                   | `https://storage.googleapis.com/ashnova-multicloud-auto-deploy-staging-frontend/index.html` |

---

## Tech Stack Summary

```
Frontend
  React 18.2 / Vite 7.3 / TypeScript / Tailwind CSS / Axios
  Hosting: S3 + CloudFront / Blob + Front Door / GCS + Cloud CDN
  Build flag: base="/sns/"  ← app is served from /sns/ on every CDN

Backend
  FastAPI 1.0 / Python 3.12 / Pydantic v2 / Mangum (Lambda adapter)
  AWS:   Lambda (x86_64) + API Gateway v2 (HTTP) + Lambda Layer
  Azure: Azure Functions (Python 3.12)
  GCP:   Cloud Run (Python 3.12, gen2)
  Local: uvicorn + DynamoDB Local + MinIO

Database (shared logical schema)
  AWS:   DynamoDB — table: simple-sns-messages
  Azure: Cosmos DB Serverless — db: simple-sns-cosmos
  GCP:   Firestore (Native) — collections: messages / posts

Infrastructure
  Pulumi Python SDK 3.x
  State: Pulumi Cloud (remote)
  AWS state fallback: s3://multicloud-auto-deploy-pulumi-state

Authentication
  AWS:   Amazon Cognito  (auto-provisioned by Pulumi)  ✅ verified
  Azure: Azure AD        (auto-provisioned by Pulumi)  ✅ verified
  GCP:   Firebase Auth   (Google Sign-In, httponly Cookie session)  ✅ verified 2026-02-21
  Staging: AUTH_DISABLED=false  ← WARNING: was mistakenly set to true in the past
```

---

## Repository Root Layout (key paths)

```
multicloud-auto-deploy/
├── .github/workflows/        ← REAL workflows that CI reads (edit ONLY here)
├── infrastructure/
│   └── pulumi/
│       ├── aws/              ← __main__.py
│       ├── azure/            ← __main__.py
│       └── gcp/              ← __main__.py
├── services/
│   ├── api/                  ← FastAPI application (app/)
│   ├── frontend_react/       ← React application (src/)
│   └── frontend_reflex/      ← experimental Reflex frontend (not in production)
├── scripts/                  ← deploy / test shell scripts
├── static-site/              ← landing pages (plain HTML/CSS)
│   ├── index.html
│   ├── aws/
│   ├── azure/
│   └── gcp/
└── docs/
    ├── AI_AGENT_GUIDE.md     ← entry point for this series
    └── archive/              ← archived / superseded documents
```

---

## Development Branch Strategy

```
feature/xxx  (local only — do NOT push)
     ↓ merge
develop  →  push  →  staging auto-deploy
     ↓ merge
main     →  push  →  production auto-deploy  ⚠️ goes live immediately
```

---

## Development Environment

### Host Machine
- **Architecture: ARM (Apple Silicon M-series Mac)**
- OS: macOS (Apple Silicon)
- Dev environment: VS Code Dev Container (`.devcontainer/`)

### Dev Container spec
| Component     | Version / Detail                                   |
|---------------|----------------------------------------------------|
| Base image    | `mcr.microsoft.com/devcontainers/base:ubuntu`      |
| Python        | 3.12 (devcontainer feature)                        |
| Node.js       | 22 (devcontainer feature)                          |
| Docker        | Docker-in-Docker v2 (moby=false)                   |
| Cloud CLIs    | AWS CLI, Azure CLI, Google Cloud SDK, GitHub CLI   |
| IaC           | Pulumi CLI (latest)                                |
| Ports exposed | 3000 (frontend dev), 8000 (API), 8080 (misc)       |

### ARM-specific build notes

> ⚠️ **ARM/Apple Silicon 注意事項**

Lambda 関数・Azureデプロイパッケージのビルドには `--platform linux/amd64` が必要。
Flex Consumption deployment (Azure): `.so` ファイルを事前に除去する必要あり。

```bash
# Lambda レイヤーのビルド (ARM ホストから x86_64 向けにビルド)
docker run --platform linux/amd64 -v "$(pwd):/workspace" python:3.12-slim bash -c \
  "pip install -r /workspace/requirements.txt --target /workspace/.package"

# GCP Cloud Run は Cloud Build で動作するため ARM 問題なし
# AWS Lambda は x86_64 ビルド必須 (ARM native は不可)
```

### Local Development
```bash
# Dev Container 内で実行
cd /workspaces/ashnova/multicloud-auto-deploy
docker compose up -d          # API (uvicorn) + DynamoDB Local + MinIO + frontend_web
curl http://localhost:8000/health   # API 確認
open http://localhost:3000/sns/     # SNS アプリ確認
```

### Cloud Credentials (auto-mounted from host)
Dev Container は以下をホストマシンからマウント：
- `~/.aws` → AWS CLI 認証情報
- `~/.azure` → Azure CLI 認証情報
- `~/.config/gcloud` → Google Cloud SDK 認証情報

---

## Next Section

→ [02 — Repository Layout](AI_AGENT_02_LAYOUT.md)
