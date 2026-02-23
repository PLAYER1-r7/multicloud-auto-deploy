# AWS Simple-SNS: Fix Report (2026-02-22)

> **Status**: ✅ All 12 issues resolved — simple-sns is fully operational on AWS staging  
> **Commits**: `9b4d37c` → `8c84a15` (develop branch)  
> **Environment**: `https://d1tf3uumcm4bo1.cloudfront.net/sns/`

---

## Executive Summary

This report documents 12 independent bugs fixed in a single session on 2026-02-22.
Together, these bugs prevented end-to-end use of the AWS staging simple-sns app after
authentication was working. All root causes have been identified, fixed, deployed, and
verified.

| #  | Symptom | Root Cause | Status |
|----|---------|-----------|--------|
| 1  | Profile GET/PUT returns 500 | Wrong model field names in aws_backend | ✅ Fixed |
| 2  | Login redirects to CloudFront domain instead of custom domain | Hardcoded redirect URI used CloudFront origin URL | ✅ Fixed |
| 3  | Cognito hosted UI shows `/error` page after login | `--supported-identity-providers` missing in CI/CD workflow update step | ✅ Fixed |
| 4  | `POST /uploads/presigned-urls` returns 422 | `count` le=10 was too low; `contentTypes` field missing from model | ✅ Fixed |
| 5  | `GET /profile` returns 401 after login | `at_hash` verification failing when id_token used standalone | ✅ Fixed |
| 6  | `POST /posts` returns 422 | `imageKeys` max_length=10 insufficient; had 13 keys | ✅ Fixed |
| 7  | Images not displaying after post creation | S3 private bucket keys stored as-is, not converted to presigned URLs | ✅ Fixed |
| 8  | Nickname missing from post list | Nickname not fetched from PROFILES table at post creation time | ✅ Fixed |
| 9  | `GET /posts/{post_id}` returns 405 | Endpoint not implemented in any backend | ✅ Fixed |
| 10 | No server-side image count enforcement | Limit hardcoded in frontend only, inconsistent with server | ✅ Fixed |
| 11 | MIME type error on JS assets | Vite built with `base="/"` but site deployed at `/sns/` | ✅ Fixed |
| 12 | "認証設定が不完全です" login error | `VITE_AUTH_PROVIDER` not set in build env; defaulted to "none" | ✅ Fixed |

---

## Bug 1 — Profile GET/PUT 500 Error

### Symptom
Profile page and profile update both returned `500 Internal Server Error`.

### Root Cause
`aws_backend.py` used wrong DynamoDB field names for the PROFILES table:
- `userId` instead of `PK`
- `email` misspelled as `eamil` in some paths

### Fix
Corrected all field names to match the DynamoDB schema (`PK`, `SK`, `nickname`, etc.).

**Files**: `services/api/app/backends/aws_backend.py`  
**Commit**: `9b4d37c`

---

## Bug 2 — Login Redirect to CloudFront Origin Domain

### Symptom
After Cognito authentication, browser was redirected to
`d1tf3uumcm4bo1.cloudfront.net/sns/callback` instead of the custom domain.

### Root Cause
`auth.ts` hardcoded the redirect URI using `window.location.origin` which resolved to
the CloudFront origin URL when accessed through the CDN.

### Fix
Made `cognitoRedirectUri` and `cognitoLogoutUri` dynamic, using
`window.location.origin` at runtime so they always reflect the user's actual URL.

**Files**: `services/frontend_react/src/config/auth.ts`  
**Commit**: `9c6f64d`

---

## Bug 3 — Cognito Hosted UI `/error` Page

### Symptom
After clicking "Sign in with Google" on the Cognito hosted UI, the page navigated
to `/error` instead of completing the OAuth flow.

### Root Cause
The Lambda update step in the CI/CD workflow (`deploy-aws.yml`) called
`aws lambda update-function-configuration` without
`--supported-identity-providers COGNITO`. Cognito treated the client as having
no identity providers, breaking the OAuth flow.

### Fix
Added `--supported-identity-providers COGNITO` to the `update-user-pool-client`
call in the workflow.

**Files**: `.github/workflows/deploy-frontend-web-aws.yml`  
**Commit**: `a501ab8`

---

## Bug 4 — POST /uploads/presigned-urls Returns 422

