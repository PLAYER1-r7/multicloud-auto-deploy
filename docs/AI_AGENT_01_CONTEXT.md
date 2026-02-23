# 01 — Context: Overview & Repository Layout

> Part I — Orientation | Parent: [AI_AGENT_GUIDE.md](AI_AGENT_GUIDE.md)

---

## What This Project Is

**multicloud-auto-deploy** is a platform that deploys the **same full-stack application**
(an SNS-style messaging app) simultaneously to **AWS, Azure, and GCP** via fully automated
CI/CD pipelines.

- Frontend: React 18 + Vite + TypeScript + Tailwind CSS
- Backend: FastAPI (Python 3.12) — Lambda / Azure Functions / Cloud Run
- Database: DynamoDB / Cosmos DB / Firestore (shared logical schema)
- IaC: Pulumi Python SDK
- CI/CD: GitHub Actions

---

## Live Endpoints (staging)

### AWS (ap-northeast-1)

| Purpose           | URL                                                           |
| ----------------- | ------------------------------------------------------------- |
| CDN (CloudFront)  | `https://d1tf3uumcm4bo1.cloudfront.net`                       |
| API (API Gateway) | `https://z42qmqdqac.execute-api.ap-northeast-1.amazonaws.com` |
| Custom domain     | `https://www.aws.ashnova.jp`                                  |

### Azure (japaneast)

| Purpose          | URL                                                                                           |
| ---------------- | --------------------------------------------------------------------------------------------- |
| CDN (Front Door) | `https://mcad-staging-d45ihd-dseygrc9c3a3htgj.z01.azurefd.net`                                |
| API (Functions)  | `https://multicloud-auto-deploy-staging-func-d8a2guhfere0etcq.japaneast-01.azurewebsites.net` |
| Custom domain    | `https://www.azure.ashnova.jp`                                                                |

> **Note**: The Azure API URL is the Function App base URL **without** any path suffix.
> The function uses a wildcard route `{*route}` so all API paths (e.g. `/health`, `/posts`)
> are served directly at the base URL. The `/api/HttpTrigger` path is **not** used.

### GCP (asia-northeast1)

| Purpose                  | URL                                                                                                     |
| ------------------------ | ------------------------------------------------------------------------------------------------------- |
| CDN (Cloud CDN)          | `http://34.117.111.182`                                                                                 |
| API (Cloud Run)          | `https://multicloud-auto-deploy-staging-api-899621454670.asia-northeast1.run.app`                       |
| Web Frontend (Cloud Run) | `https://multicloud-auto-deploy-staging-frontend-web-899621454670.asia-northeast1.run.app` (legacy SSR) |
| Custom domain            | `https://www.gcp.ashnova.jp`                                                                            |

> **Note**: The Cloud Run `frontend-web` service still exists but CDN routes `/sns/*` to the
> GCS bucket (React SPA) — not to Cloud Run. The Cloud Run URL is legacy.

---

## Tech Stack Summary

```
Frontend (SNS pages)
  AWS:   React 18.2 / Vite 7.3 / TypeScript / Tailwind CSS  ← static SPA in S3 (staging + production)
  Azure: React 18.2 / Vite / TypeScript  ← static SPA in Blob Storage $web/sns/ (production)
         (services/frontend_web Python SSR is superseded; CI now deploys React SPA via deploy-frontend-web-azure.yml)
  GCP:   React 18.2 / Vite / TypeScript  ← static SPA in GCS sns/ prefix (staging + production)
         (Cloud Run frontend-web still exists but CDN routes to GCS bucket, not Cloud Run)

Backend API
  FastAPI 1.0 / Python 3.12 / Pydantic v2
  AWS:   Lambda (x86_64) + API Gateway v2 (HTTP) + Lambda Layer + Mangum adapter
  Azure: Azure Functions (Python 3.12, FC1 FlexConsumption)
  GCP:   Cloud Run (Python 3.12, gen2)
  Local: uvicorn + DynamoDB Local + MinIO

Database (shared logical schema)
  AWS:   DynamoDB — table: simple-sns-messages
  Azure: Cosmos DB Serverless — db: simple-sns-cosmos
  GCP:   Firestore (Native) — collections: messages / posts

Infrastructure
  Pulumi Python SDK 3.x
  State: Pulumi Cloud (remote)

Authentication
  AWS:   Amazon Cognito  (auto-provisioned by Pulumi)
  Azure: Azure AD        (auto-provisioned by Pulumi)
  GCP:   Firebase Auth   (Google Sign-In, httponly Cookie session)
  Staging: AUTH_DISABLED=false  ← must never be true
```

