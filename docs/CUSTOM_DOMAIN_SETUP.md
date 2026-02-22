# Custom Domain Configuration Guide

Steps for configuring custom domains when using different domains per cloud.

---

## ✅ Production Custom Domains — Configuration Complete (2026-02-21)

> **All 3 cloud custom domains are operational.**

| Cloud     | Custom Domain          | Target Endpoint                                           | Status                                         |
| --------- | ---------------------- | --------------------------------------------------------- | ---------------------------------------------- |
| **AWS**   | `www.aws.ashnova.jp`   | `d1qob7569mn5nw.cloudfront.net`                           | ✅ HTTPS active (directly fixed 2026-02-21)    |
| **Azure** | `www.azure.ashnova.jp` | `mcad-production-diev0w-f9ekdmehb0bga5aw.z01.azurefd.net` | ✅ HTTPS active ⚠️ /sns/\* needs investigation |
| **GCP**   | `www.gcp.ashnova.jp`   | `34.8.38.222` (A record)                                  | ✅ HTTPS active                                |

### Verified Endpoints

```bash
# Landing pages
curl -I https://www.aws.ashnova.jp        # 200 OK
curl -I https://www.azure.ashnova.jp      # 200 OK
curl -I https://www.gcp.ashnova.jp        # 200 OK

# SNS app
curl https://www.aws.ashnova.jp/health    # 200 {"status":"healthy"}
curl https://www.gcp.ashnova.jp/health    # 200 {"status":"healthy"}
# ⚠️ Azure: /sns/* intermittent 502 → AFD under investigation (see AZURE_SNS_FIX_REPORT.md)
```

### Configuration Completion Checklist (Production)

**AWS**

- [x] ACM certificate `ISSUED` confirmed → `arn:aws:acm:us-east-1:278280499340:certificate/914b86b1-4c10-4354-91cf-19c4460dcde5` (expires 2027-03-12)
- [x] DNS: CNAME `www.aws.ashnova.jp` → `d1qob7569mn5nw.cloudfront.net` configured
- [x] CloudFront `E214XONKTXJEJD` alias + ACM certificate set directly (fixed via AWS CLI on 2026-02-21)
  - Issue: `pulumi up` did not apply alias/certificate (remained on CloudFrontDefaultCertificate)
  - Fix: Set alias `www.aws.ashnova.jp` + cert `914b86b1` via `aws cloudfront update-distribution`
- [!] **Note before re-running Pulumi**: Must set `pulumi config set customDomain www.aws.ashnova.jp --stack production` and `pulumi config set acmCertificateArn arn:aws:acm:us-east-1:278280499340:certificate/914b86b1-4c10-4354-91cf-19c4460dcde5 --stack production`
- [x] CORS updated

**Azure**

- [x] `az afd custom-domain create` executed (`azure-ashnova-jp`)
- [x] Custom domain attached to both routes
- [x] DNS: TXT record `_dnsauth.www.azure.ashnova.jp` configured (verified)
- [x] DNS: CNAME `www.azure.ashnova.jp` → `mcad-production-diev0w-f9ekdmehb0bga5aw.z01.azurefd.net` configured
- [x] Managed Certificate issued, HTTPS active
- [⚠️] `/sns/*` intermittent 502 issue → under investigation (see [AZURE_SNS_FIX_REPORT.md](AZURE_SNS_FIX_REPORT.md))

**GCP**

- [x] Pulumi config set (`customDomain: www.gcp.ashnova.jp`)
- [x] `pulumi up --stack production` completed
- [x] DNS: A record `www.gcp.ashnova.jp` → `34.8.38.222` configured
- [x] Managed SSL certificate `ACTIVE` confirmed

---

## 🎯 Production Custom Domain Setup (Setup Procedure)

### Target Domains

| Cloud     | Custom Domain          | Target Endpoint                                           |
| --------- | ---------------------- | --------------------------------------------------------- |
| **AWS**   | `www.aws.ashnova.jp`   | `d1qob7569mn5nw.cloudfront.net`                           |
| **Azure** | `www.azure.ashnova.jp` | `mcad-production-diev0w-f9ekdmehb0bga5aw.z01.azurefd.net` |
| **GCP**   | `www.gcp.ashnova.jp`   | `34.8.38.222` (A record)                                  |

