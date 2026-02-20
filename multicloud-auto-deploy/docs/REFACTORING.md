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

| File                                   | Reason                                                                                                                                              |
| -------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------- |
| `services/api/app/backends/local.py`   | Old MinIO-object-store backend. Used obsolete `Message` / `MessageCreate` models. Replaced by `local_backend.py`.                                   |
| `services/api/app/backends/aws.py`     | Old AWS DynamoDB backend for messages API. Replaced by `aws_backend.py`.                                                                            |
| `services/api/app/backends/azure.py`   | Old Azure Cosmos DB backend for messages API. Replaced by `azure_backend.py`.                                                                       |
| `services/api/app/backends/gcp.py`     | Old GCP Firestore backend for messages API. Replaced by `gcp_backend.py`.                                                                           |
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

| Test Class          | Tests | Result      |
| ------------------- | ----- | ----------- |
| `TestHealthAndAuth` | 3     | ✅ All pass |
| `TestPostCRUD`      | 4     | ✅ All pass |
| `TestImageUpload`   | 8     | ✅ All pass |
| `TestHashtags`      | 4     | ✅ All pass |

Run with:

```bash
cd services/api
pytest tests/test_simple_sns_local.py -v
```

---

---

## Phase 2 — Tooling Setup (2026-02-20)

This phase added static analysis and automated test tooling for both the Python
API and the React frontend. All changes are on the same branch
(`feature/simple-sns-migration`), committed as `a06527f`.

---

### Overview

| Area | Tool added | Purpose |
|------|-----------|---------|
| Python linting | **ruff 0.9.1** | Replaces flake8 + isort + pyupgrade + flake8-bugbear in one pass |
| Python coverage | **pytest-cov 7.0.0** | HTML + terminal coverage reports for `app/` |
| Frontend tests | **Vitest 3.2.4** | Unit / component test runner (replaces Jest) |
| Frontend DOM | **jsdom 26.1.0** | Simulated browser environment for Vitest |
| Frontend interactions | **@testing-library/react 16.3.0** + **user-event 14.6.1** | Component render + interaction helpers |
| Frontend coverage | **@vitest/coverage-v8 3.2.4** | V8-based coverage provider |

---

### Python — ruff

#### Configuration (`services/api/ruff.toml`)

```toml
[tool.ruff]
target-version = "py311"
line-length = 100

[tool.ruff.lint]
select = ["E", "F", "W", "I", "N", "UP", "B", "SIM", "ARG"]
ignore = [
    "E501",    # line too long — handled by formatter
    "B008",    # FastAPI Depends() in default args is intentional
    "N802",    # function names may be camelCase (nextToken API)
    "N803",    # argument names may be camelCase (nextToken API contract)
    "SIM108",  # ternary operator not always clearer
    "ARG001",  # unused function arguments (overrides / callbacks)
    "ARG002",  # unused method arguments (overrides / callbacks)
]

[tool.ruff.lint.per-file-ignores]
"tests/**" = ["S101", "ARG", "N803"]

[tool.ruff.format]
quote-style = "double"
indent-style = "space"
```

#### How to run

```bash
cd services/api

# Check only (no changes written)
ruff check app/ tests/

# Auto-fix safe violations
ruff check --fix app/ tests/

# Auto-fix including unsafe rewrites (e.g. UP035 typing imports)
ruff check --fix --unsafe-fixes app/ tests/

# Format code (Black-compatible)
ruff format app/ tests/
```

#### Resolution results

| Stage | Violations |
|-------|-----------|
| Initial scan | **342** |
| After `--fix --unsafe-fixes` | **18** |
| After manual fixes | **0** |

The 18 remaining violations after auto-fix and how they were resolved:

| Rule | Count | Resolution |
|------|-------|-----------|
| `N803` | many | Added to global `ignore` list — `nextToken` is part of the upstream API contract |
| `B904` | 10 | Added `from None` / `from exc` to all `raise` statements inside `except` blocks (`azure_backend.py`, `gcp_backend.py`, `local_backend.py`, `main.py`) |
| `B019` | 1 | Added `# noqa: B019` on the `@lru_cache` method in `jwt_verifier.py` (intentional cache on instance method) |
| `SIM117` | 2 | Flattened nested `with patch(…)` blocks into parenthesised multi-context form in `test_backends_integration.py` |
| `F401` | 1 | Changed `from app.backends.base import BackendBase` to `BackendBase as BackendBase` (explicit public re-export) in `backends/__init__.py` |

---

### Python — pytest-cov

#### Configuration changes (`services/api/pytest.ini`)

```ini
[pytest]
addopts =
    --cov=app
    --cov-report=term-missing
    --cov-report=html:htmlcov
    --cov-fail-under=0
asyncio_mode = auto
```

`--cov-fail-under=0` keeps the gate open while coverage is being built up;
raise this threshold as coverage improves.

#### How to run

```bash
cd services/api

# Run all tests with coverage
pytest tests/test_simple_sns_local.py

# Open HTML report after run
open htmlcov/index.html   # macOS
xdg-open htmlcov/index.html  # Linux
```

The `htmlcov/` directory and `.coverage` binary are excluded via
`services/api/.gitignore`.

---

### Frontend — Vitest + React Testing Library

#### Configuration changes (`services/frontend_react/vite.config.ts`)

```ts
test: {
  globals: true,
  environment: 'jsdom',
  setupFiles: ['./src/test/setup.ts'],
  include: ['src/**/*.{test,spec}.{ts,tsx}'],
  coverage: {
    provider: 'v8',
    reporter: ['text', 'html', 'lcov'],
  },
},
```

A `/storage` proxy was also added to `server.proxy` so that presigned MinIO
URLs resolve correctly during local development:

```ts
'/storage': {
  target: 'http://localhost:9000',
  changeOrigin: true,
},
```

#### npm scripts (`services/frontend_react/package.json`)

| Script | Command | Use |
|--------|---------|-----|
| `npm test` | `vitest run` | Single-pass CI run |
| `npm run test:watch` | `vitest` | Interactive watch mode |
| `npm run test:ui` | `vitest --ui` | Browser-based test explorer |
| `npm run test:coverage` | `vitest run --coverage` | Coverage report |

#### Test helper files

| File | Purpose |
|------|---------|
| `src/test/setup.ts` | Imports `@testing-library/jest-dom/vitest` matchers globally |
| `src/test/utils.tsx` | `renderWithProviders()` — wraps UI in a fresh `QueryClientProvider` per test |

`renderWithProviders` creates an isolated `QueryClient` with `retry: false` and
`gcTime: 0` so Tanstack Query state does not leak between tests.

#### Component test files

**`src/components/MessageForm.test.tsx`** — 6 tests

| Test | Assertion |
|------|-----------|
| renders form elements | textarea, tag input, and submit button are present |
| submit disabled when empty | button has `disabled` attribute on mount |
| submit enabled after typing | button becomes active after content is entered |
| calls mutateAsync with correct payload | `content` and `tags` are forwarded to the mutation |
| clears fields after successful submit | both inputs reset to empty |
| ignores blank-only input | submit via `fireEvent` does not call mutation |

**`src/components/MessageItem.test.tsx`** — 13 tests across 3 `describe` blocks

| Block | Tests | What is covered |
|-------|-------|----------------|
| display | 8 | content, nickname, userId fallback, tag badges, no-tag case, image thumbnails, "編集済" label, no label when `createdAt === updatedAt` |
| editing | 3 | enter edit mode, cancel restores original value, save calls `mutateAsync` |
| deletion | 2 | confirm dialog → delete, cancel → no-op |

**Notable fix during test authoring:** In the edit-mode cancel test,
`getByRole('textbox', { name: '' })` was ambiguous because two textboxes are
rendered simultaneously (content and tag). Changed to
`getByDisplayValue('Hello, world!')` to select the content field uniquely.

