# Simple SNS Migration & Local Development Setup

**Branch:** `feature/simple-sns-migration`  
**Date:** 2026-02-19  
**Scope:** Local development environment for the Simple SNS application

---

## Overview

This document describes the work done to migrate `simple-sns` services into the
`multicloud-auto-deploy` monorepo and to fix local development issues, including
a multi-step image upload bug through MinIO.

---

## 1. Services Introduced

### `frontend_web` (port 8080)

A server-side rendered (SSR) frontend built with **FastAPI + Jinja2**, ported
from `ashnova.v3/services/web`.

- Multi-auth support: AWS Cognito, Azure AD, GCP OIDC, Firebase Auth, local dev
  mode (`AUTH_DISABLED=true`)
- Cloud deploy targets: AWS Lambda (`handler.py`), Azure Functions
  (`function_app.py`), GCP Cloud Run (`Dockerfile`)
- Static assets: dark/light theme CSS, JS modules (`uploads.js`, `timeline.js`,
  `lightbox.js`, etc.)
- Templates: home, login, profile, post detail, OAuth callback

**Commit:** `b3bbf3c`

---

### `static_site` (port 8090)

A combined static site that serves:

| Path | Content |
|------|---------|
| `/` | Static HTML site (`index.html`, `error.html`) |
| `/sns/` | React SPA (compiled with `VITE_BASE_PATH=/sns/`) |
| `/posts`, `/profiles`, `/uploads`, `/health` | Reverse proxy → `api:8000` |
| `/storage/` | Reverse proxy → `minio:9000` (see §4) |

Built with:
- `static-site/Dockerfile`: multi-stage (`node:20-alpine` build → `nginx:alpine` serve)
- `static-site/nginx.conf`: nginx on port 8090

**Commit:** `515a7ca`

---

## 2. Backend: SQLAlchemy/SQLite → DynamoDB Local + MinIO

The local development backend (`local_backend.py`) was rewritten from
SQLAlchemy/SQLite to use the same storage stack as the AWS production backend.

### DynamoDB Local

| Item type | PK | SK |
|-----------|----|----|
| Post | `POSTS` | `<ISO timestamp>#<uuid>` |
| Profile | `USER#<userId>` | `PROFILE` |

- GSI `PostIdIndex` (hash key: `postId`, projection: ALL) for post detail lookups
- `_ensure_table()` auto-creates the table on startup (polling loop, no waiter)
- `docker-compose.yml`: `amazon/dynamodb-local` service in `-inMemory` mode

### MinIO

- Object storage for post images and profile avatars
- Bucket: `images` (auto-created on startup)
- No external CORS configuration required — MinIO handles `OPTIONS` requests
  natively (`204` with `Access-Control-Allow-Origin: *`)

**Config changes** (`config.py`):

| Field removed | Field added |
|---------------|-------------|
| `database_url` | `dynamodb_endpoint` |
| — | `dynamodb_table_name` |
| — | `minio_public_endpoint` |

**Commit:** `2ea3273`

---

## 3. React SPA Migration

`frontend_react` was updated to work with the new posts/profiles API.

### API Layer Changes

| Before | After |
|--------|-------|
| `/messages/` endpoint | `/posts` endpoint |
| `Message` / `MessagesResponse` types | `Post` / `PostsResponse` types |
| Page/PageSize pagination | Cursor-based pagination (`nextToken`) |
| `author` field | `nickname` / `userId` fields |

Backward-compatible aliases were exported from `useMessages.ts` to keep
component imports stable during transition.

### UI Changes

- Tags input added to `MessageForm`
- `MessageItem` displays tags badge and multiple image thumbnails
- `MessageList` includes tag filter input and cursor-based pagination

### Docker & Dev Server

- `Dockerfile`: multi-stage build (`node:20-alpine` → `nginx:alpine`), port 3001
- `vite.config.ts`: `server.proxy` forwards `/posts`, `/profiles`, `/uploads`,
  `/health` → `http://localhost:8000`, eliminating CORS issues in Vite dev server
- API base URL default changed from `http://localhost:8000` → `""` (relative URL)

**Commits:** `8ed6f61`, `a645a98`, `f73d2c9`

---

## 4. Image Upload Bug Fix

### Problem Chain

Browser console errors:
```
:9000/images/images/test-user-1/xxx.jpg  Failed to load resource: ERR_CONNECTION_REFUSED
TypeError: Failed to fetch
```

The upload flow:
1. `uploads.js` (browser) → `POST /uploads` → get presigned URLs
2. Browser → `PUT <presigned URL>` → upload file directly to MinIO

### Root Cause Analysis

Multiple issues were identified and fixed sequentially:

#### Issue 1 — Wrong API endpoint path

`frontend_web` proxied `POST /uploads` to `API_BASE/uploads`, but the API
endpoint is `POST /uploads/presigned-urls`.

**Fix:** Updated `views.py` to proxy to `/uploads/presigned-urls`.

#### Issue 2 — Wrong response field names

Both backends returned inconsistent field names:

| Component | Before | After |
|-----------|--------|-------|
| `local_backend.py` | `{ uploadUrl, ... }` | `{ url, key }` |
| `aws_backend.py` | `{ upload_url, image_id, public_url }` | `{ url, key }` |

