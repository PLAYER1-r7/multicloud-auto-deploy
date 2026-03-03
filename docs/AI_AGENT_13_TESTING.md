# 13 — Testing

> Part IV — Feature Reference | Parent: [AI_AGENT_GUIDE.md](AI_AGENT_GUIDE.md)
>
> **Coverage**: All test scripts, pytest suites, token acquisition, local stack setup, CI test integration.
> Full pytest details: [INTEGRATION_TESTS_GUIDE.md](INTEGRATION_TESTS_GUIDE.md)
> Staging endpoints and token setup: [STAGING_TEST_GUIDE.md](STAGING_TEST_GUIDE.md)

---

## Test Map

| Script / File                                     | Type      | Scope                             | Auth needed |
| ------------------------------------------------- | --------- | --------------------------------- | ----------- |
| `scripts/test-sns-local.sh`                       | E2E shell | Local docker-compose stack        | No          |
| `scripts/test-sns-aws.sh`                         | E2E shell | AWS staging SNS app               | Optional    |
| `scripts/test-sns-azure.sh`                       | E2E shell | Azure staging SNS app             | Optional    |
| `scripts/test-sns-gcp.sh`                         | E2E shell | GCP staging SNS app               | Optional    |
| `scripts/test-sns-all.sh`                         | E2E shell | All 3 clouds in sequence          | Optional    |
| `scripts/test-sns-all.sh`                         | E2E shell | All 3 clouds + summary report     | Optional    |
| `scripts/test-e2e.sh`                             | Smoke     | All 3 clouds health + CRUD        | Optional    |
| `scripts/test-endpoints.sh`                       | Health    | API health check per cloud        | No          |
| `scripts/test-landing-pages.sh`                   | Health    | Static landing page per cloud     | No          |
| `scripts/test-api.sh`                             | API       | CRUD operations per cloud         | Optional    |
| `scripts/test-auth-crud.sh`                       | Auth      | Full auth + CRUD flow             | Required    |
| `scripts/test-cloud-env.sh`                       | Config    | Env vars and cloud connectivity   | No          |
| `scripts/test-local-env.sh`                       | Config    | Local docker-compose env check    | No          |
| `scripts/test-deployments.sh`                     | Deploy    | Deployment health check           | No          |
| `scripts/test-cicd.sh`                            | CI/CD     | Workflow trigger + status check   | No          |
| `scripts/run-integration-tests.sh`                | pytest    | pytest runner (all backends)      | No          |
| `services/api/tests/test_backends_integration.py` | pytest    | Backend class unit tests (mocked) | No          |
| `services/api/tests/test_api_endpoints.py`        | pytest    | Live API endpoint tests           | Optional    |
| `services/api/tests/test_simple_sns_local.py`     | pytest    | Local docker-compose integration  | No          |

---

## Quick Commands

### 1 — Fastest: health check all clouds

```bash
./scripts/test-endpoints.sh
```

### 2 — E2E smoke test (all 3 clouds, public endpoints)

```bash
./scripts/test-e2e.sh
# Output: pass/fail table per cloud
```

### 3 — Full SNS test per cloud (public endpoints only)

```bash
./scripts/test-sns-aws.sh
./scripts/test-sns-azure.sh
./scripts/test-sns-gcp.sh

# All 3 in one command:
./scripts/test-sns-all.sh
```

### 4 — Full SNS test with authentication

```bash
# Acquire tokens first (see "Token Acquisition" section below)
./scripts/test-sns-aws.sh    --token "$AWS_TOKEN"
./scripts/test-sns-azure.sh  --token "$AZURE_TOKEN"
./scripts/test-sns-gcp.sh    --token "$GCP_TOKEN"

# All 3 with tokens:
./scripts/test-sns-all.sh \
  --aws-token   "$AWS_TOKEN"   \
  --azure-token "$AZURE_TOKEN" \
  --gcp-token   "$GCP_TOKEN"
```

### 5 — Local docker-compose stack test

```bash
# Start the stack first
docker compose up -d --build
sleep 30   # wait for all services

./scripts/test-sns-local.sh
# or pytest:
cd services/api && pytest tests/test_simple_sns_local.py -v -m local
```

### 6 — pytest (unit + backend mock tests — no network)

```bash
cd services/api
# All mocked tests
pytest tests/ -v

# Single cloud backend
pytest tests/ -v -m aws
pytest tests/ -v -m gcp
pytest tests/ -v -m azure

# With coverage
pytest tests/ --cov=app --cov-report=html
# → open htmlcov/index.html
```

### 7 — pytest against live deployed API

```bash
cd services/api
export AWS_API_ENDPOINT="https://z42qmqdqac.execute-api.ap-northeast-1.amazonaws.com"
export AZURE_API_ENDPOINT="https://multicloud-auto-deploy-staging-func-d8a2guhfere0etcq.japaneast-01.azurewebsites.net/api"
export GCP_API_ENDPOINT="https://multicloud-auto-deploy-staging-api-son5b3ml7a-an.a.run.app"
pytest tests/test_api_endpoints.py -v -m requires_network
```

---

## Token Acquisition

Authenticated tests require a bearer token from the respective cloud's identity provider.

### AWS — Cognito access token

