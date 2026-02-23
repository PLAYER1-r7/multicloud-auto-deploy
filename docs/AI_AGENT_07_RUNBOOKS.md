# 07 — Runbooks

> Part III — Operations | Parent: [AI_AGENT_GUIDE.md](AI_AGENT_GUIDE.md)  
> Step-by-step procedures for common tasks and incident response

---

## [RB-01] Manually Update a Lambda Function

```bash
# 1. Package app code only (ZIP)
cd /workspaces/multicloud-auto-deploy/services/api
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
cd /workspaces/multicloud-auto-deploy/services/frontend_react
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
aws s3 sync /workspaces/multicloud-auto-deploy/static-site/ \
  s3://multicloud-auto-deploy-staging-frontend/ \
  --delete --region ap-northeast-1

aws cloudfront create-invalidation \
  --distribution-id E1TBH4R432SZBZ \
  --paths "/*"
```

---

## [RB-05] Manually deploy Azure Functions

```bash
cd /workspaces/multicloud-auto-deploy/services/api

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
cd /workspaces/multicloud-auto-deploy/services/api

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
cd /workspaces/multicloud-auto-deploy/infrastructure/pulumi/aws
pulumi login
pulumi stack select staging
pulumi up --yes

# Azure
cd /workspaces/multicloud-auto-deploy/infrastructure/pulumi/azure
pulumi stack select staging
pulumi up --yes

# GCP
cd /workspaces/multicloud-auto-deploy/infrastructure/pulumi/gcp
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
cd /workspaces/multicloud-auto-deploy/services/api

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
cd /workspaces/multicloud-auto-deploy

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

## [RB-13] Rebuild and Hotfix-Deploy GCP Cloud Function (linux/amd64)

The dev container is `aarch64`; Cloud Functions runs `linux/amd64`. Always use Docker.

```bash
# 1. Build linux/amd64 packages
mkdir -p /tmp/deploy_gcp/.deployment
docker run --rm --platform linux/amd64 \
  -v /tmp/deploy_gcp:/out \
  python:3.12-slim \
  bash -c "pip install --no-cache-dir --target /out/.deployment \
           -r /workspaces/multicloud-auto-deploy/services/api/requirements-gcp.txt -q"

# 2. Copy application code
cp -r /workspaces/multicloud-auto-deploy/services/api/app /tmp/deploy_gcp/.deployment/
# Cloud Build requires main.py even when --entry-point is specified
cp /workspaces/multicloud-auto-deploy/services/api/function.py /tmp/deploy_gcp/.deployment/main.py
cp /workspaces/multicloud-auto-deploy/services/api/function.py /tmp/deploy_gcp/.deployment/function.py

# 3. Create ZIP (exclude __pycache__)
cd /tmp/deploy_gcp/.deployment
find . -name "__pycache__" -path "*/app/*" -exec rm -rf {} + 2>/dev/null || true
zip -r9q /tmp/deploy_gcp/function-source.zip .
cd /workspaces/multicloud-auto-deploy

