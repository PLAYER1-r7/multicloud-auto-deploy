# Multi-Cloud Auto Deploy Platform

Full-stack auto-deploy platform for AWS, Azure, and GCP.
Integrates FastAPI backend, React frontend, Pulumi IaC, and GitHub Actions CI/CD as a reference implementation.

[![Deploy to AWS](https://github.com/PLAYER1-r7/multicloud-auto-deploy/actions/workflows/deploy-aws.yml/badge.svg)](https://github.com/PLAYER1-r7/multicloud-auto-deploy/actions/workflows/deploy-aws.yml)
[![Deploy to Azure](https://github.com/PLAYER1-r7/multicloud-auto-deploy/actions/workflows/deploy-azure.yml/badge.svg)](https://github.com/PLAYER1-r7/multicloud-auto-deploy/actions/workflows/deploy-azure.yml)
[![Deploy to GCP](https://github.com/PLAYER1-r7/multicloud-auto-deploy/actions/workflows/deploy-gcp.yml/badge.svg)](https://github.com/PLAYER1-r7/multicloud-auto-deploy/actions/workflows/deploy-gcp.yml)

---

## Live Environment Endpoints

> Details: [docs/ENDPOINTS.md](docs/ENDPOINTS.md)

| Cloud | API | CDN (Pulumi-managed) |
|---|---|---|
| **AWS** (ap-northeast-1) | [API Gateway](https://z42qmqdqac.execute-api.ap-northeast-1.amazonaws.com) | [CloudFront](https://d1tf3uumcm4bo1.cloudfront.net) |
| **Azure** (japaneast) | [Functions](https://multicloud-auto-deploy-staging-func-d8a2guhfere0etcq.japaneast-01.azurewebsites.net/api/HttpTrigger) | [Front Door](https://mcad-staging-d45ihd-dseygrc9c3a3htgj.z01.azurefd.net) |
| **GCP** (asia-northeast1) | [Cloud Run](https://multicloud-auto-deploy-staging-api-son5b3ml7a-an.a.run.app) | [Cloud CDN](http://34.117.111.182) |

---

## Project Structure

```
multicloud-auto-deploy/
├── .github/workflows/     # GitHub Actions (deploy-aws.yml, deploy-azure.yml, deploy-gcp.yml)
├── infrastructure/pulumi/ # Pulumi Python — AWS / Azure / GCP
├── services/
│   ├── api/               # FastAPI (Python 3.12)
│   ├── frontend_react/    # React + Vite + TypeScript
│   └── frontend_reflex/   # Reflex frontend (experimental)
├── scripts/               # Deploy and test scripts
├── docs/                  # Documentation
└── static-site/           # Environment selection static page
```

---

## Quick Start

### Local Development

```bash
# Install dependencies
pip install -r services/api/requirements.txt
cd services/frontend_react && npm install

# Start dev servers
docker-compose up -d api
cd services/frontend_react && npm run dev
# API:      http://localhost:8000/docs
# Frontend: http://localhost:5173
```

### Cloud Deploy (Pulumi)

```bash
# AWS
cd infrastructure/pulumi/aws && pulumi up

# Azure
cd infrastructure/pulumi/azure && pulumi up

# GCP
cd infrastructure/pulumi/gcp && pulumi up
```

### Via Makefile (recommended)

```bash
make deploy-aws    # Deploy to AWS
make deploy-azure  # Deploy to Azure
make deploy-gcp    # Deploy to GCP
make test-all      # E2E tests across all clouds
```

---

## Prerequisites

| Tool | Version |
|---|---|
| Python | 3.12+ |
| Node.js | 18+ |
| Docker & Docker Compose | latest |
| Pulumi | 3.0+ |
| AWS CLI | 2.x |
| Azure CLI | latest |
| gcloud CLI | 556.0+ |

---

## GitHub Actions CI/CD

Auto-deploy runs on push/merge.

| Workflow | Trigger | Target |
|---|---|---|
| `deploy-aws.yml` | push to `main`/`develop` | AWS Lambda + API GW + S3 |
| `deploy-azure.yml` | push to `main`/`develop` | Azure Functions + Blob |
| `deploy-gcp.yml` | push to `main`/`develop` | Cloud Run + Cloud Storage |

### Branch Protection (`main`)

- **1 approving review required** before merge
- **Status checks required**: `deploy-aws`, `deploy-gcp`, `deploy-azure` must pass
- **Stale review dismissal**: enabled (re-approval required after new push)

### Required GitHub Secrets

In addition to cloud credentials, the following secrets control runtime configuration:

| Secret | Description | Example |
|---|---|---|
| `ALARM_EMAIL` | Email for monitoring alerts (SNS / Action Group / Cloud Monitoring) | `alerts@example.com` |
| `ALLOWED_ORIGINS` | Comma-separated CORS allowed origins | `https://example.com` or `*` |
| `GCP_MONTHLY_BUDGET_USD` | GCP billing budget threshold (USD) | `100` |

See [docs/CICD_SETUP.md](docs/CICD_SETUP.md) for full GitHub Secrets configuration.

---

## Tech Stack

| Layer | AWS | Azure | GCP |
|---|---|---|---|
| **Frontend** | S3 + CloudFront | Blob Storage + Front Door | Cloud Storage + Cloud CDN |
| **Backend** | Lambda (Python 3.12) + API Gateway v2 | Azure Functions (Python 3.12) | Cloud Run (Python 3.12) |
| **Database** | DynamoDB | Cosmos DB (Serverless) | Firestore (Native) |
| **Auth** | Amazon Cognito | Azure AD | Firebase Auth |
| **IaC** | Pulumi (Python) | Pulumi (Python) | Pulumi (Python) |
| **WAF** | AWS WAF v2 | Azure Front Door WAF | Cloud Armor |

---

## Documentation

| Document | Description |
|---|---|
| [ARCHITECTURE.md](docs/ARCHITECTURE.md) | System design and cloud-specific architecture diagrams (Mermaid) |
| [SETUP.md](docs/SETUP.md) | Detailed initial setup steps |
| [CICD_SETUP.md](docs/CICD_SETUP.md) | GitHub Actions and Secrets configuration |
| [ENDPOINTS.md](docs/ENDPOINTS.md) | All environment endpoint listings |
| [AUTHENTICATION_SETUP.md](docs/AUTHENTICATION_SETUP.md) | Cognito / Azure AD / Firebase Auth |
| [CDN_SETUP.md](docs/CDN_SETUP.md) | CloudFront / Front Door / Cloud CDN |
| [MONITORING.md](docs/MONITORING.md) | Monitoring and alerting setup |
| [SECURITY.md](docs/SECURITY.md) | WAF and encryption configuration |
| [TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md) | Problem resolution guide |
| [ENVIRONMENT_STATUS.md](docs/ENVIRONMENT_STATUS.md) | Current environment status |
| [QUICK_REFERENCE.md](docs/QUICK_REFERENCE.md) | Frequently used commands |
| [PRODUCTION_CHECKLIST.md](PRODUCTION_CHECKLIST.md) | Pre-production deployment checklist |
| [TOOLS_REFERENCE.md](docs/TOOLS_REFERENCE.md) | Developer tools reference |

---

## Testing

```bash
# API health check
bash scripts/test-endpoints.sh

# E2E tests (all clouds)
bash scripts/test-e2e.sh

# CI/CD status check
bash scripts/monitor-cicd.sh
```

---

## License

MIT License
