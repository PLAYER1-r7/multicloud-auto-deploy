# Memory Alert Incident Report — GCP & Azure

**Date**: 2026-02-19 / 2026-02-20  
**Severity**: Sev3 (Warning)  
**Status**: Resolved  
**Affected clouds**: GCP Cloud Functions, Azure Functions (Flex Consumption)

---

## Table of Contents

- [Incident Summary](#incident-summary)
- [GCP Investigation](#gcp-investigation)
- [Azure Investigation](#azure-investigation)
- [Root Cause Summary](#root-cause-summary)
- [Fixes Applied](#fixes-applied)
- [How to Apply](#how-to-apply)
- [Memory Reference Table](#memory-reference-table)
- [Prevention Checklist](#prevention-checklist)

---

## Incident Summary

Two memory alert emails were received within 24 hours:

| Cloud | Alert name                      | Resource                                 | Trigger time            |
| ----- | ------------------------------- | ---------------------------------------- | ----------------------- |
| GCP   | `function-memory-alert`         | `multicloud-auto-deploy-staging-api`     | 2026-02-20              |
| Azure | `function-memory-alert80c16d88` | `multicloud-auto-deploy-production-func` | 2026-02-19 09:37:20 UTC |

Both alerts were **false positives**. Neither function was actually close to running out of memory.

---

## GCP Investigation

### Alert details

```
Fired: Cloud Function - Memory usage is above threshold of 0.9
       with a value of 171208704
```

### Analysis

| Item                      | Value                                   |
| ------------------------- | --------------------------------------- |
| Reported value            | `171,208,704` bytes ≈ **163 MB**        |
| Threshold value in code   | `0.9`                                   |
| Function allocated memory | `512 MB` (`--memory=512MB` in workflow) |
| Actual usage (%)          | 163 MB ÷ 512 MB ≈ **32%** ✅ Normal     |

### Root cause — monitoring threshold bug

```python
# infrastructure/pulumi/gcp/monitoring.py  (BEFORE — incorrect)
threshold_value=0.9,          # BUG: compared against raw bytes, not a ratio
per_series_aligner="ALIGN_DELTA",  # WRONG: user_memory_bytes is a DISTRIBUTION metric
```

The metric `cloudfunctions.googleapis.com/function/user_memory_bytes` returns **absolute byte values**
(e.g. 171,208,704). The threshold was set to `0.9`, meaning the alert fired whenever memory
exceeded **0.9 bytes** — which is effectively always.

The correct threshold for "90% of 512 MB" is:

```
512 × 1024 × 1024 × 0.90 = 483,183,820 bytes  (~460 MB)
```

Additionally, `ALIGN_DELTA` is incorrect for a `DISTRIBUTION` metric.
`ALIGN_PERCENTILE_99` should be used instead.

### Contributing factor — `function.py` event loop leak risk

```python
# services/api/function.py  (BEFORE — per-request loop creation)
loop = asyncio.new_event_loop()
asyncio.set_event_loop(loop)
try:
    loop.run_until_complete(fastapi_app(scope, receive, send))
finally:
    loop.close()
```

Cloud Functions Gen 2 runs on Cloud Run, meaning a **single instance handles multiple requests**.
Creating and closing an event loop on every request causes:

- Repeated memory allocation / deallocation → fragmentation
- Overhead from repeated `asyncio` context setup
- Risk of task leaks if an exception occurs before `loop.close()`

---

## Azure Investigation

### Alert details

```
Fired: Sev3 Azure Monitor Alert function-memory-alert80c16d88
       on multicloud-auto-deploy-production-func (microsoft.web/sites)
       at 2/19/2026 9:37:20 AM
```

### Analysis

| Item                       | Value                            |
| -------------------------- | -------------------------------- |
| Alert threshold in code    | `800,000,000` bytes (**800 MB**) |
| Function App plan          | Flex Consumption                 |
| Default `instanceMemoryMB` | **2048 MB**                      |
| Threshold as % of instance | 800 MB ÷ 2048 MB ≈ **39%**       |

### Root cause — hardcoded threshold far below instance size

```python
# infrastructure/pulumi/azure/monitoring.py  (BEFORE — incorrect)
threshold=800_000_000,  # 800 MB — hardcoded regardless of instance size
```

The Flex Consumption plan defaults to a **2048 MB** instance. Alerting at 800 MB (39% usage)
turns the "memory > 90%" alert into an alert that fires under normal operating conditions.

The correct threshold for "90% of 2048 MB" is:

```
2048 × 1024 × 1024 × 0.90 = 1,932,735,283 bytes  (~1843 MB)
```

### Contributing factor — per-request `import` statements in `function_app.py`

```python
# services/api/function_app.py  (BEFORE — imports inside handler)
async def main(req: func.HttpRequest) -> func.HttpResponse:
    from fastapi import Request          # executed on every request
    from starlette.responses import Response  # executed on every request (unused)
    from io import BytesIO              # executed on every request (unused)
    from urllib.parse import urlparse, parse_qs  # executed on every request
```

Azure Functions Flex Consumption keeps instances warm and **reuses them across requests**.
Placing `import` statements inside the handler function causes Python to resolve module paths
on every call, increasing memory overhead unnecessarily.
`Request`, `Response`, and `BytesIO` were also completely unused, adding dead code.

---

## Root Cause Summary

| Cloud | Type              | Description                                                                 |
| ----- | ----------------- | --------------------------------------------------------------------------- |
| GCP   | **Threshold bug** | `threshold_value=0.9` compared against absolute bytes → always fires        |
| GCP   | **Wrong aligner** | `ALIGN_DELTA` used for `DISTRIBUTION` metric                                |
| GCP   | **Code quality**  | Per-request `asyncio.new_event_loop()` creation → memory fragmentation risk |
| Azure | **Threshold bug** | `threshold=800MB` hardcoded; instance is 2048 MB → fires at 39% usage       |
| Azure | **Code quality**  | `import` statements inside handler → per-request module resolution overhead |
| Azure | **Dead code**     | `Request`, `Response`, `BytesIO` imported but never used                    |

---

## Fixes Applied

### GCP — `infrastructure/pulumi/gcp/monitoring.py`

**Before**

```python
threshold_value=0.9,
per_series_aligner="ALIGN_DELTA",
```

**After**

```python
memory_threshold_bytes = int(function_memory_mb * 1024 * 1024 * 0.9)
threshold_value=memory_threshold_bytes,   # e.g. 483,183,820 for 512 MB
per_series_aligner="ALIGN_PERCENTILE_99", # correct aligner for DISTRIBUTION metrics
```

`function_memory_mb` is now a parameter (default `512`) passed from `__main__.py`
and readable from Pulumi config key `functionMemoryMb`.

### GCP — `infrastructure/pulumi/gcp/__main__.py`

```python
# Read from Pulumi config so it stays in sync with --memory in the deploy workflow
function_memory_mb = config.get_int("functionMemoryMb") or 512

monitoring_resources = monitoring.setup_monitoring(
    ...
    function_memory_mb=function_memory_mb,
)
```

### GCP — `services/api/function.py`

```python
# Module-level shared event loop (created once per instance)
_loop: asyncio.AbstractEventLoop | None = None

def _get_event_loop() -> asyncio.AbstractEventLoop:
    global _loop
    if _loop is None or _loop.is_closed():
        _loop = asyncio.new_event_loop()
        asyncio.set_event_loop(_loop)
    return _loop

@functions_framework.http
def handler(request):
    ...
    loop = _get_event_loop()
    loop.run_until_complete(fastapi_app(scope, receive, send))  # reused across requests
```

### Azure — `infrastructure/pulumi/azure/monitoring.py`

**Before**

```python
threshold=800_000_000,  # hardcoded 800 MB
```

**After**

```python
memory_threshold_bytes = int(memory_limit_mb * 1024 * 1024 * 0.9)
threshold=memory_threshold_bytes,  # e.g. 1,932,735,283 for 2048 MB
```

`memory_limit_mb` is now a parameter (default `2048`) passed from `__main__.py`
and readable from Pulumi config key `functionMemoryMb`.

### Azure — `infrastructure/pulumi/azure/__main__.py`

```python
# Must match the instanceMemoryMB configured in Azure Portal
function_memory_mb = config.get_int("functionMemoryMb") or 2048

monitoring_resources = monitoring.setup_monitoring(
    ...
    function_memory_mb=function_memory_mb,
)
```

### Azure — `infrastructure/pulumi/azure/Pulumi.production.yaml`

```yaml
multicloud-auto-deploy-azure:functionMemoryMb: "2048"
```

### Azure — `services/api/function_app.py`

```python
# BEFORE: imports inside handler (executed on every request)
async def main(req):
    from fastapi import Request       # unused
    from starlette.responses import Response  # unused
    from io import BytesIO            # unused
    from urllib.parse import urlparse, parse_qs

# AFTER: all imports at module top level
import logging
from urllib.parse import urlparse     # parse_qs removed (unused)
from app.main import app as fastapi_app
```

High-frequency `logging.info` calls in the hot path were also downgraded to `logging.debug`
to reduce Application Insights sampling overhead.

---

## How to Apply

### GCP

```bash
cd infrastructure/pulumi/gcp

# (Optional) Override memory if not 512 MB
pulumi config set functionMemoryMb 512 --stack staging

pulumi up --stack staging
pulumi up --stack production
```

Verify in **Cloud Monitoring → Alerting**: the `function-memory-alert` condition display name
should read `Memory usage > 90% (512MB allocated)`.

### Azure

```bash
cd infrastructure/pulumi/azure

# Already set in Pulumi.production.yaml — override only if instance size differs
pulumi config set functionMemoryMb 2048 --stack production

pulumi up --stack staging
pulumi up --stack production
```

Verify in **Azure Monitor → Alerts → Alert rules**: the `function-memory-alert` threshold
should be approximately **1.93 GB**.

> **Note**: If you change `instanceMemoryMB` in Azure Portal (under Function App →
> Scale and concurrency), update `functionMemoryMb` in `Pulumi.[stack].yaml` and redeploy.

---

## Memory Reference Table

### GCP — `--memory` flag values and their 90% thresholds

| `--memory` flag | Allocated     | 90% threshold (bytes)     |
| --------------- | ------------- | ------------------------- |
| `256MB`         | 268,435,456   | 241,591,910               |
| `512MB`         | 536,870,912   | **483,183,820** ← current |
| `1024MB`        | 1,073,741,824 | 966,367,641               |
| `2048MB`        | 2,147,483,648 | 1,932,735,283             |

### Azure — Flex Consumption `instanceMemoryMB` values and their 90% thresholds

| `instanceMemoryMB` | Allocated     | 90% threshold (bytes)       |
| ------------------ | ------------- | --------------------------- |
| `512`              | 536,870,912   | 483,183,820                 |
| `2048`             | 2,147,483,648 | **1,932,735,283** ← current |
| `4096`             | 4,294,967,296 | 3,865,470,566               |

---

## Prevention Checklist

When changing function memory settings in either cloud:

- [ ] Update `functionMemoryMb` in `Pulumi.[stack].yaml` for the affected cloud
- [ ] Run `pulumi up` to redeploy alert thresholds
- [ ] Confirm the alert threshold in the cloud console matches `instanceMemoryMB × 0.9`
- [ ] Verify no false-positive alerts fire within 15 minutes of deployment

General rules for cloud monitoring thresholds:

- **Always use absolute byte values** when the metric returns bytes (GCP `user_memory_bytes`, Azure `MemoryWorkingSet`)
- **Match the aligner to the metric type**: `ALIGN_PERCENTILE_99` for DISTRIBUTION, `ALIGN_RATE` for cumulative counters
- **Never hardcode thresholds** that depend on infrastructure configuration — derive them from a shared config value
- **Test alert policies** after any memory or plan tier change

---

_Report generated: 2026-02-20_  
_Fixed by: GitHub Copilot_  
_Reviewed files: `monitoring.py` (GCP & Azure), `__main__.py` (GCP & Azure), `function.py`, `function_app.py`, `Pulumi.production.yaml` (Azure)_
