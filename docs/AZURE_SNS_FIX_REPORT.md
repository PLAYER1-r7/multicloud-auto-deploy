# Azure Simple-SNS Fix Report

## Overview

Identified and resolved the issue causing the `simple-sns` frontend web app (Azure Functions Python v2)
in the Azure environment to return 503/404 errors, restoring it to full working condition.

---

## Problem Status

| Endpoint                   | Before Fix              | After Fix               |
| -------------------------- | ----------------------- | ----------------------- |
| `GET /sns/health`          | 503 Service Unavailable | 200 `{"status":"ok"}`   |
| `GET /sns/`                | 503 Service Unavailable | 200 HTML Home page      |
| `GET /sns/login`           | 503 Service Unavailable | 200 HTML Login page     |
| `GET /sns/static/app.css`  | 503 Service Unavailable | 200 CSS file            |
| `POST /api/posts` (unauth) | Working                 | 401 (auth guard active) |

---

## Identified Issues and Fixes

### Issue 1: `host.json` JSON Syntax Error (Root Cause — Direct Cause of 503)

**File**: `services/frontend_web/host.json`

```json
// Before fix (❌ invalid JSON)
{
  "version": "2.0",
  "extensions": {"http": {"routePrefix": ""}}
}
}  // ← extra closing brace

// After fix (✅ valid JSON)
{
  "version": "2.0",
  "extensions": {"http": {"routePrefix": ""}},
  "extensionBundle": {
    "id": "Microsoft.Azure.Functions.ExtensionBundle",
    "version": "[4.*, 5.0.0)"
  }
}
```

**Impact**: All endpoints returned 503

---

### Issue 2: Function App Deployment Method Mismatch (Functions Empty)

**Cause**: `WEBSITE_RUN_FROM_PACKAGE` was configured with an external SAS URL. On a Dynamic Consumption (Y1) Linux
plan, when a ZIP is mounted from an external URL, Python v2 programming model functions are not registered.

**Investigation**:

- `admin/functions` → `[]` (empty)
- `admin/host/status` → `state: Running` (host is healthy)
- Application Insights → no traces (Python worker could not detect functions)

**Fix**: Removed the `WEBSITE_RUN_FROM_PACKAGE` setting and switched to `az functionapp deployment source config-zip`
(Kudu ZIP deploy). By extracting code to `/home/site/wwwroot/`,
the Python worker can correctly load `function_app.py`.

```bash
# Before fix (❌ external URL → functions not registered)
WEBSITE_RUN_FROM_PACKAGE = https://mcadfuncd45ihd.blob.core.windows.net/...

# After fix (✅ config-zip deploy)
az functionapp deployment source config-zip \
  --resource-group "multicloud-auto-deploy-staging-rg" \
  --name "multicloud-auto-deploy-staging-frontend-web" \
  --src frontend-web-x86.zip
# → WEBSITE_RUN_FROM_PACKAGE is set automatically (Kudu-managed URL)
```

---

### Issue 3: CPU Architecture Mismatch (pydantic_core Import Error)

**Error**: `ModuleNotFoundError: No module named 'pydantic_core._pydantic_core'`

**Cause**: The development environment is `aarch64` (ARM64), but Azure Functions runs on `x86_64` (AMD64).
Running `pip install --target` locally installs compiled `.so` files for `aarch64`,
which fail to load on Azure due to CPU architecture mismatch.

**Fix**: Build packages using Docker with the `linux/amd64` platform.

```bash
# ❌ Local build (aarch64 → does not work on Azure)
pip3 install pydantic==2.9.0 fastapi==0.115.0 --target build/

# ✅ x86_64 build (using Docker)
docker run --rm \
  --platform linux/amd64 \
  -v "$(pwd):/workspace" \
  python:3.12-slim \
  pip install pydantic==2.9.0 fastapi==0.115.0 --target /workspace/build-x86

# Deploy the created zip
az functionapp deployment source config-zip \
  --src frontend-web-x86.zip ...
```

