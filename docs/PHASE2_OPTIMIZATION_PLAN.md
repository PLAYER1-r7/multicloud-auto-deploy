# Phase 2: Production Optimization Plan

> フェーズ 2 実装計画（T6-T10）
> 推定期間: 3～4週間
> 優先度: T6（Critical）→ T7-T10（Medium）

---

## Overview

### Current State
- **Phase 1**: ✅ Stability foundation complete (T1-T5)
  - GCP billing budget flag implementation
  - Production endpoint validation scripts
  - Audit log verification scripts
  - React OAuth verification
  - PM dashboard automation

- **Phase 2**: 🟡 Initialization in progress
  - **T6**: GCP Production Pulumi Deployment [CRITICAL - Ready to Execute]
  - **T7-T10**: Performance + Reliability optimization [Discovery phase]

### Success Criteria
1. ✅ T6 execution: 0 cloud errors, state drift resolved, SSL certificate ACTIVE
2. ✅ T7 completion: Lambda coldstart reduction by 30-50% (baseline measurement)
3. ✅ T8 completion: CDN caching strategy optimized, hit ratio >90%
4. ✅ T9 completion: API rate limiting enforced with 429 responses
5. ✅ T10 completion: Alert thresholds tuned, false positives <5%

---

## Task T6: GCP Production Pulumi Deployment (CRITICAL)

> **Status**: 🔴 AWAITING EXECUTION
> **Timeline**: 5-10 minutes (automated via GitHub Actions)
> **Blockers**: None (all prerequisites met)
> **Rollback**: Documented, tested

### Pre-Execution Checklist
- [ ] Git main branch, clean working directory
- [ ] GCP project `ashnova` active context
- [ ] GitHub Actions secrets verified:
  - [ ] `GCP_CREDENTIALS` (service account JSON)
  - [ ] `GCP_PROJECT_ID` (ashnova)
  - [ ] `PULUMI_ACCESS_TOKEN` (valid)

### Execution Steps

#### Option A: Automated (GitHub Actions - Recommended)
```
1. GitHub Web: https://github.com/[owner]/multicloud-auto-deploy
2. Actions tab → "Deploy to GCP" workflow
3. "Run workflow" button (top right)
4. Environment: "production"
5. Confirm "Run workflow"
6. Monitor workflow logs (~5-10 minutes)
```

#### Option B: Manual (CLI)
```bash
cd /workspaces/multicloud-auto-deploy
bash scripts/gcp-production-preflight.sh    # Validate environment (2 min)
cd infrastructure/pulumi/gcp
pulumi stack select production
pulumi config set enableBillingBudget "false"
pulumi refresh --yes                        # Resolve state drift (5 min)
pulumi up --stack production                # Deploy (5 min)
```

### Expected Outputs
```
Updating (production)

View Live Updates stream here: https://app.pulumi.com/...

     Type                                   Name     Status
 +   pulumi:pulumi:Stack               project-production  created
 +   │   ├─ gcp:monitoring: ...          billing... created
 +   ├─ gcp:storage: Bucket ...              frontend created
 +   └─ gcp:compute: ...                     cdn-config updated
 ...
 Outputs:
     custom_domain: "www.gcp.ashnova.jp"
     cdn_ip_address: "xx.xx.xx.xx"
     frontend_bucket: "gcp-frontend-prod-..."
 ...
 Resources:
     + 15 created, 3 updated
   Duration: 5m42s
```

### Post-Deployment Verification

#### Step 1: SSL Certificate Status (Immediate)
```bash
gcloud compute ssl-certificates list --project=ashnova
# Expected: www.gcp.ashnova.jp status = ACTIVE (not PROVISIONING)
```

#### Step 2: CDN Health Check (1-2 min)
```bash
curl -I https://www.gcp.ashnova.jp
# Expected: HTTP 200, Content-Type: text/html
```

#### Step 3: Audit Log Verification (3 min)
```bash
cd /workspaces/multicloud-auto-deploy
bash scripts/verify-audit-logs.sh
# Expected: GCP Cloud Audit Logs showing Pulumi deployment events
```

#### Step 4: Performance Baseline (5 min)
```bash
ab -n 100 -c 10 https://www.gcp.ashnova.jp
# Record: response time, requests/sec, errors
# Used as baseline for T8 optimization
```