---

## 📋 Current Endpoints

### Staging Environment

| Cloud     | Type       | Current Endpoint                                       | Distribution ID     |
| --------- | ---------- | ------------------------------------------------------ | ------------------- |
| **AWS**   | CloudFront | `d1tf3uumcm4bo1.cloudfront.net`                        | E1TBH4R432SZBZ      |
| **Azure** | Front Door | `mcad-staging-d45ihd-dseygrc9c3a3htgj.z01.azurefd.net` | mcad-staging-d45ihd |
| **GCP**   | Cloud CDN  | `34.117.111.182` (IP address)                          | -                   |

### Production Environment

| Cloud     | Type       | Current Endpoint                                          | Distribution ID        |
| --------- | ---------- | --------------------------------------------------------- | ---------------------- |
| **AWS**   | CloudFront | `d1qob7569mn5nw.cloudfront.net`                           | E214XONKTXJEJD         |
| **Azure** | Front Door | `mcad-production-diev0w-f9ekdmehb0bga5aw.z01.azurefd.net` | mcad-production-diev0w |
| **GCP**   | Cloud CDN  | `34.8.38.222` (IP address)                                | -                      |

---

## 🌐 Domains Used (ashnova.jp)

Custom domains configured for this project:

- **AWS**: `www.aws.ashnova.jp`
- **Azure**: `www.azure.ashnova.jp`
- **GCP**: `www.gcp.ashnova.jp`

> Note: Generic procedures use placeholders such as `aws.yourdomain.com`. In practice, use the ashnova.jp domains above.

---

## 1️⃣ AWS CloudFront Custom Domain Setup

### Prerequisites

- Domain ownership verified
- AWS Route 53 (recommended) or external DNS provider

### Steps

#### Step 1: Create ACM Certificate (us-east-1 region required)

```bash
# Request ACM certificate
aws acm request-certificate \
  --domain-name www.aws.ashnova.jp \
  --validation-method DNS \
  --region us-east-1

# Get certificate ARN
CERT_ARN=$(aws acm list-certificates \
  --region us-east-1 \
  --query "CertificateSummaryList[?DomainName=='www.aws.ashnova.jp'].CertificateArn" \
  --output text)

echo "Certificate ARN: $CERT_ARN"
```

#### Step 2: Add DNS Validation Record

```bash
# Get validation record info
aws acm describe-certificate \
  --certificate-arn $CERT_ARN \
  --region us-east-1 \
  --query 'Certificate.DomainValidationOptions[0].ResourceRecord'

# Example output:
# {
#   "Name": "_abc123.aws.yourdomain.com",
#   "Type": "CNAME",
#   "Value": "_xyz456.acm-validations.aws."
# }
```

**Configure in your DNS provider**:

- Record type: `CNAME`
- Name: `_abc123.www.aws.ashnova.jp`
- Value: `_xyz456.acm-validations.aws.`

#### Step 3: Update Pulumi Configuration

Modify the CloudFront Distribution section in `infrastructure/pulumi/aws/__main__.py`:

```python
# Set certificate ARN
cert_arn = config.get("acmCertificateArn")  # Retrieved from Pulumi config
custom_domain = config.get("customDomain")  # e.g. aws.yourdomain.com

cloudfront_kwargs = {
    # ... existing config ...
    "aliases": [custom_domain] if custom_domain else [],
    "viewer_certificate": aws.cloudfront.DistributionViewerCertificateArgs(
        acm_certificate_arn=cert_arn,
        ssl_support_method="sni-only",
        minimum_protocol_version="TLSv1.2_2021",
    ) if cert_arn else aws.cloudfront.DistributionViewerCertificateArgs(
        cloudfront_default_certificate=True,
    ),
    # ... remaining config ...
}
```

#### Step 4: Add Pulumi Configuration