---

### Issue 4: Relative Path References for Static Files and Templates

**Files**: `services/frontend_web/app/main.py`, `app/routers/views.py`, `app/routers/auth.py`

In Azure Functions, the CWD is not guaranteed, so relative paths do not work.

```python
# ❌ Before fix (relative paths)
StaticFiles(directory="app/static")
Jinja2Templates(directory="app/templates")

# ✅ After fix (absolute paths relative to __file__)
_APP_DIR = os.path.dirname(os.path.abspath(__file__))
StaticFiles(directory=os.path.join(_APP_DIR, "static"))

_TEMPLATES_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "templates")
Jinja2Templates(directory=_TEMPLATES_DIR)
```

---

### Issue 5: Synchronous Handler in `function_app.py`

**Cause**: `AsgiMiddleware.handle()` (synchronous) was being used.

**Fix**: Switched to manual ASGI conversion (same pattern as the API Function App).

```python
# ✅ After fix (manual ASGI + error diagnostics)
_IMPORT_ERROR: str | None = None
fastapi_app = None
try:
    from app.main import app as fastapi_app
except Exception as _e:
    _IMPORT_ERROR = traceback.format_exc()

app = func.FunctionApp(http_auth_level=func.AuthLevel.ANONYMOUS)

@app.function_name(name="Web")
@app.route(route="{*path}", methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"])
async def main(req: func.HttpRequest) -> func.HttpResponse:
    if fastapi_app is None:
        return func.HttpResponse(
            body=f"<h1>Import Error</h1><pre>{_IMPORT_ERROR}</pre>",
            status_code=503
        )
    # ... manual ASGI conversion
```

---

## Deployment Procedure (Reproducible)

```bash
cd multicloud-auto-deploy/services/frontend_web

# 1. Build packages for x86_64
docker run --rm \
  --platform linux/amd64 \
  -v "$(pwd):/workspace" \
  python:3.12-slim \
  bash -c "pip install \
    fastapi==0.115.0 pydantic==2.9.0 pydantic-settings==2.5.2 \
    jinja2==3.1.4 python-multipart==0.0.9 azure-functions==1.20.0 \
    requests==2.32.3 itsdangerous==2.2.0 \
    --target /workspace/build-x86 --quiet"

# 2. Add source code
cp -r app function_app.py host.json requirements.txt build-x86/
touch build-x86/app/__init__.py  # namespace package support

# 3. Create ZIP
cd build-x86 && zip -r ../frontend-web-x86.zip . \
  --exclude "*.pyc" --exclude "__pycache__/*"
cd ..

# 4. Deploy
az functionapp deployment source config-zip \
  --resource-group "multicloud-auto-deploy-staging-rg" \
  --name "multicloud-auto-deploy-staging-frontend-web" \
  --src frontend-web-x86.zip

# 5. Verify
./scripts/test-sns-azure.sh
```

---

## Test Results

```
============================================================
  Azure Simple-SNS — End-to-End Test Suite
============================================================
  Front Door  : https://mcad-staging-d45ihd-dseygrc9c3a3htgj.z01.azurefd.net
  Frontend-web: https://multicloud-auto-deploy-staging-frontend-web.azurewebsites.net
  API Function: https://multicloud-auto-deploy-staging-func-d8a2guhfere0etcq.japaneast-01.azurewebsites.net

Section 1 — Frontend-web Function App (direct)
  ✅  Frontend-web /sns/health returns 200  [HTTP 200]
  ✅    .status == "ok" (FastAPI running)
  ✅  Frontend-web /sns/ returns 200 (HTML)  [HTTP 200]
  ✅    SNS page Content-Type is text/html
  ✅  Frontend-web /sns/login page returns 200 (HTML)  [HTTP 200]
  ✅  Frontend-web /sns/static/app.css returns 200  [HTTP 200]

Section 2 — API Function App (direct)
  ✅  API /api/health returns 200  [HTTP 200]
  ✅    .provider=azure
  ✅  API GET /api/posts returns 200 (unauthenticated)  [HTTP 200]
  ✅    .items array present (16 posts)

Section 3 — Front Door CDN routing
  ✅  Front Door /sns/health via CDN returns 200  [HTTP 200]
  ✅  Front Door /sns/ returns 200 (HTML)  [HTTP 200]
  ✅  Front Door /sns/login returns 200 (HTML)  [HTTP 200]
  ✅  Front Door /sns/static/app.css returns 200 (static file)  [HTTP 200]

Section 4 — Auth guard (unauthenticated = 401)
  ✅  POST /api/posts without token returns 401  [HTTP 401]
  ✅  POST /api/uploads/presigned-urls without token returns 401  [HTTP 401]

Test Results: PASS=16 FAIL=0 SKIP=7 (auth tests require token)
✅ All tests passed!
```

