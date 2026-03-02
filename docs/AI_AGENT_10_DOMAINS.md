# 10 — Custom Domains & Testing

> Part III — Operations | Parent: [AI_AGENT_GUIDE.md](AI_AGENT_GUIDE.md)

---

## Custom Domain Status (all confirmed 2026-02-21)

| Cloud     | Custom Domain          | CDN Target                                                | DNS Type | Status          |
| --------- | ---------------------- | --------------------------------------------------------- | -------- | --------------- |
| **AWS**   | `www.aws.ashnova.jp`   | `d1qob7569mn5nw.cloudfront.net`                           | CNAME    | ✅ HTTPS active |
| **Azure** | `www.azure.ashnova.jp` | `mcad-production-diev0w-f9ekdmehb0bga5aw.z01.azurefd.net` | CNAME    | ✅ HTTPS active |
| **GCP**   | `www.gcp.ashnova.jp`   | `34.8.38.222` (A record)                                  | A        | ✅ HTTPS active |

### Staging CDN endpoints (no custom domain)

| Cloud     | CDN / Front Door URL                                   | Distribution ID     |
| --------- | ------------------------------------------------------ | ------------------- |
| **AWS**   | `d1tf3uumcm4bo1.cloudfront.net`                        | E1TBH4R432SZBZ      |
| **Azure** | `mcad-staging-d45ihd-dseygrc9c3a3htgj.z01.azurefd.net` | mcad-staging-d45ihd |
| **GCP**   | `34.117.111.182` (IP)                                  | —                   |

---

## ⚠️ Critical: Pulumi Config Before Re-running

If `pulumi up` for production AWS is run WITHOUT setting these config values, CloudFront will revert to its default certificate (breaking HTTPS):

```bash
cd infrastructure/pulumi/aws
pulumi config set customDomain www.aws.ashnova.jp --stack production
pulumi config set acmCertificateArn arn:aws:acm:us-east-1:278280499340:certificate/914b86b1-4c10-4354-91cf-19c4460dcde5 --stack production
```

ACM certificate expires: **2027-03-12**

---

## DNS Records (confirmed)

### AWS

```
CNAME  www.aws.ashnova.jp  →  d1qob7569mn5nw.cloudfront.net
CNAME  _<id>.www.aws.ashnova.jp  →  _<id>.acm-validations.aws.  (ACM validation)
```

### Azure

```
CNAME  www.azure.ashnova.jp  →  mcad-production-diev0w-f9ekdmehb0bga5aw.z01.azurefd.net
TXT    _dnsauth.www.azure.ashnova.jp  →  <validationToken>  (AFD validation)
```

### GCP

```
A  www.gcp.ashnova.jp  →  34.8.38.222  (production)
A  staging.gcp.ashnova.jp  →  34.117.111.182  (staging)
```

---

## Re-Setup Procedure (if domains need to be reconfigured)

### AWS

```bash
# 1. Confirm / request ACM certificate (us-east-1 only)
aws acm list-certificates --region us-east-1 \
  --query "CertificateSummaryList[?DomainName=='www.aws.ashnova.jp'].CertificateArn" \
  --output text

# 2. Set Pulumi config
cd infrastructure/pulumi/aws
pulumi config set customDomain www.aws.ashnova.jp --stack production
pulumi config set acmCertificateArn <CERT_ARN> --stack production
pulumi up --stack production
```

### Azure

```bash
RESOURCE_GROUP="multicloud-auto-deploy-production-rg"
PROFILE_NAME="multicloud-auto-deploy-production-fd"

# Create custom domain (idempotent)
az afd custom-domain create \
  --resource-group $RESOURCE_GROUP \
  --profile-name $PROFILE_NAME \
  --custom-domain-name azure-ashnova-jp \
  --host-name www.azure.ashnova.jp \
  --certificate-type ManagedCertificate

# Check validation status
az afd custom-domain show \
  --resource-group $RESOURCE_GROUP \
  --profile-name $PROFILE_NAME \
  --custom-domain-name azure-ashnova-jp \
  --query "{provisioningState,domainValidationState}"
```

### GCP

```bash
cd infrastructure/pulumi/gcp
pulumi config set customDomain www.gcp.ashnova.jp --stack production
pulumi up --stack production
# Note: Managed SSL cert provisioning can take up to 60 minutes after DNS propagates
```