```bash
cd infrastructure/pulumi/aws
pulumi config set customDomain www.aws.ashnova.jp --stack production
pulumi config set acmCertificateArn arn:aws:acm:us-east-1:ACCOUNT_ID:certificate/CERT_ID --stack production
pulumi up --stack production
```

#### Step 5: Add CNAME Record to DNS

**Verify the CloudFront domain for your Pulumi environment (production/staging)**:

```bash
cd infrastructure/pulumi/aws
pulumi stack select production  # or staging
CLOUDFRONT_DOMAIN=$(pulumi stack output cloudfront_domain)
echo "CloudFront Domain: $CLOUDFRONT_DOMAIN"
```

**For Route 53**:

```bash
# production environment
aws route53 change-resource-record-sets \
  --hosted-zone-id YOUR_ZONE_ID \
  --change-batch '{
    "Changes": [{
      "Action": "CREATE",
      "ResourceRecordSet": {
        "Name": "www.aws.ashnova.jp",
        "Type": "CNAME",
        "TTL": 300,
        "ResourceRecords": [{"Value": "d1qob7569mn5nw.cloudfront.net"}]
      }
    }]
  }'
```

**For external DNS providers**:

- Record type: `CNAME`
- Name: `www.aws.ashnova.jp`
- Value:
  - Production: `d1qob7569mn5nw.cloudfront.net`
  - Staging: `d1tf3uumcm4bo1.cloudfront.net`

---

## 2️⃣ Azure Front Door Custom Domain Setup

### Prerequisites

- Domain ownership verified
- Azure DNS (recommended) or external DNS provider

### Steps

#### Step 1: Add Custom Domain

**Retrieve environment resource info**:

```bash
# Check Pulumi outputs
cd infrastructure/pulumi/azure
pulumi stack select production  # or staging
FRONTDOOR_HOSTNAME=$(pulumi stack output frontdoor_hostname)
FRONTDOOR_PROFILE=$(pulumi stack output frontdoor_profile_name)
FRONTDOOR_ENDPOINT=$(pulumi stack output frontdoor_endpoint_name)
RESOURCE_GROUP=$(pulumi stack output resource_group_name)

echo "Front Door Hostname: $FRONTDOOR_HOSTNAME"
echo "Profile Name: $FRONTDOOR_PROFILE"
```

**Create custom domain**:

```bash
# Environment: production
ENVIRONMENT="production"
RESOURCE_GROUP="multicloud-auto-deploy-${ENVIRONMENT}-rg"
PROFILE_NAME="multicloud-auto-deploy-${ENVIRONMENT}-fd"
CUSTOM_DOMAIN_NAME="azure-ashnova-jp"
HOSTNAME="www.azure.ashnova.jp"

# Create custom domain
az afd custom-domain create \
  --resource-group $RESOURCE_GROUP \
  --profile-name $PROFILE_NAME \
  --custom-domain-name $CUSTOM_DOMAIN_NAME \
  --host-name $HOSTNAME \
  --certificate-type ManagedCertificate
```

#### Step 2: Add DNS Validation Record

```bash
# Get validation record info
az afd custom-domain show \
  --resource-group $RESOURCE_GROUP \
  --profile-name $PROFILE_NAME \
  --custom-domain-name $CUSTOM_DOMAIN_NAME \
  --query "validationProperties"

# Example output:
# {
#   "validationToken": "abc123def456",
#   "expirationDate": "2026-02-24T..."
# }
```

**Configure in your DNS provider**:

- Record type: `TXT`
- Name: `_dnsauth.www.azure.ashnova.jp`
- Value: `abc123def456` (validationToken)

#### Step 3: Associate with Endpoint

```bash
# Get Endpoint name (differs between production/staging)
ENDPOINT_NAME=$(pulumi stack output frontdoor_endpoint_name)
echo "Endpoint Name: $ENDPOINT_NAME"

# Associate custom domain with endpoint
az afd route create \
  --resource-group $RESOURCE_GROUP \
  --profile-name $PROFILE_NAME \
  --endpoint-name $ENDPOINT_NAME \
  --route-name custom-domain-route \
  --origin-group-name default-origin-group \
  --supported-protocols Https \
  --custom-domains $CUSTOM_DOMAIN_NAME \
  --forwarding-protocol HttpsOnly \
  --https-redirect Enabled
```