---

## Architecture Overview

```
Browser
  │
  ▼
Azure Front Door (mcad-staging-d45ihd-dseygrc9c3a3htgj.z01.azurefd.net)
  ├── /sns/*  → frontend-web Function App (Consumption Linux, Python 3.12)
  │               FastAPI SSR → templates (Jinja2) + API calls
  │               AUTH_DISABLED=true (Azure AD auth for frontend rendering only)
  │
  └── /*      → Azure Blob Static Web (index.html)

frontend-web → API Function App (Flex Consumption, Python 3.12)
                 (server-side fetch: /api/posts, /api/profile etc.)
                 Cosmos DB (messages/messages container, docType="post")
                 Azure Blob Storage (image upload SAS URL generation)
```

---

## Notes (Ongoing Operations)

1. **Always use `linux/amd64` Docker build for deployment**: If the development environment is ARM64,
   a locally built zip will cause pydantic_core errors on Azure.

2. **Use config-zip**: Setting an external SAS URL directly in `WEBSITE_RUN_FROM_PACKAGE`
   does not register Python v2 model functions on Dynamic Consumption Linux.

3. **Watch for cold starts**: Since this is on the Consumption plan, the first request after an idle period
   may take tens of seconds. The Front Door health probe periodically checks `/sns/health`.

---

## Issue 2: Intermittent 502 Errors via AFD on `/sns/*` ✅ Resolved

> **Investigation Started**: 2026-02-21  
> **Resolved**: 2026-02-25  
> **Target**: `www.azure.ashnova.jp/sns/*` (Production)  
> **Status**: ✅ **Resolved** — 0/20 = 0% failure rate confirmed

### Resolution Summary

**Root Cause**: Dynamic Consumption (Y1) Function App instances are periodically recycled.
AFD Standard cannot detect the TCP disconnect during recycling, leaving a stale connection in its pool.
The next request assigned to the stale connection is immediately returned as 502.

**Fix**: Migrated the production Function App from **Dynamic Consumption (Y1) → FC1 FlexConsumption**
with `maximumInstanceCount=1` + `alwaysReady http=1` to keep exactly one stable instance at all times.

#### Changes Made

| Resource         | Change                                                                                                       |
| ---------------- | ------------------------------------------------------------------------------------------------------------ |
| New Function App | `multicloud-auto-deploy-production-frontend-web-v2` (FC1, `instanceMemoryMB=2048`)                           |
| Scale config     | `maximumInstanceCount=1`, `alwaysReady http=1` (no cold start, no instance churn)                            |
| ZIP deployed     | `frontend-web-prod-new.zip` (x86_64, pydantic_core confirmed)                                                |
| AFD Origin       | `multicloud-auto-deploy-production-frontend-web-origin` → hostName updated to v2                             |
| Old Function App | `multicloud-auto-deploy-production-frontend-web` (Y1) — **stopped** (pending deletion)                       |
| CI/CD Workflow   | `deploy-frontend-web-azure.yml`: `--consumption-plan-location` → `--flexconsumption-location` + scale config |

#### Final Test Results (20 trials, 5-second intervals)

