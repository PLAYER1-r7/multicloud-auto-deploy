# 05 — Infrastructure (Pulumi)

> Parent: [AI_AGENT_GUIDE.md](AI_AGENT_GUIDE.md)

---

## Pulumi Overview

| Field     | Value                                               |
| --------- | --------------------------------------------------- |
| IaC tool  | Pulumi Python SDK 3.x                               |
| State     | Pulumi Cloud (remote state)                         |
| Stacks    | `staging` / `production`                            |
| Language  | Python                                              |
| Code path | `infrastructure/pulumi/{aws,azure,gcp}/__main__.py` |

---

## Common Operations

```bash
# List stacks
pulumi stack ls

# Deploy
pulumi up --stack staging

# Show outputs
pulumi stack output

# Preview changes (dry run)
pulumi preview --stack staging

# Destroy resources (be careful)
pulumi destroy --stack staging
```

---

## AWS Pulumi Stack

**Directory**: `infrastructure/pulumi/aws/`

### Resources created

| Pulumi logical name       | AWS resource           | Name pattern                    |
| ------------------------- | ---------------------- | ------------------------------- |
| `lambda-role`             | IAM Role               | `{project}-{stack}-lambda-role` |
| `app-secret`              | Secrets Manager Secret | —                               |
| `dynamodb-table`          | DynamoDB Table         | `simple-sns-messages`           |
| `lambda-function`         | Lambda Function        | `{project}-{stack}-api`         |
| `api-gateway`             | API Gateway v2         | —                               |
| `frontend-bucket`         | S3 Bucket              | `{project}-{stack}-frontend`    |
| `landing-bucket`          | S3 Bucket              | `{project}-{stack}-landing`     |
| `cloudfront-distribution` | CloudFront             | —                               |
| `cognito-user-pool`       | Cognito User Pool      | —                               |
| `sns-topic`               | SNS Topic (alerts)     | —                               |
| CloudWatch Alarms (multi) | CloudWatch             | —                               |

### Key config keys

```bash
pulumi config set aws:region ap-northeast-1
pulumi config set allowedOrigins "https://example.com"
pulumi config set alarmEmail your@email.com
pulumi config set staticSiteDomain "aws.example.com"        # custom domain (optional)
pulumi config set staticSiteAcmCertificateArn "arn:..."    # ACM certificate (optional)
```

### Key outputs

```bash
pulumi stack output api_url                     # API Gateway URL
pulumi stack output cloudfront_url              # CloudFront URL
pulumi stack output cloudfront_distribution_id  # CloudFront Distribution ID
pulumi stack output frontend_bucket_name        # S3 bucket name
pulumi stack output lambda_function_name        # Lambda function name
pulumi stack output cognito_user_pool_id
pulumi stack output cognito_client_id
```

---

## Azure Pulumi Stack

**Directory**: `infrastructure/pulumi/azure/`

### Resources created

| Pulumi logical name    | Azure resource       | Name pattern             |
| ---------------------- | -------------------- | ------------------------ |
| `resource-group`       | Resource Group       | `{project}-{stack}-rg`   |
| `functions-storage`    | Storage Account      | `mcadfunc{suffix}`       |
| `frontend-storage`     | Storage Account      | `mcadweb{suffix}`        |
| `landing-storage`      | Storage Account      | `mcadlanding{suffix}`    |
| `function-app`         | Azure Functions      | `{project}-{stack}-func` |
| `cosmos-account`       | Cosmos DB Account    | —                        |
| `frontdoor-profile`    | Front Door Profile   | `{project}-{stack}-fd`   |
| `azure-ad-app`         | Azure AD Application | —                        |
| Action Groups + Alerts | Azure Monitor        | —                        |

### Key config keys

```bash
pulumi config set azure-native:location japaneast
pulumi config set environment staging
pulumi config set alarmEmail your@email.com
pulumi config set staticSiteDomain "azure.example.com"  # optional
```

### Key outputs

```bash
pulumi stack output api_url
pulumi stack output frontdoor_url
pulumi stack output frontend_storage_name
pulumi stack output azure_ad_tenant_id
pulumi stack output azure_ad_client_id
```

---

## GCP Pulumi Stack

**Directory**: `infrastructure/pulumi/gcp/`

### Resources created

| Pulumi logical name    | GCP resource           | Name                                 |
| ---------------------- | ---------------------- | ------------------------------------ |
| `frontend-bucket`      | GCS Bucket             | `ashnova-{project}-{stack}-frontend` |
| `uploads-bucket`       | GCS Bucket             | `ashnova-{project}-{stack}-uploads`  |
| `backend-bucket`       | Compute Backend Bucket | `{project}-{stack}-cdn-backend`      |
| `cdn-ip-address`       | Global External IP     | `{project}-{stack}-cdn-ip`           |
| `url-map`              | URL Map                | —                                    |
| `cloud-run-service`    | Cloud Run              | `{project}-{stack}-api`              |
| `firestore-db`         | Firestore              | (default)                            |
| `managed-ssl-cert`     | SSL Certificate        | optional                             |
| Alert Policies (multi) | Cloud Monitoring       | —                                    |

### Key config keys

```bash
pulumi config set gcp:project ashnova
pulumi config set environment staging
pulumi config set alarmEmail your@email.com
pulumi config set staticSiteDomain "gcp.example.com"  # optional
pulumi config set monthlyBudgetUsd 50                 # production only
```

### Key outputs

```bash
pulumi stack output api_url
pulumi stack output cdn_url
pulumi stack output cdn_ip_address
pulumi stack output frontend_bucket_name
```

---

## Pulumi State Troubleshooting

### GCS resource conflict (Error 409)

```bash
# Cause: local state reset by GitHub Actions causes re-creation of existing resources
# Fix: use Pulumi Cloud remote state (current configuration)
pulumi login  # log in to Pulumi Cloud
```

### Azure CLI authentication error

```bash
# Set Service Principal credentials explicitly
export AZURE_CLIENT_ID=$(echo $AZURE_CREDENTIALS | jq -r '.clientId')
export AZURE_CLIENT_SECRET=$(echo $AZURE_CREDENTIALS | jq -r '.clientSecret')
export AZURE_SUBSCRIPTION_ID=$(echo $AZURE_CREDENTIALS | jq -r '.subscriptionId')
export AZURE_TENANT_ID=$(echo $AZURE_CREDENTIALS | jq -r '.tenantId')
```

---

## Lambda Layer Build Steps

```bash
# 1. Build layer (deps only; boto3 excluded)
./scripts/build-lambda-layer.sh
# → generates services/api/lambda-layer.zip

# 2. Publish layer
aws lambda publish-layer-version \
  --layer-name multicloud-auto-deploy-staging-dependencies \
  --zip-file fileb://services/api/lambda-layer.zip \
  --compatible-runtimes python3.12 \
  --region ap-northeast-1

# 3. Package app code only (~78 KB)
cd services/api
cp -r app .build/package/
cp index.py .build/package/
cd .build/package && zip -r ../../lambda.zip .

# 4. Update Lambda (direct ZIP upload, no S3 needed)
aws lambda update-function-code \
  --function-name multicloud-auto-deploy-staging-api \
  --zip-file fileb://lambda.zip
```

---

## Next Section

→ [06 — CI/CD Pipelines](AI_AGENT_06_CICD.md)
