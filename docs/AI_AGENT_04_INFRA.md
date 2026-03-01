# 04 — Infrastructure (Pulumi)

> Part II — Architecture & Design | Parent: [AI_AGENT_GUIDE.md](AI_AGENT_GUIDE.md)

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

| Pulumi logical name       | AWS resource                     | Name pattern                         |
| ------------------------- | -------------------------------- | ------------------------------------ |
| `lambda-role`             | IAM Role                         | `{project}-{stack}-lambda-role`      |
| `app-secret`              | Secrets Manager Secret           | —                                    |
| `dynamodb-table`          | DynamoDB Table                   | `simple-sns-messages`                |
| `lambda-function`         | Lambda Function                  | `{project}-{stack}-api`              |
| `api-gateway`             | API Gateway v2                   | —                                    |
| `frontend-bucket`         | S3 Bucket                        | `{project}-{stack}-frontend`         |
| `landing-bucket`          | S3 Bucket                        | `{project}-{stack}-landing`          |
| `cloudfront-distribution` | CloudFront (PriceClass_200)      | —                                    |
| `security-headers-policy` | CloudFront ResponseHeadersPolicy | `{project}-{stack}-security-headers` |
| `cognito-user-pool`       | Cognito User Pool                | —                                    |
| `sns-topic`               | SNS Topic (alerts)               | —                                    |
| CloudWatch Alarms (multi) | CloudWatch                       | —                                    |

### Key config keys

```bash
pulumi config set aws:region ap-northeast-1
pulumi config set allowedOrigins "https://example.com"
pulumi config set alarmEmail your@email.com
pulumi config set staticSiteDomain "aws.example.com"        # custom domain (optional)
pulumi config set staticSiteAcmCertificateArn "arn:..."    # ACM certificate (optional)
```

> ⚠️ **CRITICAL for production stack**: Always set `customDomain` and `acmCertificateArn`
> before running `pulumi up --stack production`. If absent, CloudFront will revert to
> `CloudFrontDefaultCertificate: true`, breaking HTTPS for all visitors.
>
> ```bash
> pulumi config set customDomain www.aws.ashnova.jp --stack production
> pulumi config set acmCertificateArn \
>   arn:aws:acm:us-east-1:278280499340:certificate/914b86b1-4c10-4354-91cf-19c4460dcde5 \
>   --stack production
> ```
>
> The ACM certificate must be in `us-east-1` (required for CloudFront). Current cert expires 2027-03-12.

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
| `spa-rule-set`         | AFD RuleSet          | `SpaRuleSet`             |
| `spa-rewrite-rule`     | AFD Rule             | `SpaIndexHtmlRewrite`    |
| Action Groups + Alerts | Azure Monitor        | —                        |

> **SPA routing**: `SpaRuleSet` rewrites all non-static `/sns/*` requests to `/sns/index.html`
> so React client-side routing works on direct URL access and page refresh.
> RuleSet name must be **alphanumeric only** (no hyphens). Max 10 match_values per condition.

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

> **GCP-specific notes**:
>
> - `uploads-bucket` (`ashnova-{project}-{stack}-uploads`) has `allUsers:objectViewer` — public.
>   Do NOT grant public read on the `frontend-bucket`.
> - `ManagedSslCertificate` uses `ignore_changes=["name", "managed"]` to prevent Pulumi from
>   attempting to replace the cert when the name hash changes (GCP returns 400 if the cert is
>   still attached to the HTTPS proxy).
> - If `pulumi up` fails with `Error 412: Invalid fingerprint` on URLMap, add a
>   `pulumi refresh --yes --skip-preview` step before `pulumi up`.
> - Firebase authorized domains must be updated via Identity Toolkit Admin v2 API (requires
>   `x-goog-user-project` header). This is automated in `deploy-gcp.yml`.

### GCS resource conflict (Error 409 / Error 412)

```bash
# Error 409: bucket already exists (state out of sync)
# Fix: import existing bucket into Pulumi state before pulumi up
pulumi import gcp:storage/bucket:Bucket uploads-bucket \
  ashnova-multicloud-auto-deploy-staging-uploads --stack staging

# Error 412: Invalid fingerprint on URLMap (Pulumi state stale)
# Fix: add pulumi refresh before pulumi up
pulumi refresh --yes --skip-preview --stack staging
pulumi up --yes --stack staging
```

### Azure CLI authentication error

```bash
# Set Service Principal credentials explicitly
export AZURE_CLIENT_ID=$(echo $AZURE_CREDENTIALS | jq -r '.clientId')
export AZURE_CLIENT_SECRET=$(echo $AZURE_CREDENTIALS | jq -r '.clientSecret')
export AZURE_SUBSCRIPTION_ID=$(echo $AZURE_CREDENTIALS | jq -r '.subscriptionId')
export AZURE_TENANT_ID=$(echo $AZURE_CREDENTIALS | jq -r '.tenantId')
```

### Azure Pulumi pending operations

```bash
# Error: "Stack has pending operation"
pulumi stack export | \
  python3 -c "import sys,json; d=json.load(sys.stdin); d['deployment']['pending_operations']=[]; print(json.dumps(d))" | \
  pulumi stack import --force
```

---

## Lambda Layer Configuration

Two options (see `LAMBDA_LAYER_OPTIMIZATION.md` for full details):

**Option A — Klayers (default, recommended)**:
No build required. Uses public community-managed Lambda Layers. Enable in Pulumi config:

```bash
pulumi config set use_klayers true
```

**Option B — Custom Layer** (full control, specific versions):
Build with `./scripts/build-lambda-layer.sh` (excludes boto3 / Azure / GCP SDKs from the ZIP).

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
  --compatible-runtimes python3.13 \
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

→ [05 — CI/CD Pipelines](AI_AGENT_05_CICD.md)