```
After AFD origin switch to v2 + v1 stopped (5-minute edge propagation wait):
  1 – 20: all HTTP 200 (0.09 – 1.76s)
Result: OK=20 NG=0 / 20  ← 0% failure rate
```

#### Key Commands Used

```bash
# Created FC1 FlexConsumption Function App
az functionapp create \
  --name multicloud-auto-deploy-production-frontend-web-v2 \
  --resource-group multicloud-auto-deploy-production-rg \
  --flexconsumption-location japaneast \
  --runtime python --runtime-version 3.12 \
  --storage-account mcadfuncdiev0w

# Scale config: fix to 1 instance, always warm
az functionapp scale config set \
  --name multicloud-auto-deploy-production-frontend-web-v2 \
  --resource-group multicloud-auto-deploy-production-rg \
  --maximum-instance-count 1
az functionapp scale config always-ready set \
  --name multicloud-auto-deploy-production-frontend-web-v2 \
  --resource-group multicloud-auto-deploy-production-rg \
  --settings "http=1"

# Deployed x86_64 ZIP
az functionapp deployment source config-zip \
  --name multicloud-auto-deploy-production-frontend-web-v2 \
  --resource-group multicloud-auto-deploy-production-rg \
  --src services/frontend_web/frontend-web-prod-new.zip

# Updated AFD origin to v2
az afd origin update \
  --resource-group multicloud-auto-deploy-production-rg \
  --profile-name multicloud-auto-deploy-production-fd \
  --origin-group-name multicloud-auto-deploy-production-frontend-web-origin-group \
  --origin-name multicloud-auto-deploy-production-frontend-web-origin \
  --host-name multicloud-auto-deploy-production-frontend-web-v2.azurewebsites.net \
  --origin-host-header multicloud-auto-deploy-production-frontend-web-v2.azurewebsites.net

# Stopped old v1 (stale TCP source)
az functionapp stop \
  --name multicloud-auto-deploy-production-frontend-web \
  --resource-group multicloud-auto-deploy-production-rg
```

#### Lessons Learned

- `--consumption-plan-location` creates Dynamic Y1 → do NOT use with AFD (stale TCP problem)
- `--flexconsumption-location` creates FC1 → stable with `maximumInstanceCount=1`
- Azure Kestrel strips `Connection: close` headers returned by the app (cannot be used as mitigation)
- AFD origin updates take up to 5 minutes for full edge propagation
- `az functionapp update --plan` does not support Linux→Linux plan migration (Windows only)

---

### Symptoms

- AFD-routed access to `www.azure.ashnova.jp/sns/health` returns **HTTP 502 approximately 50% of the time**
- Direct Function App access (`multicloud-auto-deploy-production-frontend-web.azurewebsites.net`) **succeeds 100%**
- 502 responses are returned instantly (**0.08–0.36 seconds**) → AFD is returning the error without attempting a connection to the origin

```
AFD test results (typical example):
  1: 200 (0.27s)
  2: 502 (0.10s)  ← instant
  3: 200 (0.26s)
  4: 502 (0.10s)  ← instant
…
OK=10 NG=10 / 20
```

### Findings

| Item                    | Detail                                                         |
| ----------------------- | -------------------------------------------------------------- |
| Function App (direct)   | 6/6 = 100% HTTP 200                                            |
| Via AFD                 | ~50% HTTP 502 (instant response)                               |
| 502 response body       | AFD standard error HTML (249 bytes) = generated by AFD itself  |
| `x-cache` header        | `CONFIG_NOCACHE` (not cached)                                  |
| AFD Edge Node           | Both 200 and 502 returned from same node `15bbd5d46d5`         |
| AFD DNS                 | 2 IPs: `13.107.246.46`, `13.107.213.46` — same pattern on both |
| Function App HTTP/2     | `http20Enabled: true` (disabling did not improve)              |
| Function App SKU        | Dynamic Consumption (Y1), `alwaysOn: false`                    |
| Function App OS/Runtime | Linux / Python 3.12                                            |