### Success Criteria
- [ ] `pulumi up` exit code 0 (or 1 with continue-on-error: only state drift warnings)
- [ ] SSL certificate status: ACTIVE
- [ ] CDN returns HTTP 200 with <1s response time
- [ ] Cloud Audit Logs record deployment success
- [ ] No errors in Cloud Monitoring dashboard

### Failure Handling
If T6 deployment fails:
1. Check Cloud Audit Logs for 403/409/412 errors
2. If ManagedSslCertificate/URLMap errors → Run `pulumi refresh --yes` again
3. If IAM errors → Verify service account permissions (monitoring role)
4. If credential errors → Re-run `gcloud auth login` or restart container
5. Last resort: Run rollback script (documented in GCP_PRODUCTION_DEPLOYMENT_PLAN.md)

---

## Task T7: Lambda Coldstart Reduction (Medium Priority)

> **Target**: 30-50% latency reduction for cold starts
> **Discovery**: 1-2 days | Implementation: 3-5 days
> **Timeline**: Week of 2026-03-10

### Phase 1: Measurement & Analysis (1 day)

#### 1.1 Establish Baseline
```bash
# Get Lambda invocation metrics from CloudWatch
aws logs insights query: \
  fields @duration \
  | filter ispresent(@duration) \
  | stats avg(@duration), pct(@duration, 50), pct(@duration, 99)

# Record metrics for cold/warm starts:
# - Cold start P50: ??? ms
# - Cold start P99: ??? ms
# - Warm start P50: ??? ms
```

#### 1.2 Identify Bottlenecks
- Analyze CloudWatch X-Ray traces for slow imports/initialization
- Check Python `requirements.txt` for heavy dependencies (numpy, pytorch, etc.)
- Measure Lambda layer size vs execution capacity

### Phase 2: Implementation Options (3-5 days)

#### Option A: Provisioned Concurrency (Recommended)
```
Cost: ~$5-10/day for 5 warm instances
Benefit: Eliminates cold starts entirely
Risk: Increased baseline cost

Implementation:
1. Create Lambda alias "warm"
2. Set provisioned concurrency: 5
3. Update API Gateway to use alias
4. Monitor: Verify stream events from provisioned instances
```

#### Option B: Container Image Optimization
```
Cost: None (code optimization only)
Benefit: Faster initialization (5-10s → 2-3s cold start)
Risk: Requires Python version lock, careful testing

Implementation:
1. Replace heavy dependencies with lighter alternatives
2. Use Python distroless base image
3. Lazy-load large libraries in handler
4. Test with SAM local invocation
```

#### Option C: Lambda Layers + Code Separation
```
Cost: None (code restructuring only)
Benefit: Faster zip file delivery (20-30% faster)
Risk: Dependency management overhead

Implementation:
1. Extract shared dependencies to Lambda layer
2. Move data loading to layer initialization
3. Keep handler code minimal
4. Test layer size vs latency trade-off
```

### Phase 3: Validation

#### 3.1 Performance Test
```bash
# After implementation, re-measure:
aws logs insights query: ... (same as 1.1)

# Target: Cold start P99 reduced by 30-50%
# Example: 5000ms → 2500ms (50% reduction)
```

#### 3.2 Error Rate Monitoring
```python
# CloudWatch alarm: ErrorRate > 5% → FAIL
# CloudWatch alarm: Duration P99 > 10000ms → FAIL
```

### Success Criteria
- [ ] Cold start latency reduced 30-50%
- [ ] No error rate increase
- [ ] Cost within budget ($0-15/day additional)
- [ ] Performance metrics documented in PERFORMANCE.md

---

## Task T8: CDN Caching Strategy Optimization (Medium Priority)

> **Target**: Cache hit ratio >90% (from ~70% baseline)
> **Discovery**: 1-2 days | Implementation: 3-5 days
> **Timeline**: Week of 2026-03-10

### Phase 1: Analysis (1 day)

#### 1.1 Audit Current Configuration

**AWS CloudFront**:
```bash
aws cloudfront get-distribution --id E1ABC2DEFG3H4I --query 'Distribution.DistributionConfig.CacheBehaviors'
# Check: TTL values, query string handling, compression enabled
```

**Azure CDN**:
```bash
az cdn endpoint rule list --resource-group rg-production --profile-name cdn-prod --name frontend
# Check: Cache rules, compression, query string handling
```

**GCP CDN**:
```bash
gcloud compute backend-buckets describe frontend-cdn --project=ashnova --format=json
# Check: enable-cdn, bucket policies, cache-mode
```