# 4. Upload to GCS (clear stale tracker files first if resuming)
rm -f ~/.config/gcloud/surface_data/storage/tracker_files/*
gcloud storage cp /tmp/deploy_gcp/function-source.zip \
  gs://ashnova-multicloud-auto-deploy-staging-function-source/function-source.zip

# 5. Deploy
gcloud functions deploy multicloud-auto-deploy-staging-api \
  --gen2 --region=asia-northeast1 --runtime=python312 \
  --source=gs://ashnova-multicloud-auto-deploy-staging-function-source/function-source.zip \
  --entry-point=handler --project=ashnova --quiet
```

**Key rules**:

- `main.py` MUST exist in the ZIP — Cloud Build rejects source without it even when `--entry-point` names another function.
- Always verify syntax before packaging: `python3 -m py_compile services/api/app/backends/local_backend.py && echo OK`
- `gcloud run services update --update-env-vars` cannot be used for URL values (`:` causes parse errors). Use `--env-vars-file` instead.

---

## [RB-14] Fix Azure Front Door 502 (Dynamic Consumption → FC1 FlexConsumption)

Dynamic Consumption (Y1) Function Apps are periodically recycled. AFD Standard cannot
detect the TCP disconnect, leaving stale connections in its pool that return 502 instantly.
The fix is to migrate to **FC1 FlexConsumption** with a fixed single instance.

```bash
RG="multicloud-auto-deploy-production-rg"
FD="multicloud-auto-deploy-production-fd"
EP="mcad-production-diev0w"
OG="multicloud-auto-deploy-production-frontend-web-origin-group"
ORIGIN="multicloud-auto-deploy-production-frontend-web-origin"

# 1. Create FC1 FlexConsumption Function App
az functionapp create \
  --name multicloud-auto-deploy-production-frontend-web-v2 \
  --resource-group "$RG" \
  --flexconsumption-location japaneast \
  --runtime python --runtime-version 3.12 \
  --storage-account mcadfuncdiev0w

# 2. Fix instance count to 1 (no recycling)
az functionapp scale config set \
  --name multicloud-auto-deploy-production-frontend-web-v2 \
  --resource-group "$RG" \
  --maximum-instance-count 1
az functionapp scale config always-ready set \
  --name multicloud-auto-deploy-production-frontend-web-v2 \
  --resource-group "$RG" \
  --settings "http=1"

# 3. Deploy x86_64 ZIP (build with Docker --platform linux/amd64 first)
az functionapp deployment source config-zip \
  --name multicloud-auto-deploy-production-frontend-web-v2 \
  --resource-group "$RG" \
  --src services/frontend_web/frontend-web-prod.zip

# 4. Update AFD origin to point to new Function App
az afd origin update \
  --resource-group "$RG" \
  --profile-name "$FD" \
  --origin-group-name "$OG" \
  --origin-name "$ORIGIN" \
  --host-name multicloud-auto-deploy-production-frontend-web-v2.azurewebsites.net \
  --origin-host-header multicloud-auto-deploy-production-frontend-web-v2.azurewebsites.net

# 5. Stop old Y1 app (wait ~5 min for AFD edge propagation)
az functionapp stop \
  --name multicloud-auto-deploy-production-frontend-web \
  --resource-group "$RG"
```

**Critical notes**:

- `--consumption-plan-location` creates Y1 Dynamic (wrong). Always use `--flexconsumption-location` for FC1.
- `az functionapp update --plan` does NOT support Linux→Linux plan migration; create a new app instead.
- AFD origin updates take up to 5 minutes for full edge propagation.
- `SCM_DO_BUILD_DURING_DEPLOYMENT` causes `InvalidAppSettingsException` on Flex Consumption — never set it.

---

## [RB-15] Fix AWS CloudFront HTTPS Certificate Error (ERR_CERT_COMMON_NAME_INVALID)

If `pulumi up --stack production` was run without `customDomain` / `acmCertificateArn` set,
CloudFront reverts to `CloudFrontDefaultCertificate: true`, breaking HTTPS for the custom domain.

```bash
# 1. Retrieve current distribution config and ETag
aws cloudfront get-distribution-config --id E214XONKTXJEJD > /tmp/cf-config.json
# Note the ETag from the response (e.g. E13V1IB3VIYZZH)

# 2. Patch the JSON (Python one-liner)
python3 - <<'EOF'
import json
with open('/tmp/cf-config.json') as f:
    data = json.load(f)
cfg = data['DistributionConfig']
cfg['Aliases'] = {'Quantity': 1, 'Items': ['www.aws.ashnova.jp']}
cfg['ViewerCertificate'] = {
    'ACMCertificateArn': 'arn:aws:acm:us-east-1:278280499340:certificate/914b86b1-4c10-4354-91cf-19c4460dcde5',
    'SSLSupportMethod': 'sni-only',
    'MinimumProtocolVersion': 'TLSv1.2_2021',
    'CertificateSource': 'acm'
}
with open('/tmp/cf-config-updated.json', 'w') as f:
    json.dump(cfg, f, indent=2)
print('Done')
EOF

# 3. Apply update (replace <ETAG> with value from step 1)
aws cloudfront update-distribution \
  --id E214XONKTXJEJD \
  --distribution-config file:///tmp/cf-config-updated.json \
  --if-match <ETAG>

# 4. Wait for propagation and verify
aws cloudfront wait distribution-deployed --id E214XONKTXJEJD
curl -sI https://www.aws.ashnova.jp | head -3
```

**Prevention** — always set these before `pulumi up --stack production`:

```bash
cd infrastructure/pulumi/aws
pulumi config set customDomain www.aws.ashnova.jp --stack production
pulumi config set acmCertificateArn \
  arn:aws:acm:us-east-1:278280499340:certificate/914b86b1-4c10-4354-91cf-19c4460dcde5 \
  --stack production
```

**ACM certificate** (production): ARN `914b86b1` — domain `www.aws.ashnova.jp`, expires 2027-03-12.

---

## Next Section

→ [08 — Security](AI_AGENT_08_SECURITY.md)