### Attempted Mitigations and Results

| Mitigation                                            | Result                     |
| ----------------------------------------------------- | -------------------------- |
| AFD `originResponseTimeoutSeconds` 30s → 60s          | 502 continues              |
| AFD health probe interval 100s → 30s                  | 502 continues              |
| AFD `sampleSize` 4→2, `successfulSamplesRequired` 3→1 | 502 continues              |
| Function App restart                                  | 502 continues              |
| SNS Route disable → enable                            | 502 continues              |
| `http20Enabled` false (HTTP/2 disabled)               | 502 continues              |
| `WEBSITE_KEEPALIVE_TIMEOUT=30` set                    | 502 continues (monitoring) |
| `pulumi up` (origin group reconfigured)               | 502 continues              |

### Root Cause Hypothesis

**AFD Standard stale TCP connection pool issue**

```
AFD Edge Node
  ├── Connection Pool
  │     ├── Conn A  → Function App instance X (running)  → 200 ✅
  │     └── Conn B  → Function App instance Y (recycled) → TCP disconnected → 502 ❌
  │
  └── New connections succeed immediately; stale connections return 502 instantly
```

On Dynamic Consumption, Function App instances are recycled periodically.
AFD cannot detect the TCP disconnect during recycling and the stale connection remains in the pool.
When the next request is assigned to the stale connection, it immediately returns 502.

**Evidence**:

- 502 is returned instantly (no AFD→origin connection attempted)
- Direct Function App access succeeds 100% (instances themselves are healthy)
- Pattern is regular (one 502 after each recycle, then returns to 200)

### Current Configuration State (2026-02-21)

```bash
# Function App
WEBSITE_KEEPALIVE_TIMEOUT=30    # added
WEBSITE_WARMUP_PATH=/sns/health  # added
http20Enabled=false              # disabled

# AFD Origin Group
probeIntervalInSeconds=30        # 30s (applied via Pulumi)
sampleSize=2                     # relaxed (4→2)
successfulSamplesRequired=1      # relaxed (3→1)

# AFD Profile
originResponseTimeoutSeconds=60  # extended (30s→60s)
```

### Next Investigation Steps (Continue in Separate Chat)

In priority order. Try from the top.

1. **Confirm long-term effect of `WEBSITE_KEEPALIVE_TIMEOUT`**  
   Effect is unclear immediately after setting. Run continuous tests for 30+ minutes to check for improvement.

   ```bash
   OK=0; NG=0
   for i in $(seq 1 30); do
     CODE=$(curl -s -o /dev/null -w "%{http_code}" --max-time 15 "https://www.azure.ashnova.jp/sns/health")
     if [ "$CODE" = "200" ]; then ((OK++)); else ((NG++)); echo "FAIL $i: $CODE"; fi
     sleep 60  # 30 times at 1-minute intervals = 30 minutes
   done
   echo "OK=$OK NG=$NG / 30"
   ```

2. **Add `Connection: close` header via AFD Rule Set** (most promising)  
   Force AFD→origin TCP connections to be created fresh each time (no Keep-Alive).
   → Requires deployment (see "Services Requiring Deployment" below)

3. **Adjust `WEBSITE_IDLE_TIMEOUT_IN_MINUTES`**  
   Extend Function App instance idle timeout to suppress instance recycling.

   ```bash
   az functionapp config appsettings set \
     --name multicloud-auto-deploy-production-frontend-web \
     --resource-group multicloud-auto-deploy-production-rg \
     --settings "WEBSITE_IDLE_TIMEOUT_IN_MINUTES=60"
   ```

4. **Migrate to Flex Consumption**  
   Using Flex Consumption instead of Dynamic Consumption (Y1) enables
   `instanceMemoryMB` / `maximumInstanceCount` settings, stabilizing instances.
   Requires changing `kind` + `serverFarmId` in Pulumi's `azure.web.WebApp`.