#### 1.2 Current Hit Ratio Analysis
```bash
# CloudWatch (AWS)
aws cloudwatch get-metric-statistics \
  --namespace CloudFront \
  --metric-name CacheHitRate \
  --statistics Average \
  --start-time 2026-03-01 --end-time 2026-03-04

# Application Insights (Azure)
# Portal: CDN → Endpoint → Performance Settings

# Cloud CDN (GCP)
gcloud compute backend-buckets describe frontend-cdn \
  --project=ashnova \
  --format='value(sessionAffinity,connDrainTimeoutSec,enableCDN)'
```

### Phase 2: Implementation (3-5 days)

#### 2.1 Dynamic Content Caching
```
Strategy: Cache HTML index.html with short TTL (300s)
          Cache assets (.js/.css/.woff2) with long TTL (1 month)
          Cache API responses (JSON) with vary header

Implementation:
1. Update Cache-Control headers in application (FastAPI/Express)
2. Configure origin rules for conditional caching
3. Add Vary: Authorization, Accept-Encoding headers
```

**Example: FastAPI cache headers**
```python
# In infrastructure/pulumi/gcp/backend.py or services/api/app/cache.py

@app.get("/")
async def index():
    response = FileResponse("index.html")
    response.headers["Cache-Control"] = "public, max-age=300"  # 5 min
    return response

@app.get("/api/v1/data")
async def get_data():
    response = JSONResponse({"data": [...]})
    response.headers["Cache-Control"] = "private, max-age=60, must-revalidate"
    response.headers["Vary"] = "Authorization"
    return response

@app.get("/assets/{path:path}")
async def serve_asset(path: str):
    response = FileResponse(f"assets/{path}")
    response.headers["Cache-Control"] = "public, max-age=31536000, immutable"  # 1 year
    return response
```

#### 2.2 Query String Handling
```
Problem: Different query strings create separate cache entries
         (?sort=asc vs ?sort=desc == 2 cache entries for same content)

Solution:
- CloudFront: Forward only necessary query strings (not tracking params)
- Azure CDN: Configure Query String Cache Behavior
- GCP CDN: Exclude utm_*, ga_* params from cache key
```

#### 2.3 Compression Configuration
```
Enable gzip/brotli compression:
- HTML, JSON, text: 70-90% reduction
- Images, video: No compression needed
- Binary (woff2): Already compressed
```

#### 2.4 Stale-While-Revalidate
```
Strategy: Serve stale content while origin is down
Header: Cache-Control: public, max-age=3600, stale-while-revalidate=86400
Effect: Better availability during origin maintenance
```

### Phase 3: Validation

#### 3.1 Cache Hit Ratio Test
```bash
# Generate realistic traffic pattern
ab -n 10000 -c 50 -H "User-Agent: Bot" https://www.gcp.ashnova.jp

# Measure hit ratio
aws cloudwatch get-metric-statistics \
  --namespace CloudFront \
  --metric-name CacheHitRate \
  --statistics Average \
  --start-time [after traffic] --end-time [current]

# Target: >90% (from ~70% baseline)
```

#### 3.2 Origin Error Rate
```bash
# Monitor: OriginError count should not increase
# Target: OriginLatency P99 < 2000ms (without cache)
#         EdgeLatency P99 < 100ms (with cache hit)
```

### Success Criteria
- [ ] Cache hit ratio >90%
- [ ] No 4xx/5xx error increase
- [ ] Origin load reduced by >20%
- [ ] Performance metrics documented in PERFORMANCE.md

---

## Task T9: API Rate Limiting Configuration (Medium Priority)

> **Target**: Enforce 100-1000 requests/sec per client
> **Discovery**: 1 day | Implementation: 2-3 days
> **Timeline**: Week of 2026-03-17

### Phase 1: Requirement Analysis (1 day)

#### 1.1 Define Rate Limits
```
Strategy: 3-tier approach

Tier 1: API Gateway level (global)
- 10,000 requests/sec (limit per account)
- Apply to all routes

Tier 2: Endpoint level (per API)
- /api/v1/data: 100 req/sec per IP
- /api/v1/predict: 10 req/sec per IP (expensive ML)
- /api/v1/upload: 2 req/sec per IP (file limits)

Tier 3: User level (authenticated)
- Premium users: 1000 req/sec
- Free users: 100 req/sec
- Anonymous: 10 req/sec
```