---

## Repository Directory Tree

```
multicloud-auto-deploy/               ← workspace root = git repo root
│
├── .github/
│   └── workflows/                    ← ★ REAL workflows — CI reads ONLY these
│       ├── deploy-aws.yml
│       ├── deploy-azure.yml
│       ├── deploy-gcp.yml
│       ├── deploy-landing-aws.yml
│       ├── deploy-landing-azure.yml
│       ├── deploy-landing-gcp.yml
│       ├── deploy-frontend-web-aws.yml
│       ├── deploy-frontend-web-azure.yml
│       └── deploy-frontend-web-gcp.yml
│
├── infrastructure/
│   └── pulumi/
│       ├── aws/
│       │   ├── __main__.py           ← all AWS resources (S3/CF/Lambda/APIGW/DDB/Cognito)
│       │   ├── Pulumi.yaml
│       │   ├── Pulumi.staging.yaml
│       │   └── requirements.txt
│       ├── azure/
│       │   ├── __main__.py           ← all Azure resources (Storage/FuncApp/CosmosDB/FrontDoor/AD)
│       │   ├── Pulumi.yaml
│       │   └── requirements.txt
│       └── gcp/
│           ├── __main__.py           ← all GCP resources (GCS/CloudRun/Firestore/CDN)
│           ├── Pulumi.yaml
│           └── requirements.txt
│
├── services/
│   ├── api/                          ← FastAPI backend
│   │   ├── app/
│   │   │   ├── main.py               ← FastAPI app, CORS, Mangum handler
│   │   │   ├── config.py             ← Pydantic Settings (loads env vars)
│   │   │   ├── models.py             ← Pydantic models (Post, Profile, ...)
│   │   │   ├── auth.py               ← JWT auth middleware
│   │   │   ├── jwt_verifier.py       ← Cognito / Azure AD / Firebase JWT validation
│   │   │   ├── backends/
│   │   │   │   ├── base.py           ← BackendBase abstract class
│   │   │   │   ├── aws_backend.py    ← DynamoDB + S3 implementation
│   │   │   │   ├── azure_backend.py  ← Cosmos DB + Blob Storage implementation
│   │   │   │   ├── gcp_backend.py    ← Firestore + Cloud Storage implementation
│   │   │   │   └── local_backend.py  ← DynamoDB Local + MinIO implementation
│   │   │   └── routes/
│   │   │       ├── posts.py          ← POST/GET/PUT/DELETE /posts
│   │   │       ├── profile.py        ← GET/PUT /profile/{userId}
│   │   │       └── uploads.py        ← POST /uploads/presigned-url
│   │   ├── index.py                  ← Lambda handler (Mangum wrapper)
│   │   ├── function_app.py           ← Azure Functions handler
│   │   ├── function.py               ← GCP Cloud Functions handler
│   │   ├── requirements.txt          ← shared deps (fastapi, mangum, pydantic...)
│   │   ├── requirements-aws.txt      ← AWS-specific (boto3, etc.)
│   │   ├── requirements-azure.txt    ← Azure-specific (azure-cosmos, etc.)
│   │   ├── requirements-gcp.txt      ← GCP-specific (google-cloud-firestore, etc.)
│   │   └── requirements-layer.txt    ← Lambda Layer deps (excludes boto3)
│   │
│   ├── frontend_react/               ← React frontend (SNS app — AWS)
│   │   ├── src/
│   │   │   ├── main.tsx
│   │   │   ├── App.tsx
│   │   │   ├── api/                  ← Axios client
│   │   │   ├── components/           ← UI components
│   │   │   └── hooks/                ← custom hooks
│   │   ├── vite.config.ts            ← sets base: "/sns/"
│   │   └── package.json
│   │
│   └── frontend_web/                 ← Python FastAPI frontend (SNS app — Azure + GCP)
│
├── static-site/                      ← landing pages (plain HTML, not SPA)
│   ├── index.html                    ← shared landing (auto-detects cloud/local env)
│   ├── aws/  azure/  gcp/            ← cloud-themed landing variants
│   └── nginx.conf
│
├── scripts/                          ← deploy / test shell scripts
├── docs/
│   ├── AI_AGENT_GUIDE.md             ← ★ AI agent entry point
│   ├── AI_AGENT_00_CRITICAL_RULES.md ← read first
│   ├── AI_AGENT_01_CONTEXT.md        ← this file
│   └── archive/                      ← archived / superseded docs
│
├── docker-compose.yml                ← api + dynamodb-local + minio
├── Makefile
└── README.md
```