```bash
# Via browser: log in at https://d1tf3uumcm4bo1.cloudfront.net/sns/
# DevTools → Application → Local Storage → origin → access_token

# Via AWS CLI (email/password):
aws cognito-idp initiate-auth \
  --auth-flow USER_PASSWORD_AUTH \
  --client-id 1k41lqkds4oah55ns8iod30dv2 \
  --auth-parameters USERNAME=<email>,PASSWORD=<password> \
  --region ap-northeast-1 \
  --query 'AuthenticationResult.AccessToken' --output text
```

### Azure — Azure AD id_token

```bash
# Via browser: log in at https://staging.azure.ashnova.jp/sns/
# DevTools → Application → Local Storage → id_token
```

### GCP — Firebase id_token

```bash
# Via gcloud (uses your logged-in Google account — must be a registered user):
gcloud auth print-identity-token

# Via browser: log in at https://staging.gcp.ashnova.jp/sns/
# DevTools → Application → Local Storage → id_token
```

---

## Local Docker Compose Stack

The full local development stack is defined in `docker-compose.yml` at the repo root.

```bash
docker compose up -d --build    # start all services
docker compose ps                # verify all containers are Up
docker compose logs api -f       # stream API logs
docker compose down              # stop all services
```

**Services started**:

| Service          | Port | Description                              |
| ---------------- | ---- | ---------------------------------------- |
| `api`            | 8000 | FastAPI backend (DynamoDB Local + MinIO) |
| `frontend_web`   | 8080 | Python/FastAPI SSR frontend (Jinja2)     |
| `minio`          | 9000 | S3-compatible object storage             |
| `dynamodb-local` | 8001 | DynamoDB Local                           |
| `frontend_react` | 3001 | React SPA (nginx, `/sns/`)               |
| `static_site`    | 8090 | Static landing page (nginx proxy)        |

**Key env vars set automatically by docker-compose**:

```
AUTH_DISABLED=true
CLOUD_PROVIDER=local
DYNAMODB_ENDPOINT=http://dynamodb-local:8001
MINIO_ENDPOINT=http://minio:9000
```

---

## pytest Markers

| Marker             | When activated                       | Description                            |
| ------------------ | ------------------------------------ | -------------------------------------- |
| `aws`              | always                               | AWS backend specific tests             |
| `gcp`              | always                               | GCP backend specific tests             |
| `azure`            | always                               | Azure backend specific tests           |
| `local`            | always                               | Local docker-compose integration tests |
| `requires_network` | `--run-network-tests` or env var set | Tests that call live API endpoints     |
| `slow`             | `--run-slow-tests`                   | Tests that take >5 seconds             |

---

## Staging Endpoints (reference)

| Cloud          | API Endpoint                                                                                      | Frontend URL                                 |
| -------------- | ------------------------------------------------------------------------------------------------- | -------------------------------------------- |
| AWS staging    | `https://z42qmqdqac.execute-api.ap-northeast-1.amazonaws.com`                                     | `https://d1tf3uumcm4bo1.cloudfront.net/sns/` |
| Azure staging  | `https://multicloud-auto-deploy-staging-func-d8a2guhfere0etcq.japaneast-01.azurewebsites.net/api` | `https://staging.azure.ashnova.jp/sns/`      |
| GCP staging    | `https://multicloud-auto-deploy-staging-api-son5b3ml7a-an.a.run.app`                              | `https://staging.gcp.ashnova.jp/sns/`        |
| AWS production | `https://qkzypr32af.execute-api.ap-northeast-1.amazonaws.com`                                     | `https://www.aws.ashnova.jp/sns/`            |
| GCP production | (same Cloud Run URL)                                                                              | `https://www.gcp.ashnova.jp/sns/`            |

> Always test staging before production. See [AI_AGENT_06_STATUS.md](AI_AGENT_06_STATUS.md) for current health.

---

## CI/CD Test Integration

Tests run automatically on every push via GitHub Actions:

| Workflow                   | Trigger                             | Tests run                                 |
| -------------------------- | ----------------------------------- | ----------------------------------------- |
| `deploy-aws.yml`           | push to `develop` / `main`          | Post-deploy `./scripts/test-endpoints.sh` |
| `deploy-azure.yml`         | push to `develop` / `main`          | Post-deploy `./scripts/test-endpoints.sh` |
| `deploy-gcp.yml`           | push to `develop` / `main`          | Post-deploy `./scripts/test-endpoints.sh` |
| `run-integration-tests.sh` | manual or via `test-sns-all.sh`     | pytest + E2E shell                        |

---

## Troubleshooting

| Problem                              | Cause                      | Fix                                                                      |
| ------------------------------------ | -------------------------- | ------------------------------------------------------------------------ |
| `pytest: command not found`          | Python env not activated   | `source .venv/bin/activate` or `pip install pytest`                      |
| `ImportError: No module named 'app'` | Wrong working directory    | `cd services/api` then run pytest                                        |
| `Connection refused` on local tests  | docker-compose not running | `docker compose up -d && sleep 30`                                       |
| 401 on authenticated test            | Expired token              | Re-acquire token (tokens expire in ~1 hour)                              |
| 503 on staging                       | Service cold start         | Wait 30s and retry; check [AI_AGENT_06_STATUS.md](AI_AGENT_06_STATUS.md) |

---

_Last updated: 2026-02-27_