#### 1.2 Measurement
```bash
# Current baseline (2026-03-03)
# GET /api/v1/data peak: ??? req/sec
# GET /api/v1/predict peak: ??? req/sec
# POST /api/v1/upload peak: ??? req/sec

# Capture from metrics across clouds:
aws cloudwatch get-metric-statistics \
  --namespace AWS/ApiGateway \
  --metric-name Count \
  --statistics Sum
```

### Phase 2: Implementation (2-3 days)

#### 2.1 AWS API Gateway Throttling
```json
{
  "format": "AWS SAM CloudFormation",
  "Resources": {
    "ApiGateway": {
      "Type": "AWS::ApiGatewayV2::Api",
      "Properties": {
        "ThrottleSettings": {
          "RateLimit": 10000,
          "BurstLimit": 15000
        }
      }
    },
    "ApiGatewayStage": {
      "Type": "AWS::ApiGatewayV2::Stage",
      "Properties": {
        "ThrottleSettings": {
          "RateLimit": 100,
          "BurstLimit": 200
        }
      }
    }
  }
}
```

#### 2.2 Azure Functions Rate Limiting
```python
# In services/api/app/middleware.py

from azure.identity import DefaultAzureCredential
from azure.storage.blob import BlobServiceClient
import time
import json

class RateLimitMiddleware:
    def __init__(self, requests_per_second=100):
        self.requests_per_second = requests_per_second
        self.client_timestamps = {}  # {ip: [ts, ts, ts]}

    async def __call__(self, scope, receive, send):
        client_ip = scope["client"][0]
        current_time = time.time()

        # Clean old timestamps (>1 second ago)
        if client_ip in self.client_timestamps:
            self.client_timestamps[client_ip] = [
                ts for ts in self.client_timestamps[client_ip]
                if current_time - ts < 1.0
            ]
        else:
            self.client_timestamps[client_ip] = []

        # Check rate limit
        if len(self.client_timestamps[client_ip]) >= self.requests_per_second:
            # Return 429 Too Many Requests
            await send({
                "type": "http.response.start",
                "status": 429,
                "headers": [[b"content-type", b"application/json"]],
            })
            await send({
                "type": "http.response.body",
                "body": json.dumps({"error": "Rate limit exceeded"}).encode(),
            })
            return

        # Record this request
        self.client_timestamps[client_ip].append(current_time)

        # Continue with next middleware
        await send(...)
```

#### 2.3 GCP Cloud Armor Rate Limiting
```bash
gcloud compute security-policies create api-ratelimit \
  --description "Rate limiting policy for API endpoints"

gcloud compute security-policies rules create 1000 \
  --security-policy api-ratelimit \
  --action rate-based-ban \
  --rate-limit-options \
    enforce-on-key=IP \
    rate-limit-key=IP \
    rate-limit-per-second=100 \
    --ban-durationSec=3600
```

### Phase 3: Validation

#### 3.1 Load Test with Rate Limit
```bash
# Exceed rate limit by 50%
ab -n 1500 -c 50 https://api.example.com/v1/data
# Expected: 100 requests succeed (rate limit)
#          1400 requests receive 429 Too Many Requests
```

#### 3.2 Legitimate Traffic Test
```bash
# Send traffic at 50 req/sec (below limit)
# Expected: All requests succeed, no 429 errors
```

### Success Criteria
- [ ] API Gateway throttling enforced (100-1000 req/sec per endpoint)
- [ ] 429 responses sent for over-limit requests
- [ ] Legitimate traffic unaffected
- [ ] Metrics documented: rate limit triggers/day

---

## Task T10: Alert & Monitoring Tuning (Low Priority)

> **Target**: False positive reduction <5%, alert SLA accuracy >99%
> **Discovery**: 1 day | Implementation: 2-3 days
> **Timeline**: Week of 2026-03-17

### Phase 1: Current Alert Review (1 day)

#### 1.1 Inventory All Alerts
```bash
# AWS CloudWatch
aws cloudwatch describe-alarms --query 'MetricAlarms[*].{AlarmName,MetricName,Threshold,ComparisonOperator}' --output table

# Azure Monitor
az monitor metrics list-definitions --resource-group rg-production

# GCP Cloud Monitoring
gcloud monitoring alerts list --filter 'displayName:*'
```

#### 1.2 Analyze False Positives
```
Metric: Alert firing rate vs true incident rate
Target: False positive ratio < 5%

For each alert:
- Trigger frequency: ???/week
- False positive count: ???/week
- True incident count: ???/week
- False positive ratio: ???%

Thresholds that need tuning: [list]
```