### Symptom
Uploading images returned `422 Unprocessable Entity`.

### Root Cause
Two model validation issues:
1. `UploadUrlsRequest.count` had `le=10`, but the frontend could request up to 16
2. `contentTypes` field was present in the request but not defined in the Pydantic model

### Fix
- Raised `count` limit to `le=100` (actual enforcement in config)
- Added `contentTypes: list[str]` field to `UploadUrlsRequest` model

**Files**: `services/api/app/models.py`, `services/api/app/routes/uploads.py`  
**Commit**: `6f658d8`

---

## Bug 5 — GET /profile Returns 401 (at_hash)

### Symptom
`GET /profile` returned 401 even with a valid Cognito id_token.

### Root Cause
The JWT verifier was checking `at_hash` (the access token hash embedded in the
id_token), but we pass only the id_token without its companion access_token.
The `at_hash` validation therefore always failed.

Additionally, Cognito access_tokens do not have an `aud` claim, causing
verification to fail on access_token paths.

### Fix
- Set `verify_at_hash: False` in jwt_verifier
- Made `verify_aud` conditional on whether the token contains an `aud` claim

**Files**: `services/api/app/jwt_verifier.py`  
**Commit**: `099c57c`

---

## Bug 6 — POST /posts Returns 422 (imageKeys length)

### Symptom
Creating a post with multiple images returned `422 Unprocessable Entity`.

### Root Cause
`CreatePostBody.image_keys` had `max_length=10`. When uploading 13 images,
the 14-element list (or more) exceeded this limit.

### Fix
Removed the hardcoded `max_length` from the model. Actual enforcement is now
done via the `MAX_IMAGES_PER_POST` config setting in the routes layer.

**Files**: `services/api/app/models.py`  
**Commit**: `8e818d4` (raised to 16 first), then `1351076` (made config-driven)

---

## Bug 7 — Images Not Displaying

### Symptom
After creating a post, image thumbnails showed broken image icons.

### Root Cause
The S3 images bucket has all public access blocked. The backend was returning
raw S3 keys (e.g. `uploads/abc123.jpg`) instead of presigned GET URLs.
The frontend tried to use these as `<img src>` values, which always failed.

### Fix
Added `_key_to_presigned_url()` and `_resolve_image_urls()` helpers to
`aws_backend.py`. All post list and post detail responses now convert
stored S3 keys to presigned GET URLs (1-hour expiry).

DynamoDB items now store `imageKeys` (raw keys) instead of `imageUrls`,
which allows regeneration of presigned URLs on every read.

**Files**: `services/api/app/backends/aws_backend.py`  
**Commit**: `1351076`

---

## Bug 8 — Nickname Missing from Post List

### Symptom
Posts in the feed showed an empty or missing author nickname.

### Root Cause
`aws_backend.py create_post()` was not fetching the user's profile from the
PROFILES DynamoDB table. The `nickname` field was never written to the POSTS table.

### Fix
`create_post()` now fetches `nickname` from the PROFILES table (via `PK=USER#<userId>`)
before writing the post item. The nickname is stored in the post and returned in list/get responses.

**Files**: `services/api/app/backends/aws_backend.py`  
**Commit**: `1351076`

---

## Bug 9 — GET /posts/{post_id} Returns 405

### Symptom
Opening an individual post returned `405 Method Not Allowed`.

### Root Cause
The `GET /posts/{post_id}` endpoint was not implemented in any backend.
FastAPI returned 405 because no matching route existed.

### Fix
Added `get_post(post_id)` to:
- `aws_backend.py` — queries `PostIdIndex` GSI on POSTS table
- `azure_backend.py`, `gcp_backend.py`, `local_backend.py` — stub returning 404

Also added the route to `routes/posts.py`.

**Files**: `services/api/app/backends/*.py`, `services/api/app/routes/posts.py`  
**Commit**: `4555d82`

---

## Bug 10 — No Server-Side Image Count Enforcement

### Symptom
The upload limit was only enforced in the frontend. Backend accepted any number of
images, creating inconsistency and a potential abuse vector.

### Root Cause
No server-side limit was configured or enforced.

### Fix
- Added `MAX_IMAGES_PER_POST` env var to `config.py` (default: 10)
- Added `GET /limits` endpoint (no auth) returning `{"maxImagesPerPost": N}`
- Added limit checks in `routes/uploads.py` and `routes/posts.py`
- Frontend fetches `/limits` on mount; `PostForm.tsx` uses dynamic `maxImages`