---

### Tooling Test Results (final state)

#### Python

```
19 passed in 1.65s
```

| Test class | Tests | Status |
|-----------|-------|--------|
| `TestHealthAndAuth` | 3 | ✅ pass |
| `TestPostCRUD` | 4 | ✅ pass |
| `TestImageUpload` | 8 | ✅ pass |
| `TestHashtags` | 4 | ✅ pass |

#### TypeScript

```
19 passed in 1.88s (2 test files)
```

| Test file | Tests | Status |
|-----------|-------|--------|
| `MessageForm.test.tsx` | 6 | ✅ pass |
| `MessageItem.test.tsx` | 13 | ✅ pass |

---

### New and Modified Files (Phase 2)

| File | Status | Change |
|------|--------|--------|
| `services/api/ruff.toml` | **New** | Ruff linter / formatter configuration |
| `services/api/.gitignore` | **New** | Excludes `.coverage`, `htmlcov/`, `.pytest_cache/` |
| `services/api/requirements.txt` | Modified | Added `pytest-cov==7.0.0`, `ruff==0.9.1` |
| `services/api/pytest.ini` | Modified | Added coverage flags to `addopts` |
| `services/api/app/backends/__init__.py` | Modified | Explicit `BackendBase as BackendBase` re-export |
| `services/api/app/backends/azure_backend.py` | Modified | 5× B904 `raise … from None` |
| `services/api/app/backends/gcp_backend.py` | Modified | 3× B904 `raise … from None` |
| `services/api/app/backends/local_backend.py` | Modified | B904 `raise … from exc` |
| `services/api/app/jwt_verifier.py` | Modified | `# noqa: B019` on `@lru_cache` method |
| `services/api/app/main.py` | Modified | B904 `raise … from e` |
| `services/api/tests/test_backends_integration.py` | Modified | SIM117 context-manager flattening, import cleanup |
| `services/api/tests/test_simple_sns_local.py` | Modified | Removed unused `import io` |
| `services/frontend_react/vite.config.ts` | Modified | Vitest config + `/storage` proxy |
| `services/frontend_react/package.json` | Modified | Test scripts + devDependencies |
| `services/frontend_react/tsconfig.app.json` | Modified | Added `"types": ["vitest/globals"]` |
| `services/frontend_react/src/test/setup.ts` | **New** | Vitest global setup (jest-dom matchers) |
| `services/frontend_react/src/test/utils.tsx` | **New** | `renderWithProviders` helper |
| `services/frontend_react/src/components/MessageForm.test.tsx` | **New** | 6 component tests |
| `services/frontend_react/src/components/MessageItem.test.tsx` | **New** | 13 component tests |

---

## File Inventory After Refactoring

### `services/api/app/backends/`

| File               | Status      | Purpose                                         |
| ------------------ | ----------- | ----------------------------------------------- |
| `__init__.py`      | Modified    | Factory: `get_backend()` + `BackendBase` export |
| `base.py`          | Unchanged   | Abstract base class `BackendBase`               |
| `local_backend.py` | Modified    | Local dev: DynamoDB Local + MinIO               |
| `aws_backend.py`   | Unchanged   | AWS: DynamoDB + S3                              |
| `azure_backend.py` | Unchanged   | Azure: Cosmos DB + Blob Storage                 |
| `gcp_backend.py`   | Unchanged   | GCP: Firestore + Cloud Storage                  |
| ~~`local.py`~~     | **Deleted** | Old MinIO-object-store backend                  |
| ~~`aws.py`~~       | **Deleted** | Old DynamoDB messages backend                   |
| ~~`azure.py`~~     | **Deleted** | Old Cosmos DB messages backend                  |
| ~~`gcp.py`~~       | **Deleted** | Old Firestore messages backend                  |
| ~~`factory.py`~~   | **Deleted** | Duplicate factory (broken)                      |
