# 02 — Repository Layout

> Parent: [AI_AGENT_GUIDE.md](AI_AGENT_GUIDE.md)

---

## Full Directory Tree (important files only)

```
multicloud-auto-deploy/
│
├── .github/  ← lives in ashnova/ (git root). Not visible when multicloud-auto-deploy/ is opened, but CI works correctly
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
│   │   ├── requirements-layer.txt    ← Lambda Layer deps (excludes boto3)
│   │   ├── Dockerfile                ← for local dev / GCP Cloud Run
│   │   ├── Dockerfile.lambda         ← for Lambda container deployment
│   │   └── tests/
│   │       ├── conftest.py
│   │       ├── test_backends_integration.py
│   │       └── test_api_endpoints.py
│   │
│   ├── frontend_react/               ← React frontend
│   │   ├── src/
│   │   │   ├── main.tsx
│   │   │   ├── App.tsx
│   │   │   ├── api/                  ← Axios client
│   │   │   ├── components/           ← UI components
│   │   │   ├── hooks/                ← custom hooks
│   │   │   └── types/                ← TypeScript type definitions
│   │   ├── vite.config.ts            ← sets base: "/sns/"
│   │   ├── package.json
│   │   └── dist/                     ← build output (gitignored)
│
├── static-site/                      ← landing pages (plain static HTML, not SPA)
│   ├── index.html                    ← shared landing (auto-detects cloud/local env)
│   ├── error.html
│   ├── aws/                          ← AWS-themed landing (index.html + error.html)
│   ├── azure/                        ← Azure-themed landing
│   ├── gcp/                          ← GCP-themed landing
│   ├── Dockerfile                    ← nginx container image
│   └── nginx.conf
│
├── scripts/
│   ├── build-lambda-layer.sh         ← builds Lambda Layer zip
│   ├── test-api.sh                   ← single-API HTTP test
│   ├── test-e2e.sh                   ← E2E tests across all 3 clouds (18 tests)
│   ├── test-endpoints.sh             ← endpoint connectivity check
│   └── run-integration-tests.sh      ← runs pytest integration tests
│
├── docs/
│   ├── AI_AGENT_GUIDE.md             ← ★ AI agent entry point
│   ├── AI_AGENT_01_OVERVIEW.md
│   ├── AI_AGENT_02_LAYOUT.md         ← this file
│   └── archive/                      ← archived / superseded docs
│
├── docker-compose.yml                ← api + dynamodb-local + minio
├── Makefile
└── README.md
```

---

## Quick File Reference

| What you want to do         | File(s) to edit                                      |
| --------------------------- | ---------------------------------------------------- |
| Add an API endpoint         | `services/api/app/routes/*.py`                       |
| Change DB logic (AWS)       | `services/api/app/backends/aws_backend.py`           |
| Change DB logic (Azure)     | `services/api/app/backends/azure_backend.py`         |
| Change DB logic (GCP)       | `services/api/app/backends/gcp_backend.py`           |
| Add an environment variable | `services/api/app/config.py` + `Pulumi.*.yaml`       |
| Change AWS infrastructure   | `infrastructure/pulumi/aws/__main__.py`              |
| Change Azure infrastructure | `infrastructure/pulumi/azure/__main__.py`            |
| Change GCP infrastructure   | `infrastructure/pulumi/gcp/__main__.py`              |
| Edit a CI/CD workflow       | `.github/workflows/*.yml` (repo root only)           |
| Edit frontend UI            | `services/frontend_react/src/`                       |
| Edit landing pages          | `static-site/` (multicloud-auto-deploy/static-site/) |

---

## ⚠️ Location of `.github/workflows/`

When `multicloud-auto-deploy/` is opened in VS Code, the `.github/` folder is **not visible** in the tree.  
Workflows exist only in the git repository root at `ashnova/.github/workflows/` (the copy inside mcad was deleted on 2026-02-21).

```bash
# To edit workflows, navigate to the git repository root
cd /workspaces/ashnova
code .github/workflows/deploy-aws.yml
```

See [11 — Workspace Migration](AI_AGENT_11_WORKSPACE_MIGRATION.md) for details.

---

## Next Section

→ [03 — Architecture](AI_AGENT_03_ARCHITECTURE.md)
