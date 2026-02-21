# 08 — Runbooks

> Parent: [AI_AGENT_GUIDE.md](AI_AGENT_GUIDE.md)  
> Step-by-step procedures for common tasks and incident response

---

## [RB-01] Manually Update a Lambda Function

```bash
# 1. Package app code only (ZIP)
cd /workspaces/ashnova/multicloud-auto-deploy/services/api
rm -rf .build && mkdir -p .build/package
cp -r app .build/package/
cp index.py .build/package/
cd .build/package && zip -r ../../lambda.zip . && cd ../..

# 2. Update Lambda
aws lambda update-function-code \
  --function-name multicloud-auto-deploy-staging-api \
  --zip-file fileb://lambda.zip \
  --region ap-northeast-1

# 3. Verify update
aws lambda invoke \
  --function-name multicloud-auto-deploy-staging-api \
  --payload '{"version":"2.0","routeKey":"$default","rawPath":"/health","requestContext":{"http":{"method":"GET","path":"/health"}}}' \
  --cli-binary-format raw-in-base64-out \
  /tmp/response.json && cat /tmp/response.json | python3 -m json.tool
```

---

## [RB-02] Check Lambda logs

```bash
# Live tail
aws logs tail /aws/lambda/multicloud-auto-deploy-staging-api --follow --region ap-northeast-1

# Last 10 minutes, errors only
aws logs tail /aws/lambda/multicloud-auto-deploy-staging-api \
  --since 10m --filter-pattern "ERROR" --region ap-northeast-1
```

---

## [RB-03] Manually deploy the React frontend (AWS)

```bash
cd /workspaces/ashnova/multicloud-auto-deploy/services/frontend_react
npm ci

# Build with API URL; base="/sns/" is already fixed in vite.config.ts
VITE_API_URL=https://z42qmqdqac.execute-api.ap-northeast-1.amazonaws.com npm run build

# Upload to S3 — MUST use sns/ prefix
aws s3 sync dist/ s3://multicloud-auto-deploy-staging-frontend/sns/ \
  --delete --region ap-northeast-1

# Invalidate CloudFront cache
aws cloudfront create-invalidation \
  --distribution-id E1TBH4R432SZBZ \
  --paths "/*"
```

---

## [RB-04] Manually deploy the landing page (AWS)

```bash
# Upload static-site/ to bucket root
aws s3 sync /workspaces/ashnova/multicloud-auto-deploy/static-site/ \
  s3://multicloud-auto-deploy-staging-frontend/ \
  --delete --region ap-northeast-1

aws cloudfront create-invalidation \
  --distribution-id E1TBH4R432SZBZ \
  --paths "/*"
```

---

## [RB-05] Manually deploy Azure Functions

```bash
cd /workspaces/ashnova/multicloud-auto-deploy/services/api

# Create deployment package
pip install -r requirements-azure.txt -t .deploy-azure/
cp -r app .deploy-azure/
cp function_app.py host.json local.settings.json .deploy-azure/

# Zip
cd .deploy-azure && zip -r ../function-app.zip . && cd ..

# Deploy via Azure CLI
az functionapp deployment source config-zip \
  --resource-group multicloud-auto-deploy-staging-rg \
  --name multicloud-auto-deploy-staging-func \
  --src function-app.zip
```

---

## [RB-06] Manually deploy GCP Cloud Run

```bash
cd /workspaces/ashnova/multicloud-auto-deploy/services/api

# Zip source for Cloud Run build
zip -r gcp-cloudrun-source.zip app/ function.py requirements.txt requirements-gcp.txt Dockerfile

# Deploy from source with gcloud
gcloud run deploy multicloud-auto-deploy-staging-api \
  --source . \
  --region asia-northeast1 \
  --project ashnova \
  --platform managed \
  --allow-unauthenticated \
  --set-env-vars "CLOUD_PROVIDER=gcp,AUTH_DISABLED=false,GCP_POSTS_COLLECTION=posts"
```

---

## [RB-07] Re-deploy a Pulumi stack

```bash
# AWS
cd /workspaces/ashnova/multicloud-auto-deploy/infrastructure/pulumi/aws
pulumi login
pulumi stack select staging
pulumi up --yes

# Azure
cd /workspaces/ashnova/multicloud-auto-deploy/infrastructure/pulumi/azure
pulumi stack select staging
pulumi up --yes

# GCP
cd /workspaces/ashnova/multicloud-auto-deploy/infrastructure/pulumi/gcp
pulumi stack select staging
pulumi up --yes
```

