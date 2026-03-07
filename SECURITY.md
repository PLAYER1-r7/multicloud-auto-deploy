# Security Policy

**Last Updated**: March 4, 2026
**Status**: Active (Individual Developer Maintained)
**Maintainer**: [@PLAYER1-r7](https://github.com/PLAYER1-r7)

---

## 📋 Overview

This document describes the security design, implementation, and operational policies for the multicloud-auto-deploy project. It addresses security requirements for a **single-maintainer multi-cloud system** running on three cloud providers: AWS, Azure, and GCP.

> **Note**: This is an individual developer project. Security processes are simplified to be maintainable by one person while maintaining essential security standards.

### Three Pillars of Security

1. **Confidentiality** — Only authorized users can access data and features
2. **Integrity** — Detect and prevent data tampering and unauthorized modifications
3. **Availability** — Ensure availability through rate limiting, WAF, and DDoS protection

---

## 🔐 Authentication & Authorization

### Unified Multi-Cloud Authentication

Native authentication services for each cloud are adopted, unified with the OAuth 2.0 + PKCE flow by default.

| Cloud     | Service       | Implementation            | Token Management             |
| --------- | ------------- | ------------------------- | ---------------------------- |
| **AWS**   | Cognito       | Authorization Code + PKCE | Session cookie (secure)      |
| **Azure** | Azure AD      | Authorization Code + PKCE | Session cookie (secure)      |
| **GCP**   | Firebase Auth | Authorization Code + PKCE | JWT (idToken / refreshToken) |

### PKCE (Proof Key for Code Exchange) — Implemented 2026-02-23

```
Browser                    Authorization Server
  │                              │
  ├─ code_verifier              │
  │  (256-bit random)           │
  │                              │
  ├─ code_challenge             │
  │  = SHA-256(verifier)         │
  │  → Authorization Request     │
  │ ──────────────────────────>│
  │                              │
  │    Authorization Code        │
  │ <──────────────────────────│
  │                              │
  │  Token Exchange + verifier    │
  │  (not exposed in URL fragment)
  │ ──────────────────────────>│
  │                              │
  │    ID Token + Refresh Token   │
  │ <──────────────────────────│
```

**Advantages**:

- ✅ Complete elimination of token leakage to URL fragments (implicit flow deprecated)
- ✅ Compliance with modern OAuth/OIDC security standards
- ✅ Mobile apps can use the same flow

### Single Maintainer Account Setup

As an individual developer, you control all cloud accounts. **Best practices**:

| Cloud      | Account           | MFA Required | Backup Access               |
| ---------- | ----------------- | ------------ | --------------------------- |
| **AWS**    | Personal IAM User | ✅ Yes       | Emergency AWS root backup   |
| **Azure**  | Personal account  | ✅ Yes       | Backup credentials file     |
| **GCP**    | Personal account  | ✅ Yes       | Service account key backup  |
| **GitHub** | Personal account  | ✅ Yes       | Backup authentication codes |

**Essential**: Enable MFA on all accounts. Keep backup credentials (encrypted) but not committed to repos.

---

## 🔒 Encryption

### Encryption in Transit

| Target              | Cloud | Implementation | Status |
| ------------------- | ----- | -------------- | ------ |
| CDN → Browser       | All   | TLS 1.3        | ✅     |
| Browser → Backend   | All   | TLS 1.3        | ✅     |
| CloudFront → Origin | AWS   | TLS 1.3        | ✅     |
| Front Door → Origin | Azure | TLS 1.3        | ✅     |
| Cloud CDN → Origin  | GCP   | TLS 1.3        | ✅     |

**HTTPS Enforcement**: All HTTP requests are redirected with 301 (→ HTTPS)

```
curl -I http://staging.aws.ashnova.jp/
# HTTP/1.1 301 Moved Permanently
# Location: https://staging.aws.ashnova.jp/
```

### Encryption at Rest

| Resource       | AWS             | Azure        | GCP            | Implementation                                        |
| -------------- | --------------- | ------------ | -------------- | ----------------------------------------------------- |
| Object Storage | S3              | Blob Storage | GCS            | SSE-S3 (AWS) / Azure SSE (automatic) / Google-managed |
| Database       | DynamoDB        | Cosmos DB    | Firestore      | AWS KMS integration / Azure-managed / Google-managed  |
| Secrets        | Secrets Manager | Key Vault    | Secret Manager | Full encryption                                       |

**AWS KMS**: Lambda execution role can automatically decrypt via `secretsmanager:GetSecretValue`

---

## 🌐 Network Security

### HTTPS Enforcement & Security Headers

#### ✅ AWS CloudFront (Implemented 2026-02-23)

```http
Strict-Transport-Security: max-age=31536000; includeSubDomains
Content-Security-Policy: upgrade-insecure-requests
X-Content-Type-Options: nosniff
X-Frame-Options: SAMEORIGIN
X-XSS-Protection: 1; mode=block
Referrer-Policy: strict-origin-when-cross-origin
```

**Verification**:

```bash
curl -sI https://staging.aws.ashnova.jp/ | grep -iE 'strict-transport|content-security'
```

#### ❌ Azure Front Door (Not Implemented)

Plan to add HSTS/CSP/X-Frame-Options to AFD RuleSet.

#### ❌ GCP Cloud Run (Not Implemented)

Plan to add security headers middleware to FastAPI.

### WAF (Web Application Firewall)

| Cloud     | Implementation    | Status | Details                                                             |
| --------- | ----------------- | ------ | ------------------------------------------------------------------- |
| **AWS**   | CloudFront WebACL | ✅     | Rate limiting: 2000 req/5min/IP                                     |
| **Azure** | Front Door WAF    | ❌     | Premium SKU is prohibited; use Standard SKU + standalone WAF Policy |
| **GCP**   | Cloud Armor       | ✅     | Rate limiting: 100 req/min/IP                                       |

**Azure Option (policy-compliant)**:

- Create and attach a standalone Azure WAF Policy on Front Door Standard SKU

### CORS (Cross-Origin Resource Sharing)

#### AWS CDN

```bash
# CloudFront: CORS at CDN level is not needed
# Browser does not communicate directly with S3 (via CloudFront)
```

#### Azure CORS (Important — Two-Layer Structure)

⚠️ **Kestrel (Function App) CORS** and **Blob Storage CORS** are independent

```bash
# Layer 1: Function App API requests
az functionapp cors add \
  --resource-group "multicloud-auto-deploy-production-rg" \
  --name "multicloud-auto-deploy-production-func" \
  --allowed-origins "https://production.azure.ashnova.jp"

# Layer 2: Blob Storage image uploads (SAS URL)
az storage cors add \
  --account-name "mcadwebprod****" \
  --services b \
  --methods GET POST PUT DELETE OPTIONS \
  --origins "https://production.azure.ashnova.jp" \
  --allowed-headers "*" \
  --max-age 3600
```

#### GCP CORS

```python
# Cloud Run FastAPI: Get CORS origins from environment variables
ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "").split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
    max_age=3600,
)
```

**Production**: Restrict wildcard `*` to actual domain (e.g., `https://gcp.ashnova.jp`)

---

## 🔑 Secrets & Key Management

### Storage Locations

| Environment         | Service         | Usage                          | Access                              |
| ------------------- | --------------- | ------------------------------ | ----------------------------------- |
| **AWS Lambda**      | Secrets Manager | DB credentials / API keys      | IAM role (GetSecretValue)           |
| **Azure Functions** | Key Vault       | Connection strings / passwords | Managed Identity (Key Vault User)   |
| **GCP Cloud Run**   | Secret Manager  | Service account keys           | Workload Identity / Service Account |
| **CI/CD**           | GitHub Secrets  | Cloud provider credentials     | GitHub Actions (OIDC auth)          |

### Secrets Rotation

- ✅ **Secrets Manager (AWS)**: Automatic rotation configurable (Lambda integration)
- ✅ **Key Vault (Azure)**: Rotation Policy required (Automation Account)
- ✅ **Secret Manager (GCP)**: Manual rotation recommended (Pub/Sub trigger available)
- ✅ **GitHub Secrets**: Environment variables updated per deployment

### Secrets Exposure Response

**Immediately execute the following**:

1. Delete the affected key from GitHub Secrets / Vault
2. Invalidate and rotate the secret on the cloud provider side
3. Remove from repository history (`git-filter-branch` or `git rebase`)
4. Issue a security advisory

---

## 📊 Audit Logging & Compliance

### Implemented (2026-02-24)

#### AWS CloudTrail

```python
# infrastructure/pulumi/aws/__main__.py
cloudtrail = aws.cloudtrail.Trail(
    "trail",
    s3_bucket_name=cloudtrail_bucket.id,
    is_multi_region_trail=True,
    include_global_service_events=True,
    enable_log_file_validation=True,  # SHA-256 digest verification
)
```

**Audited Services**: Lambda, APIGateway, Cognito, IAM, S3, DynamoDB, and all services

#### Azure Log Analytics

```yaml
# Auto-delete after 30 days
Log Analytics Workspace
├── Front Door Logs
├── Function App Logs
└── Key Vault Access Logs
```

**Query Example**:

```kusto
AzureDiagnostics
| where ResourceProvider == "MICROSOFT.CDN"
| where TimeGenerated >= ago(24h)
| summarize count() by httpStatus_s, clientIP_s
```

#### GCP Cloud Audit Logs

```python
# infrastructure/pulumi/gcp/__main__.py
audit_config = gcp.projects.IAMAuditConfig(
    service="allServices",
    audit_log_configs=[
        gcp.projects.AuditLogConfigArgs(
            service="allServices",
            log_type="ADMIN_READ",
        ),
        gcp.projects.AuditLogConfigArgs(
            service="allServices",
            log_type="DATA_READ",
        ),
    ],
)
```

**Verification**: Cloud Console > Logs > Cloud Audit Logs

---

## 🛡️ Data Protection & Personal Information

### User Data Classification

| Data Type          | Examples             | Storage                                 | Encrypted | Access Control            |
| ------------------ | -------------------- | --------------------------------------- | --------- | ------------------------- |
| **Authentication** | Password / MFA       | Cognito / Azure AD / Firebase           | ✅        | IdP only                  |
| **Personal Info**  | Username / Email     | DynamoDB / Cosmos DB / Firestore        | ✅        | Authenticated users       |
| **Content**        | Post text / Comments | DynamoDB / Cosmos DB / Firestore        | ✅        | Author / authorized users |
| **Media**          | Images / Uploads     | S3 / Blob Storage / GCS                 | ✅        | Presigned URL + TTL       |
| **Logs**           | Access / Audit logs  | CloudTrail / Log Analytics / Audit Logs | ✅        | Admin only                |

### Personal Information Deletion (GDPR / Privacy Law Compliance)

**User Deletion Request**:

```bash
# Delete all records for the user from DynamoDB/Cosmos/Firestore
DELETE FROM Posts WHERE userId = "user-123"
DELETE FROM Comments WHERE userId = "user-123"
DELETE FROM Profiles WHERE userId = "user-123"

# Delete uploaded images from S3/Blob/GCS
aws s3 rm s3://bucket/uploads/user-123/ --recursive

# Retain audit logs (legal requirement)
# CloudTrail / Log Analytics / Audit Logs are not deleted
```

---

## 🚨 Incident Response

### Security Incident Classification

| Severity     | Definition                                       | Response Time   | Example                                 |
| ------------ | ------------------------------------------------ | --------------- | --------------------------------------- |
| **Critical** | System outage / data breach / auth failure       | Within 1 hour   | All users' authentication invalidated   |
| **High**     | Partial function outage / individual user impact | Within 4 hours  | Single user account unauthorized access |
| **Medium**   | Log recording gaps / WAF blocking surge          | Within 24 hours | DDoS attack detected                    |
| **Low**      | Documentation typos / missing security headers   | Within 1 week   | CSP header not configured               |

### Incident Response Flow

```
1. Detection & Reporting
   ↓
2. Initial Response & Containment
   ├─ Stop affected service or restrict functionality
   ├─ Confirm impact scope
   └─ Collect and preserve logs
   ↓
3. Root Cause Investigation
   ├─ Review CloudTrail / Log Analytics / Audit Logs
   ├─ Analyze application logs
   └─ External audit (if necessary)
   ↓
4. Remediation & Recovery
   ├─ Apply security patches
   ├─ Rotate secrets
   └─ Test and deploy to production
   ↓
5. Post-Incident Report
   ├─ Notify stakeholders
   ├─ Implement preventive measures
   └─ Update documentation
```

---

## ✅ Security Checklist

### Before Deployment (All Environments)

- [ ] Secrets/API keys are not included in the repository (git secrets scanned)
- [ ] HTTPS/TLS 1.3 verified
- [ ] CORS origins restricted to actual domains
- [ ] Security headers configured
- [ ] WAF rules enabled
- [ ] Audit logs being recorded

### After Staging Deployment

- [ ] HTTPS certificate valid (hosting $DOMAIN)
- [ ] Authentication flow successful (Cognito/Azure AD/Firebase)
- [ ] PKCE token exchange verifiable in browser console
- [ ] Operation logs recorded in CloudTrail / Log Analytics / Audit Logs
- [ ] Image upload → SAS URL → browser display successful
- [ ] Security headers verified with curl

### Before Production Deployment (Final Check)

- [ ] Custom domain / SSL certificate specified in settings
- [ ] IAM/RBAC permissions reviewed (MFA enabled, unnecessary APIs disabled)
- [ ] Database encryption / Key rotation enabled
- [ ] Backup / Disaster Recovery plan documented
- [ ] Security testing (vulnerability scan) completed
- [ ] Personal security review completed (README, credentials, config)

---

## 🔄 Security Roadmap (Priority Order)

### Phase 1 — Apply Pulumi Changes to Production (Immediate)

```bash
# All implemented in Pulumi code, requires pulumi up
cd infrastructure/pulumi/aws   && pulumi up --stack production
cd infrastructure/pulumi/azure && pulumi up --stack production
cd infrastructure/pulumi/gcp   && pulumi up --stack production
```

**Included**:

- ✅ CORS `*` → restrict to actual domains (all 3 clouds)
- ✅ AWS CloudTrail enablement
- ✅ GCP HTTP→HTTPS redirect separation
- ✅ Azure Log Analytics + Front Door diagnostic settings

### Phase 2 — Add Security Headers (1-2 weeks)

- [ ] Add HSTS/CSP/X-Frame-Options to Azure Front Door RuleSet
- [ ] Implement security headers middleware in GCP Cloud Run FastAPI
- [ ] Verify AWS CloudFront `upgrade-insecure-requests` CSP setting

### Phase 3 — Azure Security Improvements (2-4 weeks)

- [ ] Enable Function App Managed Identity
- [ ] Enable Key Vault purge protection
- [ ] Configure Key Vault diagnostic logs → Log Analytics

### Phase 4 — Azure WAF Implementation

- [ ] Create and attach standalone WAF Policy on Front Door Standard SKU (Premium prohibited by policy)
- [ ] Configure SQLi / XSS / Bot Protection rules

---

## 📞 Security Contacts & Reporting

### Reporting a Vulnerability

If you discover a security vulnerability in this project, **please do not create a public GitHub issue**. Instead:

1. **Use GitHub's Private Vulnerability Reporting** (Recommended)
   - Navigate to: https://github.com/PLAYER1-r7/multicloud-auto-deploy/security/advisories
   - Click "Report a vulnerability"
   - Fill in the vulnerability details

2. **Email Notification** (Alternative)
   - Send details to: `sat0sh1kawada@spa.nifty.com`
   - Subject: `[SECURITY] Vulnerability Report`

### Information to Include

When reporting, please provide:

- Description of the vulnerability and its impact
- Affected resources (e.g., Lambda functions, storage buckets, Cloud Run services)
- Steps to reproduce
- Suggested fix (if any)

### Expected Response Timeline

As a **1-person project**, response times are best-effort, not guaranteed SLAs:

| Severity     | Target Response | Target Patch   |
| ------------ | --------------- | -------------- |
| **Critical** | 48 hours        | 1 week         |
| **High**     | 1 week          | 2 weeks        |
| **Medium**   | 2 weeks         | 1 month        |
| **Low**      | 1 month         | When available |

### Responsible Disclosure

I commit to:

- Confirming receipt of your report
- Working on a fix in a private branch
- Notifying you before public disclosure
- Crediting you in the commit (if you wish)

Please:

- Do not disclose publicly until I've released a patch
- Give reasonable time for fixes before disclosure (aim for 30-60 days)
- Help coordinate a safe disclosure timeline

### Security Update Notifications

Subscribe to security updates:

- [GitHub Dependabot alerts](https://github.com/PLAYER1-r7/multicloud-auto-deploy/security/dependabot)
- AWS/Azure/GCP console security notifications
- Watch this repository for releases

---

## � Supported Versions

The following versions are currently receiving security updates:

| Version        | Branch           | Supported | EOL Date |
| -------------- | ---------------- | --------- | -------- |
| **Production** | `main`           | ✅        | TBD      |
| **Staging**    | `main`           | ✅        | Current  |
| Pre-release    | Feature branches | ⚠️        | On merge |

**Versions older than the current production release are not supported and will not receive security patches.**

---

## 🔐 Security Best Practices for Contributors

If you're contributing code to this project:

- Run `git secrets` before commits to prevent credential leaks
- Use AWS Secrets Manager for API keys, never hardcode credentials
- Follow the [Principle of Least Privilege](docs/AI_AGENT_00_CRITICAL_RULES.md#rule-16) for IAM roles
- Enable MFA on cloud provider accounts
- Test security changes in staging before production deployment
- Request code review from security-aware maintainers
- Document any sensitive configuration changes

---

## 📚 References

**Design Documentation** (Japanese):

- [AI_AGENT_08_SECURITY_JA.md](docs/AI_AGENT_08_SECURITY_JA.md) — Detailed security architecture
- [AI_AGENT_04_INFRA_JA.md](docs/AI_AGENT_04_INFRA_JA.md) — Pulumi infrastructure code
- [AI_AGENT_00_CRITICAL_RULES_JA.md](docs/AI_AGENT_00_CRITICAL_RULES_JA.md) — Critical security rules

**External Resources**:

- [AWS Well-Architected Security Pillar](https://docs.aws.amazon.com/wellarchitected/latest/security-pillar/welcome.html)
- [Azure Security Best Practices](https://learn.microsoft.com/en-us/azure/security/fundamentals/best-practices-and-patterns)
- [Google Cloud Security Best Practices](https://cloud.google.com/architecture/best-practices-for-security)
- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [GitHub Private Vulnerability Reporting](https://docs.github.com/en/code-security/security-advisories/privately-reporting-a-security-vulnerability)

---

**Maintained by**: [@PLAYER1-r7](https://github.com/PLAYER1-r7) (individual developer)
**Last Updated**: March 4, 2026
**Next Security Review**: June 4, 2026