---

## CORS After Domain Change

Always update CORS when domains change:

```bash
# AWS
cd infrastructure/pulumi/aws
pulumi config set allowedOrigins "https://www.aws.ashnova.jp,http://localhost:5173" --stack production
pulumi up --stack production

# GCP
cd infrastructure/pulumi/gcp
pulumi config set allowedOrigins "https://www.gcp.ashnova.jp,http://localhost:5173" --stack production
pulumi up --stack production

# Azure — Azure Function App CORS must be set via CLI (not Pulumi)
az functionapp cors add \
  --resource-group multicloud-auto-deploy-production-rg \
  --name multicloud-auto-deploy-production-func \
  --allowed-origins "https://www.azure.ashnova.jp"
```

---

## Verification

```bash
# HTTPS check
curl -sI https://www.aws.ashnova.jp   | head -3
curl -sI https://www.azure.ashnova.jp | head -3
curl -sI https://www.gcp.ashnova.jp   | head -3

# API health check
curl -s https://www.aws.ashnova.jp/health
curl -s https://www.gcp.ashnova.jp/health

# DNS resolution
dig www.aws.ashnova.jp
dig www.azure.ashnova.jp
dig www.gcp.ashnova.jp
```

---

## Testing All Environments

### Quick connectivity check (~30s, no auth required)

```bash
./scripts/test-staging-all.sh --quick
```

Checks per cloud: landing page `/` → 200, SNS app `/sns/` → 200, API `/health` → 200.

### Full authenticated test (all 3 clouds)

```bash
./scripts/test-staging-all.sh \
  --aws-token   "$AWS_TOKEN" \
  --azure-token "$AZURE_TOKEN" \
  --gcp-token   "$GCP_TOKEN"
```

### Obtaining auth tokens

#### AWS — Cognito

```bash
AWS_TOKEN=$(aws cognito-idp initiate-auth \
  --auth-flow USER_PASSWORD_AUTH \
  --client-id 1k41lqkds4oah55ns8iod30dv2 \
  --auth-parameters USERNAME=YOUR_EMAIL,PASSWORD=YOUR_PASSWORD \
  --region ap-northeast-1 \
  --query 'AuthenticationResult.AccessToken' \
  --output text)
```

#### GCP — Firebase

```bash
GCP_TOKEN=$(gcloud auth print-identity-token)
```

#### Azure — Azure AD (browser only)

```
1. Open https://mcad-staging-d45ihd-dseygrc9c3a3htgj.z01.azurefd.net/sns/
2. Log in with Microsoft account
3. DevTools → Application → Local Storage → origin → id_token
AZURE_TOKEN="<paste id_token here>"
```

### Per-cloud test scripts

| Script                          | Purpose                                        |
| ------------------------------- | ---------------------------------------------- |
| `scripts/test-staging-all.sh`   | ⭐ Orchestrates all 3 clouds                   |
| `scripts/test-landing-pages.sh` | Landing page tests only                        |
| `scripts/test-sns-aws.sh`       | Full AWS suite (authenticated)                 |
| `scripts/test-sns-azure.sh`     | Full Azure suite (authenticated)               |
| `scripts/test-sns-gcp.sh`       | Full GCP suite (authenticated)                 |
| `scripts/test-sns-all.sh`       | All-cloud E2E with binary PUT + imageUrl check |
| `scripts/test-e2e.sh`           | Lightweight multi-cloud smoke test             |

### pytest Integration Tests (unit/integration, mocked)

```bash
# All tests
cd services/api && pytest tests/

# By cloud backend
pytest tests/ -m aws
pytest tests/ -m gcp
pytest tests/ -m azure

# Via shell script
./scripts/run-integration-tests.sh        # standard
./scripts/run-integration-tests.sh -v     # verbose
./scripts/run-integration-tests.sh --coverage  # with coverage report
```

Test coverage includes CRUD operations, permission checks, pagination, tag filtering, and profile update for all 3 backends.

---

## Next Section

→ [00 — Critical Rules](AI_AGENT_00_CRITICAL_RULES.md) (cycle back) | [07 — Runbooks](AI_AGENT_07_RUNBOOKS.md)
