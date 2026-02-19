# Local Environment Refactoring

**Branch:** `feature/simple-sns-migration`  
**Date:** 2026-02-19  
**Scope:** `services/api`, `services/frontend_web`, `docker-compose.yml`

---

## Summary

This document records all refactoring changes made to the local development environment and the active service source code. The goal was to remove dead code accumulated from the previous messaging-based architecture, fix configuration bugs discovered in the process, modernise deprecated API usage, and add missing HTTP endpoints.

All 19 integration tests pass after the changes (`pytest tests/test_simple_sns_local.py`).

---

## Changes by File

### 1. Deleted — Legacy Backend Files (5 files)

| File | Reason |
|------|--------|
| `services/api/app/backends/local.py` | Old MinIO-object-store backend. Used obsolete `Message` / `MessageCreate` models. Replaced by `local_backend.py`. |
| `services/api/app/backends/aws.py` | Old AWS DynamoDB backend for messages API. Replaced by `aws_backend.py`. |
| `services/api/app/backends/azure.py` | Old Azure Cosmos DB backend for messages API. Replaced by `azure_backend.py`. |
| `services/api/app/backends/gcp.py` | Old GCP Firestore backend for messages API. Replaced by `gcp_backend.py`. |
| `services/api/app/backends/factory.py` | Duplicate `get_backend()` function. Imported from the deleted `local.py`, rendering it broken. The authoritative factory is `backends/__init__.py`. |

All five files imported the obsolete models (`Message`, `MessageCreate`, `MessageUpdate`) that no longer exist in `models.py`. They were not imported by any live code path.

---

### 2. `services/api/app/backends/__init__.py`

**Change:** Removed the `BaseBackend = BackendBase` backward-compatibility alias.

**Before:**
```python
from app.backends.base import BackendBase

# Alias for backward compatibility
BaseBackend = BackendBase
```

**After:**
```python
from app.backends.base import BackendBase
```

**Rationale:** The alias was only consumed by the deleted `factory.py` and the deleted old backend files. No live code referenced `BaseBackend`.

---

### 3. `services/api/app/config.py`

**Changes (2):**

#### 3-a. Fixed `MINIO_BUCKET_NAME` environment variable mismatch

**Before:**
```python
minio_bucket: str = "images"
```

**After:**
```python
# Accepts both MINIO_BUCKET and MINIO_BUCKET_NAME environment variables
minio_bucket: str = Field(
    default="images",
    validation_alias=AliasChoices("minio_bucket", "minio_bucket_name"),
)
```

**Root cause:** `docker-compose.yml` passes `MINIO_BUCKET_NAME=simple-sns` to the `api` service. Pydantic-settings performs case-insensitive matching, so `MINIO_BUCKET_NAME` maps to the field name `minio_bucket_name`. Without an alias, the field defaulted to `"images"` even though the docker-compose intended `"simple-sns"`. This caused presigned URLs to reference the wrong bucket.

#### 3-b. Removed unused `storage_path` field and orphan `import os`

```python
# Removed:
storage_path: str = "./storage"
import os
```

`storage_path` was only referenced by the deleted `local.py` backend. `import os` became unused after that removal.

---

### 4. `services/api/app/backends/local_backend.py`

**Changes (2):**

#### 4-a. Removed redundant inline `import boto3`

The module already imports `boto3` at the top level (line 22). A duplicate `import boto3` existed inside the `generate_upload_urls()` function body. The inline import was removed.

**Before (inside function):**
```python
import boto3
from botocore.config import Config
s3_signing = boto3.client(...)
```

**After:** `boto3` used directly; `from botocore.config import Config` moved to the top-level import block.

#### 4-b. Removed unused `timedelta` import

```python
# Before:
from datetime import datetime, timezone, timedelta

# After:
from datetime import datetime, timezone
```

`timedelta` was imported but never used in the module.

---

### 5. `services/api/app/main.py`

**Change:** Migrated from deprecated `@app.on_event` handlers to the modern `lifespan` context manager (FastAPI ≥ 0.93).

**Before:**
```python
app = FastAPI(title="Simple SNS API", ...)

@app.on_event("startup")
async def startup_event():
    logger.info("Starting Simple SNS API", ...)

@app.on_event("shutdown")
async def shutdown_event():
    logger.info("Shutting down Simple SNS API")
```