### Phase 2: Threshold Tuning (2-3 days)

#### 2.1 Example: CPU Utilization Alert
```
BEFORE (too aggressive):
- Threshold: CPU > 50%
- Firing: 20 times/week
- False positives: 19/20 (95% false positive rate) ❌

AFTER (tuned):
- Threshold: CPU > 80% for 5 consecutive minutes
- Firing: 2 times/week
- False positives: 1/2 (50% — still high)

FINAL (optimized):
- Threshold: CPU > 85% for 10 consecutive minutes
- Firing: <1 time/week
- False positives: <5% ✅
```

#### 2.2 Anomaly Detection Integration
```python
# Cloud Monitoring example: One-click anomaly detection
gcloud monitoring alert-policies create \
  --display-name "High Error Rate (Anomaly)" \
  --condition-display-name "ErrorRate > baseline" \
  --condition-threshold-value 0.05 \
  --condition-threshold-duration 60s \
  --condition-threshold-comparison-type COMPARISON_GT \
  --condition-threshold-aggregation-type alignment_mean \
  --notification-channels [channel-id]
```

### Phase 3: SLA Accuracy Validation (1 day)

#### 3.1 Alert Response Time
```
Target: Page engineer < 5 minutes after alert fires

Metric: MTTR (Mean Time To Remediation)
- P50: ???
- P95: ???
- P99: ???

Improvement strategy:
- Update runbooks with step-by-step remediation
- Add auto-remediation for common issues (restart service, clear cache)
- Practice incident response with drill exercises
```

#### 3.2 Alert Documentation
```
For each alert, maintain:
1. Trigger condition (threshold, duration, annotations)
2. Root cause analysis (likely reasons for alert)
3. Runbook: 5-step fix-it guide
4. Escalation path: Who to notify, when to escalate
5. SLA: Expected MTTR, MTR
```

### Success Criteria
- [ ] False positive ratio < 5%
- [ ] Alert SLA accuracy > 99%
- [ ] MTTR P95 < 15 minutes
- [ ] Runbooks complete and tested
- [ ] Alert metrics documented in PERFORMANCE.md

---

## Implementation Timeline

```
Week of 2026-03-03              Week of 2026-03-10           Week of 2026-03-17          Week of 2026-03-24
├─ T6: GCP Prod Deploy          ├─ T7: Coldstart Reduction   ├─ T9: Rate Limiting     └─ T10: Monitoring Tuning
│  (5-10 min)                   │  (3-5 days)                │  (2-3 days)               (2-3 days)
│                               │                             │
│  ✅ Pre-flight script          ├─ T8: CDN Caching          └─ Documentation phase
│  ✅ Deployment plan            │  (3-5 days)
│  ✅ Ready for execution        │
│                               └─ All in parallel
└─ [CRITICAL PATH]
```

---

## Risk Summary

| Task | Risk Level | Mitigation |
|------|-----------|-----------|
| **T6** | 🔴 CRITICAL | Pre-flight checks, state refresh, rollback doc |
| **T7** | 🟡 MEDIUM | Performance test, error monitoring, cost capping |
| **T8** | 🟡 MEDIUM | Cache key analysis, CDN rule testing, origin monitoring |
| **T9** | 🟡 MEDIUM | Load testing, legitimate traffic patterns, user tier mapping |
| **T10** | 🟢 LOW | Threshold validation data, MTTR tracking, runbook reviews |

---

## Resources

- [GCP_PRODUCTION_DEPLOYMENT_PLAN.md](GCP_PRODUCTION_DEPLOYMENT_PLAN.md) — T6 detailed guide
- [AI_AGENT_06_STATUS_JA.md](AI_AGENT_06_STATUS_JA.md) — Operational status & session records
- [deploy-gcp.yml](.github/workflows/deploy-gcp.yml) — GitHub Actions automation (T6 uses this)
- [gcp-production-preflight.sh](../scripts/gcp-production-preflight.sh) — Environment validation script

---

**Next Action**: Execute GitHub Actions workflow for T6 deployment

```bash
# Option 1: GitHub Web (Recommended)
# Actions → "Deploy to GCP" → Run workflow → production

# Option 2: CLI (Manual)
cd /workspaces/multicloud-auto-deploy
bash scripts/gcp-production-preflight.sh
cd infrastructure/pulumi/gcp
pulumi stack select production
pulumi refresh --yes
pulumi up --stack production
```