#### Step 4: Add CNAME Record to DNS

**Verify the Front Door Hostname**:

```bash
cd infrastructure/pulumi/azure
pulumi stack select production  # or staging
FRONTDOOR_HOSTNAME=$(pulumi stack output frontdoor_hostname)
echo "Front Door Hostname: $FRONTDOOR_HOSTNAME"
```

**For Azure DNS**:

```bash
az network dns record-set cname set-record \
  --resource-group YOUR_DNS_RG \
  --zone-name ashnova.jp \
  --record-set-name www.azure \
  --cname $FRONTDOOR_HOSTNAME
```

**For external DNS providers**:

- Record type: `CNAME`
- Name: `www.azure.ashnova.jp`
- Value:
  - Production: `mcad-production-diev0w-f9ekdmehb0bga5aw.z01.azurefd.net`
  - Staging: `mcad-staging-d45ihd-dseygrc9c3a3htgj.z01.azurefd.net`

#### Step 5: Confirm HTTPS Is Active

```bash
# Check custom domain status
az afd custom-domain show \
  --resource-group $RESOURCE_GROUP \
  --profile-name $PROFILE_NAME \
  --custom-domain-name $CUSTOM_DOMAIN_NAME \
  --query "{provisioningState, domainValidationState, deploymentStatus}"
```

---

## 3️⃣ GCP Cloud CDN Custom Domain Setup

### Prerequisites

- Domain ownership verified
- Google Cloud DNS (recommended) or external DNS provider

### Steps

#### Step 1: Update Managed SSL Certificate

Modify the SSL certificate section in `infrastructure/pulumi/gcp/__main__.py`:

```python
# Configure custom domain
custom_domain = config.get("customDomain")  # e.g. gcp.yourdomain.com

managed_ssl_cert = gcp.compute.ManagedSslCertificate(
    f"{project_name}-{stack}-ssl-cert",
    managed=gcp.compute.ManagedSslCertificateManagedArgs(
        domains=[custom_domain] if custom_domain else ["example.com"],
    ),
    opts=pulumi.ResourceOptions(
        delete_before_replace=True,
    ),
)
```

#### Step 2: Update Pulumi Configuration and Deploy

```bash
cd infrastructure/pulumi/gcp
pulumi config set customDomain www.gcp.ashnova.jp --stack production
pulumi up --stack production
```

**Note**: Managed SSL certificate provisioning can take up to 60 minutes.

#### Step 3: Add A Record to DNS

**Verify the CDN IP address**:

```bash
cd infrastructure/pulumi/gcp
pulumi stack select production  # or staging
CDN_IP=$(pulumi stack output cdn_ip_address)
echo "CDN IP Address: $CDN_IP"
```

**For Google Cloud DNS**:

```bash
gcloud dns record-sets create www.gcp.ashnova.jp. \
  --zone=YOUR_ZONE_NAME \
  --type=A \
  --ttl=300 \
  --rrdatas=$CDN_IP
```

**For external DNS providers**:

- Record type: `A`
- Name: `www.gcp.ashnova.jp`
- Value:
  - Production: `34.8.38.222`
  - Staging: `34.117.111.182`

#### Step 4: Verify SSL Certificate Provisioning

```bash
# Check certificate status (wait until ACTIVE)
gcloud compute ssl-certificates describe multicloud-auto-deploy-production-ssl-cert-3ee2c3ce \
  --global \
  --format="value(managed.status)"

# Expected: ACTIVE
```

**If provisioning takes a long time**:

- Verify that the DNS record is correctly configured
- Wait for DNS propagation (up to 48 hours, usually a few minutes to hours)
- Verify DNS resolution with `dig www.gcp.ashnova.jp`

---

## 🔄 Update CORS Settings

After configuring custom domains, CORS settings for each cloud must be updated.

### AWS

