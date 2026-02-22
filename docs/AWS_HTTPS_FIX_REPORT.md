# AWS Production HTTPS Fix Report (2026-02-21)

> **Status**: ✅ Resolved — `https://www.aws.ashnova.jp` HTTPS operating normally  
> **Target Distribution**: `E214XONKTXJEJD` (`d1qob7569mn5nw.cloudfront.net`)  
> **Fix Method**: `aws cloudfront update-distribution` (direct modification)

---

## Symptoms

Opening `https://www.aws.ashnova.jp` in a browser displayed the following error:

```
NET::ERR_CERT_COMMON_NAME_INVALID
Your connection is not private
Attackers might be trying to steal your information from www.aws.ashnova.jp.
```

---

## Root Cause

CloudFront distribution `E214XONKTXJEJD` was missing the **custom domain alias** and **ACM certificate** configuration.

| Setting | Before (Broken State) | After (Fixed State) |
|---|---|---|
| `Aliases` | `Quantity: 0` (not set) | `["www.aws.ashnova.jp"]` |
| `ViewerCertificate` | `CloudFrontDefaultCertificate: true` (only `*.cloudfront.net`) | ACM certificate `914b86b1` (dedicated to `www.aws.ashnova.jp`) |

DNS had `www.aws.ashnova.jp → d1qob7569mn5nw.cloudfront.net` (CNAME) already configured,
but since CloudFront only held the `*.cloudfront.net` certificate,
the browser raised a domain mismatch error (`ERR_CERT_COMMON_NAME_INVALID`).

### Why `pulumi up` Did Not Apply the Fix

The design document ([CUSTOM_DOMAIN_SETUP.md](CUSTOM_DOMAIN_SETUP.md)) recorded that aliases were added after `pulumi up --stack production`, but **in reality, the Pulumi state contained no `customDomain` / `acmCertificateArn` config values**.

Logic in `infrastructure/pulumi/aws/__main__.py`:

```python
custom_domain = config.get("customDomain")    # None → falls into else branch
acm_certificate_arn = config.get("acmCertificateArn")  # None

if custom_domain and acm_certificate_arn:
    # Configure custom certificate (this was NOT executed)
else:
    cloudfront_kwargs["viewer_certificate"] = (
        aws.cloudfront.DistributionViewerCertificateArgs(
            cloudfront_default_certificate=True,  # ← this was applied
        )
    )
```

Because the config values were not set, the `else` branch executed and the default CloudFront certificate was retained.

---

## Investigation Steps

```bash
# 1. Check the certificate configuration of the CloudFront distribution
aws cloudfront get-distribution --id E214XONKTXJEJD \
  --query 'Distribution.DistributionConfig.{Aliases:Aliases,ViewerCertificate:ViewerCertificate}' \
  --output json

# Output (broken state):
# {
#   "Aliases": { "Quantity": 0 },
#   "ViewerCertificate": {
#     "CloudFrontDefaultCertificate": true,
#     ...
#   }
# }

# 2. List ACM certificates in us-east-1 and confirm an ISSUED certificate for www.aws.ashnova.jp
aws acm list-certificates --region us-east-1 --output json
# → arn:aws:acm:us-east-1:278280499340:certificate/914b86b1-4c10-4354-91cf-19c4460dcde5
#   DomainName: www.aws.ashnova.jp, Status: ISSUED, NotAfter: 2027-03-12
```

---

## Fix Procedure

### 1. Retrieve the current distribution config

```bash
aws cloudfront get-distribution-config --id E214XONKTXJEJD > /tmp/cf-config.json
# ETag: E13V1IB3VIYZZH
```

### 2. Modify the configuration

```python
import json

with open('/tmp/cf-config.json') as f:
    data = json.load(f)

config = data['DistributionConfig']

config['Aliases'] = {
    'Quantity': 1,
    'Items': ['www.aws.ashnova.jp']
}

config['ViewerCertificate'] = {
    'ACMCertificateArn': 'arn:aws:acm:us-east-1:278280499340:certificate/914b86b1-4c10-4354-91cf-19c4460dcde5',
    'SSLSupportMethod': 'sni-only',
    'MinimumProtocolVersion': 'TLSv1.2_2021',
    'CertificateSource': 'acm'
}

with open('/tmp/cf-config-updated.json', 'w') as f:
    json.dump(config, f, indent=2)
```

### 3. Update the distribution

```bash
aws cloudfront update-distribution \
  --id E214XONKTXJEJD \
  --distribution-config file:///tmp/cf-config-updated.json \
  --if-match E13V1IB3VIYZZH \
  --query 'Distribution.{Id:Id,Status:Status,Aliases:DistributionConfig.Aliases}' \
  --output json

# Result:
# {
#   "Id": "E214XONKTXJEJD",
#   "Status": "InProgress",   ← propagation to edge nodes started
#   "Aliases": { "Quantity": 1, "Items": ["www.aws.ashnova.jp"] }
# }
```

### 4. Verify Operation

```bash
curl -sI https://www.aws.ashnova.jp | head -5
# HTTP/2 200
# server: AmazonS3
# x-cache: RefreshHit from cloudfront
# via: 1.1 ...cloudfront.net (CloudFront)
```

---

## ACM Certificate Used

| ARN | Domain | Expiry | Status |
|---|---|---|---|
| `arn:aws:acm:us-east-1:278280499340:certificate/914b86b1-4c10-4354-91cf-19c4460dcde5` | `www.aws.ashnova.jp` | 2027-03-12 | ISSUED |

> **Note**: Multiple ACM certificates exist for `www.aws.ashnova.jp`, but `914b86b1` was selected as it has the latest expiry (2027-03-12).

---

## Prevention

Before running `pulumi up --stack production` again, always set the following config values:

```bash
cd infrastructure/pulumi/aws
pulumi stack select production
pulumi config set customDomain www.aws.ashnova.jp
pulumi config set acmCertificateArn arn:aws:acm:us-east-1:278280499340:certificate/914b86b1-4c10-4354-91cf-19c4460dcde5
pulumi up --stack production
```

Without setting these values, `pulumi up` will revert CloudFront to `CloudFrontDefaultCertificate: true`, causing the same issue to recur.

---

## Timeline

| Time (JST) | Action |
|---|---|
| ~2026-02-21 21:11 | Confirmed `NET::ERR_CERT_COMMON_NAME_INVALID` in browser |
| ~2026-02-21 21:15 | Identified that CloudFront distribution alias and certificate were not configured |
| ~2026-02-21 21:20 | Set alias + ACM certificate via `aws cloudfront update-distribution` |
| ~2026-02-21 21:20 | Confirmed `curl -I https://www.aws.ashnova.jp` → HTTP/2 200 (nearest edge already updated) |
| ~2026-02-21 21:35 | Expected full propagation to all CloudFront edges (`Status: Deployed`) |