**After:**
```python
from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan: startup and shutdown logic."""
    logger.info("Starting Simple SNS API", ...)
    yield
    logger.info("Shutting down Simple SNS API")

app = FastAPI(title="Simple SNS API", ..., lifespan=lifespan)
```

**Additional cleanup:** Consolidated two separate `from fastapi import ...` statements into one.

---

### 6. `services/api/app/routes/posts.py`

**Change:** Added `GET /posts/{post_id}` endpoint.

**Before:** The backend had a `get_post(post_id)` method but no HTTP route exposed it. `frontend_web` worked around this by fetching all posts (`GET /posts?limit=50`) and filtering in Python — an O(n) scan.

**After:**
```python
from fastapi import APIRouter, Depends, HTTPException, Query

@router.get("/{post_id}")
def get_post(post_id: str) -> dict:
    """Retrieve a single post by ID."""
    backend = get_backend()
    try:
        return backend.get_post(post_id)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=404, detail="Post not found") from exc
```

---

### 7. `services/frontend_web/app/routers/views.py`

**Change:** Refactored `post_detail` view to use the new `GET /posts/{post_id}` API endpoint.

**Before (O(n) full scan):**
```python
# Fetched all posts and filtered in Python
data = _fetch_json_with_headers(f"{api}/posts", {"limit": 50}, headers)
for item in data.get("items", []):
    if item.get("postId") == post_id:
        return templates.TemplateResponse("post.html", ...)
raise HTTPException(status_code=404, detail="Post not found")
```

**After (O(1) direct lookup):**
```python
item = _fetch_json_with_headers(f"{api}/posts/{post_id}", None, headers)
return templates.TemplateResponse("post.html", ...)
```

---

### 8. `docker-compose.yml` — MinIO setup correction

**Change:** Added anonymous download access and CORS configuration for the `simple-sns` bucket in the `minio-setup` one-shot container.

**Before:** Only the `images` bucket received `mc anonymous set download` and `mc cors set`. The `simple-sns` bucket (the one configured via `MINIO_BUCKET_NAME=simple-sns`) had neither.

**After:** Both `images` and `simple-sns` buckets receive identical download permissions and CORS setup.

**Impact:** Without this fix, presigned PUT uploads succeeded (HMAC-signed, no public access needed) but plain GET requests to stored images returned `403 Forbidden`.

---

## Bug Discovered and Fixed

### `MINIO_BUCKET_NAME` silently ignored

**Symptom:** Presigned upload URLs referenced the `images` bucket even though `MINIO_BUCKET_NAME=simple-sns` was set in docker-compose.

**Root cause:** Pydantic-settings matches environment variables to field names by converting to lowercase. `MINIO_BUCKET_NAME` → `minio_bucket_name`, which did not match the field `minio_bucket`. The field fell back to the default value `"images"`.

**Fix:** Added `validation_alias=AliasChoices("minio_bucket", "minio_bucket_name")` so either `MINIO_BUCKET` or `MINIO_BUCKET_NAME` is accepted.

---

## Test Results

```
19 passed in 0.53s
```

| Test Class | Tests | Result |
|------------|-------|--------|
| `TestHealthAndAuth` | 3 | ✅ All pass |
| `TestPostCRUD` | 4 | ✅ All pass |
| `TestImageUpload` | 8 | ✅ All pass |
| `TestHashtags` | 4 | ✅ All pass |

Run with:
```bash
cd services/api
pytest tests/test_simple_sns_local.py -v
```

---

## File Inventory After Refactoring

### `services/api/app/backends/`

| File | Status | Purpose |
|------|--------|---------|
| `__init__.py` | Modified | Factory: `get_backend()` + `BackendBase` export |
| `base.py` | Unchanged | Abstract base class `BackendBase` |
| `local_backend.py` | Modified | Local dev: DynamoDB Local + MinIO |
| `aws_backend.py` | Unchanged | AWS: DynamoDB + S3 |
| `azure_backend.py` | Unchanged | Azure: Cosmos DB + Blob Storage |
| `gcp_backend.py` | Unchanged | GCP: Firestore + Cloud Storage |
| ~~`local.py`~~ | **Deleted** | Old MinIO-object-store backend |
| ~~`aws.py`~~ | **Deleted** | Old DynamoDB messages backend |
| ~~`azure.py`~~ | **Deleted** | Old Cosmos DB messages backend |
| ~~`gcp.py`~~ | **Deleted** | Old Firestore messages backend |
| ~~`factory.py`~~ | **Deleted** | Duplicate factory (broken) |