```bash
cd infrastructure/pulumi/aws
pulumi config set allowedOrigins "https://www.aws.ashnova.jp,http://localhost:5173" --stack production
pulumi up --stack production
```

### Azure

```bash
cd infrastructure/pulumi/azure
pulumi config set allowedOrigins "https://www.azure.ashnova.jp,http://localhost:5173" --stack production
# Azure Function App environment variables require manual update
```

### GCP

```bash
cd infrastructure/pulumi/gcp
pulumi config set allowedOrigins "https://www.gcp.ashnova.jp,http://localhost:5173" --stack production
pulumi up --stack production
```

---

## ✅ Verification

### 1. Verify DNS Resolution

```bash
# AWS
dig www.aws.ashnova.jp
nslookup www.aws.ashnova.jp

# Azure
dig www.azure.ashnova.jp
nslookup www.azure.ashnova.jp

# GCP
dig www.gcp.ashnova.jp
nslookup www.gcp.ashnova.jp
```

### 2. Verify SSL Certificate

```bash
# Check SSL certificate validity
curl -vI https://www.aws.ashnova.jp
curl -vI https://www.azure.ashnova.jp
curl -vI https://www.gcp.ashnova.jp

# Or
openssl s_client -connect www.aws.ashnova.jp:443 -servername www.aws.ashnova.jp < /dev/null
```

### 3. Verify Application

```bash
# Access frontends
curl https://www.aws.ashnova.jp
curl https://www.azure.ashnova.jp
curl https://www.gcp.ashnova.jp

# Access APIs (health check)
curl https://www.aws.ashnova.jp/health
curl https://www.azure.ashnova.jp/api/health
curl https://www.gcp.ashnova.jp/health
```

---

## 🔍 Troubleshooting

### Certificate Error

**Problem**: SSL certificate error occurs

**Solution**:

1. Check certificate status
2. Verify that domain aliases are correctly configured
3. Verify that the certificate is associated with CloudFront / Front Door / Cloud CDN

### DNS Resolution Failure

**Problem**: Domain does not resolve

**Solution**:

1. Verify that DNS records are correctly configured
2. Wait for DNS propagation (up to 48 hours)
3. Check from Google DNS: `dig @8.8.8.8 www.aws.ashnova.jp`
4. Check TTL values (after changes, wait for old TTL to expire)

### GCP Managed SSL Certificate Not Becoming ACTIVE

**Problem**: Certificate remains in PROVISIONING state for a long time

**Solution**:

1. Verify that the DNS A record points to the correct IP address
2. Verify that the load balancer is operating normally
3. Verify that the domain is globally resolvable (run `dig` from multiple locations)

### Azure Front Door Validation Failure

**Problem**: Custom domain validation fails

**Solution**:

1. Verify that the TXT record (`_dnsauth`) is correctly configured
2. Verify that validationToken is correct
3. Wait for DNS propagation
4. Verify with `dig TXT _dnsauth.www.azure.ashnova.jp`

---

## 📝 Additional Costs per Cloud

| Cloud     | Additional Cost                                               |
| --------- | ------------------------------------------------------------- |
| **AWS**   | ACM certificate: Free<br>CloudFront custom domain: Free       |
| **Azure** | Front Door Managed Certificate: Free<br>Custom domain: Free   |
| **GCP**   | Managed SSL Certificate: Free<br>Load balancer already exists |

---

## 🎯 Next Steps

Recommended tasks after custom domain setup:

1. **Update monitoring alerts**: Configure monitoring for new domains
2. **Validate CORS settings**: Access from a browser to verify behavior
3. **Add security headers**: Configure HSTS, CSP, etc.
4. **Configure redirects**: Redirect from old endpoints to new domains
5. **Update documentation**: Add new URLs to README.md

---

## 📚 Reference Links

- [AWS CloudFront - Custom Domain Setup](https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/CNAMEs.html)
- [Azure Front Door - Custom Domain](https://learn.microsoft.com/en-us/azure/frontdoor/standard-premium/how-to-add-custom-domain)
- [GCP - Managed SSL Certificates](https://cloud.google.com/load-balancing/docs/ssl-certificates/google-managed-certs)