---

## [RB-08] Run API endpoint tests

```bash
# E2E across all clouds (curl-based)
./scripts/test-e2e.sh

# Single cloud
./scripts/test-api.sh -e https://z42qmqdqac.execute-api.ap-northeast-1.amazonaws.com

# pytest (mock tests)
cd services/api
source .venv/bin/activate
pytest tests/test_backends_integration.py -v

# pytest (live API)
API_BASE_URL=https://z42qmqdqac.execute-api.ap-northeast-1.amazonaws.com \
  pytest tests/test_api_endpoints.py -v
```

---

## [RB-09] Verify / create the DynamoDB PostIdIndex GSI

```bash
# Check whether GSI exists
aws dynamodb describe-table \
  --table-name simple-sns-messages \
  --region ap-northeast-1 \
  --query 'Table.GlobalSecondaryIndexes[*].IndexName'

# If GSI is missing, create it
aws dynamodb update-table \
  --table-name simple-sns-messages \
  --region ap-northeast-1 \
  --attribute-definitions AttributeName=postId,AttributeType=S \
  --global-secondary-index-updates '[{"Create":{"IndexName":"PostIdIndex","KeySchema":[{"AttributeName":"postId","KeyType":"HASH"}],"Projection":{"ProjectionType":"ALL"}}}]'
```

---

## [RB-11] Rebuild and hotfix-deploy API Lambda (no CI)

Use this when you need to deploy a quick code fix to the API Lambda without waiting for CI.

```bash
cd /workspaces/ashnova/multicloud-auto-deploy/services/api

# 1. Update .build/package with latest source
cp -r app index.py .build/package/

# 2. Rebuild lambda.zip
cd .build/package
zip -r ../../lambda.zip . -x "*.pyc" -x "__pycache__/*" > /dev/null
cd ../..

# 3. Guard: wait for any in-progress update to complete first
aws lambda wait function-updated \
  --function-name multicloud-auto-deploy-staging-api \
  --region ap-northeast-1

# 4. Deploy
aws lambda update-function-code \
  --function-name multicloud-auto-deploy-staging-api \
  --region ap-northeast-1 \
  --zip-file fileb://lambda.zip \
  --output text --query 'LastUpdateStatus'

# 5. Wait for deployment to complete
aws lambda wait function-updated \
  --function-name multicloud-auto-deploy-staging-api \
  --region ap-northeast-1 && echo "Ready"
```

---

## [RB-12] Run the AWS simple-sns E2E test

```bash
# Public-only tests (no credentials required)
./scripts/test-sns-aws.sh

# Full authenticated tests — get a token first:
TOKEN=$(aws cognito-idp initiate-auth \
  --auth-flow USER_PASSWORD_AUTH \
  --client-id 1k41lqkds4oah55ns8iod30dv2 \
  --auth-parameters USERNAME=<your-email>,PASSWORD=<your-password> \
  --region ap-northeast-1 \
  --query 'AuthenticationResult.AccessToken' --output text)

./scripts/test-sns-aws.sh --token "$TOKEN" --verbose
```

**Reference**: [docs/AWS_SNS_FIX_REPORT.md](AWS_SNS_FIX_REPORT.md)

---

## [RB-10] Start the Local Development Environment

> **Host machine**: ARM (Apple Silicon M-series Mac)
> Run from inside the Dev Container.

```bash
cd /workspaces/ashnova/multicloud-auto-deploy

# Start infrastructure
docker compose up -d

# Verify startup
docker compose ps
curl http://localhost:8000/health

# Check logs
docker compose logs -f api
```

### Environment Variable Overrides (for debugging)

To point at a specific backend, create a `.env` file:

```bash
# Specify via services/api/.env or docker-compose env_file
CLOUD_PROVIDER=local
AUTH_DISABLED=true
API_BASE_URL=http://localhost:8000
```

### ARM Notes

- Local docker compose runs natively on **ARM** (no issues)
- Building packages for Lambda requires `--platform linux/amd64`
  → Normally handled by GitHub Actions (ubuntu-latest = x86_64)
- Same applies to GCP Cloud Function ZIP builds (handled automatically in CI)

---

## Next Section

→ [09 — Security](AI_AGENT_09_SECURITY.md)