5. **Consider migrating to AFD Premium SKU**  
   There may be a connection pool management issue with AFD Standard.
   Premium allows Private Link connections with different behavior.
   Significant cost increase — last resort.

6. **File an Azure Support ticket**  
   This may be a known stale connection issue with AFD Standard + Dynamic Consumption.

---

### Setup for Resuming Investigation (Required Tools)

Commands used during investigation, plus tools useful to have ready for next time.

#### 1. Environment Variables (Set Each Time)

```bash
export RG="multicloud-auto-deploy-production-rg"
export FD="multicloud-auto-deploy-production-fd"
export EP="mcad-production-diev0w"
export OG="multicloud-auto-deploy-production-frontend-web-origin-group"
export ORIGIN="multicloud-auto-deploy-production-frontend-web-origin"
export FUNC_WEB="multicloud-auto-deploy-production-frontend-web"
export HOSTNAME="multicloud-auto-deploy-production-frontend-web.azurewebsites.net"
export AFD_URL="https://www.azure.ashnova.jp"
```

#### 2. 502 Rate Check Script (Standard Test)

```bash
# 10 tests (5-second intervals)
OK=0; NG=0
for i in $(seq 1 10); do
  TIMING=$(curl -s -o /dev/null -w "%{http_code}/%{time_total}" --max-time 15 "$AFD_URL/sns/health")
  CODE="${TIMING%%/*}"; TIME="${TIMING##*/}"
  if [ "$CODE" = "200" ]; then ((OK++)); else ((NG++)); fi
  echo "  $i: $CODE (${TIME}s)"
  sleep 5
done
echo "OK=$OK NG=$NG / 10"
```

#### 3. AFD Test by IP (Identify Which Edge Node Has the Problem)

```bash
# Get AFD IPs (usually returns 2)
python3 -c "
import socket
ips = list(set([r[4][0] for r in socket.getaddrinfo('www.azure.ashnova.jp', 443, socket.AF_INET)]))
print('AFD IPs:', ips)
"

# Test pinned to a specific IP
IP1="13.107.246.46"
IP2="13.107.213.46"
for IP in $IP1 $IP2; do
  echo "=== $IP ==="
  for i in $(seq 1 5); do
    CODE=$(curl -s -o /dev/null -w "%{http_code}" --max-time 15 \
      --resolve "www.azure.ashnova.jp:443:$IP" "$AFD_URL/sns/health")
    echo "  $i: $CODE"; sleep 3
  done
done
```

#### 4. Check Current AFD Configuration

```bash
# Origin Group settings
az afd origin-group show --profile-name $FD --resource-group $RG \
  --origin-group-name $OG \
  --query "{loadBalancing:loadBalancingSettings, healthProbe:healthProbeSettings}" -o json

# Origin settings
az afd origin show --profile-name $FD --resource-group $RG \
  --origin-group-name $OG --origin-name $ORIGIN \
  --query "{hostname:hostName, enabled:enabledState, priority:priority}" -o json

# Route settings
az afd route list --profile-name $FD --resource-group $RG --endpoint-name $EP \
  --query "[].{name:name, patterns:patternsToMatch, enabled:enabledState}" -o table
```

#### 5. Check Function App Configuration

```bash
az functionapp show --name $FUNC_WEB --resource-group $RG \
  --query "{sku:sku, state:state, alwaysOn:siteConfig.alwaysOn, http20:siteConfig.http20Enabled}" -o json

az functionapp config appsettings list --name $FUNC_WEB --resource-group $RG \
  --query "[?name=='WEBSITE_KEEPALIVE_TIMEOUT' || name=='WEBSITE_WARMUP_PATH' || name=='WEBSITE_IDLE_TIMEOUT_IN_MINUTES'].{name:name,value:value}" -o table
```

#### 6. DNS Lookup Without `dig` (Not Installed in This Container)