---

## Quick File Reference

| What you want to do         | File(s) to edit                                |
| --------------------------- | ---------------------------------------------- |
| Add an API endpoint         | `services/api/app/routes/*.py`                 |
| Change DB logic (AWS)       | `services/api/app/backends/aws_backend.py`     |
| Change DB logic (Azure)     | `services/api/app/backends/azure_backend.py`   |
| Change DB logic (GCP)       | `services/api/app/backends/gcp_backend.py`     |
| Add an environment variable | `services/api/app/config.py` + `Pulumi.*.yaml` |
| Change AWS infrastructure   | `infrastructure/pulumi/aws/__main__.py`        |
| Change Azure infrastructure | `infrastructure/pulumi/azure/__main__.py`      |
| Change GCP infrastructure   | `infrastructure/pulumi/gcp/__main__.py`        |
| Edit a CI/CD workflow       | `.github/workflows/*.yml` (workspace root)     |
| Edit React frontend UI      | `services/frontend_react/src/`                 |
| Edit Python frontend        | `services/frontend_web/`                       |
| Edit landing pages          | `static-site/`                                 |

---

## Development Environment

### Host Machine

- **Architecture: ARM (Apple Silicon M-series Mac)**
- Dev environment: VS Code Dev Container (`.devcontainer/`)

### Dev Container

| Component     | Detail                                           |
| ------------- | ------------------------------------------------ |
| Base image    | `mcr.microsoft.com/devcontainers/base:ubuntu`    |
| Python        | 3.12                                             |
| Node.js       | 22                                               |
| Docker        | Docker-in-Docker v2                              |
| Cloud CLIs    | AWS CLI, Azure CLI, Google Cloud SDK, GitHub CLI |
| IaC           | Pulumi CLI                                       |
| Ports exposed | 3000 (frontend dev), 8000 (API)                  |

### ARM Build Warning

> ⚠️ The dev container is `linux/aarch64`. All cloud runtimes run on `linux/amd64`.
> Always cross-compile Python packages for deployment:
>
> ```bash
> docker run --rm --platform linux/amd64 \
>   -v /tmp/deploy:/out python:3.12-slim \
>   bash -c "pip install --no-cache-dir --target /out -r requirements.txt -q"
> ```
>
> See Rule 2 in [AI_AGENT_00_CRITICAL_RULES.md](AI_AGENT_00_CRITICAL_RULES.md) for details.

### Local Development

```bash
cd /workspaces/multicloud-auto-deploy
docker compose up -d          # API (uvicorn) + DynamoDB Local + MinIO + frontend_web
curl http://localhost:8000/health
```

### Cloud Credentials (auto-mounted from host)

- `~/.aws` → AWS CLI credentials
- `~/.azure` → Azure CLI credentials
- `~/.config/gcloud` → Google Cloud SDK credentials

---

## Branch Strategy

```
feature/xxx  →  develop  →  push  →  staging auto-deploy
                    ↓
                  main   →  push  →  production auto-deploy  ⚠️ immediate
```

---

## Next Section

→ [02 — Architecture](AI_AGENT_02_ARCHITECTURE.md)