**Fix:** Both backends standardised to `{ "url": "...", "key": "..." }`.

#### Issue 3 — Presigned URL used `minio:9000` (Docker-internal hostname)

The MinIO client was initialised with the internal Docker hostname `minio:9000`.
A presigned URL embedding that hostname is unreachable from the browser.

**Approaches attempted:**

| Approach | Outcome |
|----------|---------|
| String-replace `minio:9000` → `localhost:9000` in URL | FAIL — Host header is included in the AWS Signature (`X-Amz-SignedHeaders=host`); replacing hostname breaks the signature |
| Separate `minio_signing_client` with `localhost:9000` | FAIL — `minio-py` v7.2.9 makes an actual HTTP connection to generate presigned URLs; `localhost:9000` is unreachable from inside the container |
| `boto3 put_bucket_cors` | FAIL — MinIO returns `NotImplemented` |
| **`boto3.generate_presigned_url` with `endpoint_url='http://localhost:9000'`** | **SUCCESS** — Pure local HMAC calculation, no HTTP connection; PUT returned `200 OK` |

**Fix:** Replaced minio-py presigned URL generation with `boto3.generate_presigned_url`
using `endpoint_url=http://localhost:9000`.  
Added `minio_public_endpoint` config field; set `MINIO_PUBLIC_ENDPOINT=http://localhost:9000`
in `docker-compose.yml`.

#### Issue 4 — `localhost:9000` unreachable in dev container

Even with `localhost:9000` in the URL, the browser running inside a VS Code dev
container (Codespaces / Remote Containers) could not reach port 9000 directly,
resulting in `ERR_CONNECTION_REFUSED`.

**Root cause:** The presigned URL must use a hostname the *browser* can reach,
which inside a dev container is the forwarded app port — not a raw MinIO port.

**Fix:** Route all MinIO access through the application server:

```
Before:  browser → PUT http://localhost:9000/images/...      ← ERR_CONNECTION_REFUSED
After:   browser → PUT /storage/images/...   (relative URL, same origin)
                        ↓
              frontend_web :8080  /storage/{path}  →  minio:9000/{path}  ✅
              static_site  :8090  /storage/        →  minio:9000/        ✅
```

**Changes made:**

| File | Change |
|------|--------|
| `local_backend.py` | Sign with `endpoint_url=http://minio:9000`; replace `http://minio:9000` with `/storage` in the returned URL |
| `local_backend.py` | `_build_image_urls()` returns `/storage/{bucket}/{key}` (relative) |
| `views.py` | Added `GET/PUT/HEAD /storage/{path}` reverse proxy handler |
| `static-site/nginx.conf` | Added `location /storage/ { proxy_pass http://minio:9000/; Host: minio:9000; }` |

**Why the signature remains valid:** The presigned URL is signed with
`Host: minio:9000`. The proxy forwards the request to `http://minio:9000/...`
and the `requests` library (Python) / nginx set `Host: minio:9000` accordingly,
so MinIO's signature verification passes.

**Commits:** `3e143ba`, `7fcbd87`

---

## 5. Verified Working State

| Endpoint | Method | Result |
|----------|--------|--------|
| `POST localhost:8000/uploads/presigned-urls` | Direct API | ✅ 200, returns `{ url: "/storage/...", key: "..." }` |
| `POST localhost:8080/uploads` | frontend_web | ✅ 200, returns presigned URLs |
| `PUT  localhost:8080/storage/<presigned path>` | frontend_web proxy | ✅ 200, file stored in MinIO |
| `POST localhost:8090/uploads/presigned-urls` | static_site (nginx) | ✅ 200 |
| `PUT  localhost:8090/storage/<presigned path>` | static_site proxy | ✅ 200 |
| Browser image upload (frontend_web) | End-to-end | ✅ Confirmed |

---

## 6. File Reference

```
multicloud-auto-deploy/
├── docker-compose.yml                          # dynamodb-local, minio, frontend_web, frontend_react, static_site
├── minio-cors.json                             # Reference only (MinIO handles CORS natively)
├── static-site/
│   ├── Dockerfile                              # node build → nginx serve
│   └── nginx.conf                             # port 8090, /sns/ SPA, /storage/ proxy
├── services/
│   ├── api/app/
│   │   ├── config.py                          # + minio_public_endpoint field
│   │   ├── models.py                          # UploadUrl: { url, key }
│   │   └── backends/
│   │       ├── local_backend.py               # DynamoDB Local + MinIO + /storage/ presigned URLs
│   │       └── aws_backend.py                 # { url, key } response
│   ├── frontend_web/app/routers/views.py      # /uploads/presigned-urls + /storage/ proxy
│   └── frontend_react/
│       ├── src/api/client.ts                  # postsApi, relative URL default
│       ├── src/hooks/useMessages.ts           # usePosts (backward-compat aliases)
│       ├── src/components/                    # MessageForm/Item/List updated
│       ├── vite.config.ts                     # VITE_BASE_PATH + dev proxy
│       ├── Dockerfile                         # multi-stage build
│       └── nginx.conf                         # port 3001, SPA fallback
```