```bash
# Alternative to dig
python3 -c "
import socket
host = 'www.azure.ashnova.jp'
for af, name in [(socket.AF_INET, 'IPv4'), (socket.AF_INET6, 'IPv6')]:
    try:
        ips = list(set([r[4][0] for r in socket.getaddrinfo(host, 443, af)]))
        print(f'{name}: {ips}')
    except: print(f'{name}: none')
"

# To install dig
sudo apt-get install -y dnsutils
```

---

### Services Requiring Deployment

Based on the investigation, deploying the following Azure services is considered effective.

#### Priority HIGH: AFD Rule Set (`Connection: close` header)

Fundamental fix for stale TCP connection issue. Forces AFD→Function App HTTP connections to be created fresh each time.

**Pulumi code insertion point**: `infrastructure/pulumi/azure/__main__.py`

```python
# AFD Rule Set: Force Connection: close to prevent stale connections
frontend_web_rule_set = azure.cdn.RuleSet(
    "frontdoor-frontend-web-rule-set",
    rule_set_name=f"{project_name}-{stack}-fw-rs",
    profile_name=frontdoor_profile.name,
    resource_group_name=resource_group.name,
)

frontend_web_connection_close_rule = azure.cdn.Rule(
    "frontdoor-connection-close-rule",
    rule_name="ForceConnectionClose",
    rule_set_name=frontend_web_rule_set.name,
    profile_name=frontdoor_profile.name,
    resource_group_name=resource_group.name,
    order=1,
    # No conditions = apply to all requests
    conditions=[],
    actions=[
        azure.cdn.DeliveryRuleResponseHeaderActionArgs(
            name="ModifyResponseHeader",
            parameters=azure.cdn.HeaderActionParametersArgs(
                type_name="DeliveryRuleHeaderActionParameters",
                header_action="Overwrite",
                header_name="Connection",
                value="close",
            ),
        )
    ],
)

# Add to frontdoor_sns_route's rule_sets
# frontdoor_sns_route = azure.cdn.Route(
#     ...
#     rule_sets=[azure.cdn.ResourceReferenceArgs(id=frontend_web_rule_set.id)],
#     ...
# )
```

To try via CLI first:

```bash
# Create rule set
az afd rule-set create \
  --resource-group $RG --profile-name $FD \
  --rule-set-name fwconnclose

# Add rule (Connection: close)
az afd rule create \
  --resource-group $RG --profile-name $FD \
  --rule-set-name fwconnclose \
  --rule-name ForceConnectionClose \
  --order 1 \
  --action-name ModifyResponseHeader \
  --header-action Overwrite \
  --header-name Connection \
  --header-value close

# Attach rule set to SNS Route
az afd route update \
  --resource-group $RG --profile-name $FD \
  --endpoint-name $EP --route-name multicloud-auto-deploy-production-sns-route \
  --rule-sets fwconnclose
```

#### Priority MEDIUM: Migrate to Flex Consumption Plan

Change Dynamic Consumption (Y1) → Flex Consumption to improve instance stability.
**Note**: Requires changes to Pulumi code. Since the current Function App was deployed manually, changes may need to be made outside Pulumi.

```bash
# Check current plan
az functionapp show --name $FUNC_WEB --resource-group $RG \
  --query "{planName:serverFarmId, sku:sku}" -o json

# Create Flex Consumption plan (Japan East)
az functionapp plan create \
  --resource-group $RG \
  --name multicloud-auto-deploy-production-flex-plan \
  --location japaneast \
  --sku FC1 \
  --is-linux true

# Migrate Function App to new plan
az functionapp update \
  --name $FUNC_WEB \
  --resource-group $RG \
  --plan multicloud-auto-deploy-production-flex-plan
```

### Related Commits

| Commit     | Description                                                                             |
| ---------- | --------------------------------------------------------------------------------------- |
| `9ed48d6`  | CI/CD bug fix (issue where SNS dist overwrote `$web`)                                   |
| `27a44af`  | AFD timeout extension, warmup settings, landing page fix                                |
| `(latest)` | `WEBSITE_KEEPALIVE_TIMEOUT=30`, `http20Enabled=false`, AFD origin group reconfiguration |