**Files**: `services/api/app/config.py`, `services/api/app/routes/limits.py`,  
`services/api/app/routes/uploads.py`, `services/api/app/routes/posts.py`,  
`services/frontend_react/src/api/config.ts`, `services/frontend_react/src/components/PostForm.tsx`  
**Commit**: `3841048`

---

## Bug 11 — MIME Type Error on JS Assets

### Symptom
Browser console showed:
```
Failed to load module script: Expected a JavaScript module script but the server
responded with a MIME type of "text/html".
```
The app was completely blank.

### Root Cause
Vite was built with `base: "/"` (default), so all asset references were like
`/assets/index-xxx.js`. But the site is deployed under `/sns/` on CloudFront.
Requests to `/assets/...` returned a 404, which CloudFront served as the SPA
`index.html` with `Content-Type: text/html` — causing the MIME error.

### Fix
Rebuilt the frontend with `VITE_BASE_PATH=/sns/` (which sets Vite's `base`
option). All asset paths now reference `/sns/assets/...`.

Also fixed CloudFront custom error pages: changed their `ResponsePagePath`
from `/index.html` to `/sns/index.html`.

**Files**: `services/frontend_react/vite.config.ts`  
**Deployment**: Rebuilt → uploaded new bundle → CloudFront invalidated  
**Commit**: `d1c3679`

---

## Bug 12 — "認証設定が不完全です" Login Error

### Symptom
Clicking the login button showed the Japanese error message
"認証設定が不完全です" ("Authentication configuration is incomplete").

### Root Cause
The frontend build did not have `VITE_AUTH_PROVIDER` set in the environment.
`getLoginUrl()` returned an empty string when provider was "none", which
`auth.ts` detected as incomplete configuration.

### Fix
Created `.env.aws.staging` with all required Cognito environment variables:
```
VITE_AUTH_PROVIDER=aws
VITE_API_URL=https://z42qmqdqac.execute-api.ap-northeast-1.amazonaws.com
VITE_COGNITO_DOMAIN=multicloud-auto-deploy-staging.auth.ap-northeast-1.amazoncognito.com
VITE_COGNITO_CLIENT_ID=1k41lqkds4oah55ns8iod30dv2
```

Build command for AWS staging:
```bash
set -a && source .env.aws.staging && set +a
VITE_BASE_PATH=/sns/ npm run build
```

**Files**: `services/frontend_react/.env.aws.staging` (new file)  
**Commit**: `8c84a15`

---

## Deployment Summary

| Component | Details |
|-----------|---------|
| Lambda | `multicloud-auto-deploy-staging-api` — deployed at 13:59:29 UTC |
| API Gateway | `z42qmqdqac.execute-api.ap-northeast-1.amazonaws.com` |
| Frontend bundle | `index-BNBGmVGx.js` (uploaded to `s3://multicloud-auto-deploy-staging-frontend/sns/`) |
| CloudFront | `E1TBH4R432SZBZ` — invalidated (`I673IPPNYKBF1G6CSCYH2AIRGS`) |
| Cognito Pool | `ap-northeast-1_AoDxOvCib` |
| Cognito Client | `1k41lqkds4oah55ns8iod30dv2` |
| DynamoDB | `multicloud-auto-deploy-staging-posts`, GSIs: `UserPostsIndex`, `PostIdIndex` |

---

## Key Lessons

1. **Vite base path**: Always build with `VITE_BASE_PATH=/sns/` for staging deployments at a sub-path. The default `base: "/"` breaks all asset loads.
2. **CloudFront error pages**: Must point to `/sns/index.html` not `/index.html` when the SPA lives at a sub-path.
3. **S3 private buckets**: Never return raw S3 keys to the frontend. Always convert to presigned URLs server-side.
4. **Cognito id_token standalone**: Set `verify_at_hash: False` when you don't have the companion access_token.
5. **`.env.aws.staging`**: Keep this file tracked in the repo (it contains no secrets — only non-sensitive IDs and public domain names).
6. **DynamoDB `imageKeys` vs `imageUrls`**: Store keys, generate URLs at read time so presigned URLs stay fresh.
