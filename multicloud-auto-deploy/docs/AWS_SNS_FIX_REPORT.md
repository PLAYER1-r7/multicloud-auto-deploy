# AWS Simple-SNS: Fix Report (2026-02-20)

> **Status**: ✅ All issues resolved — simple-sns is fully operational on AWS staging  
> **Commits**: `c5a261c` → `4d2bce0` (develop branch)  
> **Environment**: `https://d1tf3uumcm4bo1.cloudfront.net/sns/`

---

## Executive Summary

This report documents four independent bugs that collectively prevented the AWS staging
simple-sns application from working end-to-end after authentication was enabled.
All four root causes have been identified, fixed, and deployed.

| # | Symptom | Root Cause | Commits | Status |
|---|---------|------------|---------|--------|
| 1 | Profile page shows "Sign in to see profile details" + API base `http://localhost:8000` | CI/CD reset env vars on every push via `ResourceConflictException` | `c5a261c` `2b38fc0` `9ed8200` `17a944f` | ✅ Fixed |
| 2 | CI/CD fixes had no effect across sessions | All previous fixes were applied to the subdirectory copy of the workflow, not the repo-root file that GitHub Actions actually reads | `17a944f` | ✅ Fixed |
| 3 | Logout redirected to `/login` (HTTP 404) | `auth.py` hardcoded `/login`; no CloudFront behavior exists at that path | `cced4cb` | ✅ Fixed |
| 4 | `POST /sns/uploads` returned `502 Bad Gateway` | API model validated `count ≤ 10` and `imageKeys ≤ 10`; frontend allows up to 16 | `0388b3f` `4d2bce0` | ✅ Fixed |

---

## Bug 1 — CI/CD Overwrote Lambda Environment Variables

### Symptom

The profile page displayed:
- _"Sign in to see profile details"_ even when logged in
- API base URL shown as `http://localhost:8000` instead of the real API Gateway URL

### Root Cause

The `deploy-aws.yml` workflow did not update the `frontend-web` Lambda's environment
variables. Therefore, after each CI/CD run, the Lambda retained stale defaults:

```
AUTH_DISABLED=true
API_BASE_URL=""           # falls back to http://localhost:8000 in config
COGNITO_CLIENT_ID=""
```

These values were set once at Lambda creation (by Pulumi) but were never refreshed by CI.

Additionally, the workflow issued `aws lambda update-function-code` while Pulumi's
asynchronous `update-function-configuration` was still in progress. Lambda replied
with `ResourceConflictException`, silently skipping the code update — leaving the
Lambda with wrong env vars permanently.

### Fix

1. Added a **"Update frontend-web Lambda"** step to the root workflow that calls
   `aws lambda update-function-configuration` with the correct values:

   ```yaml
   - name: Update frontend-web Lambda
     run: |
       aws lambda wait function-updated --function-name $FN ...  # pre-flight guard
       aws lambda update-function-configuration \
         --function-name multicloud-auto-deploy-staging-frontend-web \
         --environment "Variables={
           AUTH_DISABLED=false,
           API_BASE_URL=$API_ENDPOINT,
           COGNITO_CLIENT_ID=$CLIENT_ID,
           COGNITO_DOMAIN=$COGNITO_DOMAIN,
           COGNITO_REDIRECT_URI=https://$CF_DOMAIN/sns/auth/callback,
           COGNITO_LOGOUT_URI=https://$CF_DOMAIN/sns/,
           STAGE_NAME=sns,
           AUTH_PROVIDER=aws,
           ENVIRONMENT=staging
         }"
       aws lambda wait function-updated --function-name $FN ...  # completion guard
   ```

2. Added `aws lambda wait function-updated` **before** `update-function-code` to guard
   against the race condition with Pulumi's async configuration update.

---

## Bug 2 — Fixes Were Applied to the Wrong Workflow File

### Symptom

Previous fix sessions applied changes to
`multicloud-auto-deploy/.github/workflows/deploy-aws.yml`
(a subdirectory copy) but the fixes never took effect in CI.

### Root Cause

GitHub Actions reads `.github/workflows/` from the **repository root**, not from
any subdirectory. The project contains two files with the same name:

| Path | Triggered by CI? |
|------|-----------------|
| `.github/workflows/deploy-aws.yml` | ✅ **Yes — this is the real workflow** |
| `multicloud-auto-deploy/.github/workflows/deploy-aws.yml` | ❌ No — ignored by Actions |

All previous fix sessions edited the subdirectory copy;
the root file was missing the `wait` steps and the frontend-web update step entirely.

### Fix

Committed all fixes directly to `.github/workflows/deploy-aws.yml` (repo root).
CI run `#22239547937` confirmed that the "Update frontend-web Lambda" step executed
successfully for the first time.

> **Note for future work**: always edit `.github/workflows/` at the repo root.
> The subdirectory copy at `multicloud-auto-deploy/.github/workflows/` is kept for
> reference only and should not be edited. See `docs/AI_AGENT_06_CICD.md`.

---

## Bug 3 — Logout Redirected to a Non-Existent Path

### Symptom

Clicking logout redirected the user to `/login`, which returns HTTP 404
because CloudFront has no behavior configured for that path.

### Root Cause

`services/frontend_web/app/routers/auth.py` fell back to `redirect_url = "/login"` when
the Cognito logout URL could not be constructed — even though the required env vars
(`COGNITO_DOMAIN`, `COGNITO_CLIENT_ID`, `COGNITO_LOGOUT_URI`) were all correctly set.

Actually, the real issue was that the Lambda env vars were missing (Bug 1), so the fallback
path was always taken. After Bug 1 was fixed the Cognito logout URL is now constructed
correctly. The hardcoded fallback was also changed from `/login` to the app root:

```python
# Before
redirect_url = f"{base_path}/" if base_path else "/"   # fell back to /login

# After (cced4cb)
# Cognito logout URL is now always built:
cognito_logout = (
    f"https://{settings.cognito_domain}/logout"
    f"?client_id={settings.cognito_client_id}"
    f"&logout_uri={quote(settings.cognito_logout_uri)}"
)
redirect_url = cognito_logout
```

The Cognito logout endpoint revokes the session and redirects back to
`COGNITO_LOGOUT_URI=https://d1tf3uumcm4bo1.cloudfront.net/sns/`.

---

## Bug 4 — Image Upload Returned 502 Bad Gateway

### Symptom

```
POST https://d1tf3uumcm4bo1.cloudfront.net/sns/uploads  →  502 Bad Gateway
"Failed to get upload URLs"
```

Selecting and submitting images always failed, regardless of the number of files.

### Root Cause A — `count` validation (0388b3f)

`services/api/app/models.py` defined:

```python
class UploadUrlsRequest(BaseModel):
    count: int = Field(..., ge=1, le=10)   # ← rejects > 10
```

But `uploads.js` allows up to 16 files:

```javascript
if (files.length > 16) { showError("Too many images (max 16)"); return; }
```

Uploading 11–16 files sent `count=11..16` to the API, which returned
`422 Unprocessable Entity`. The frontend-web proxy converts any non-2xx API response
to `502 Bad Gateway`, which is what the browser saw.

### Root Cause B — `imageKeys` validation (4d2bce0)

After fixing `count`, the post-creation step failed with:

```
422 {"detail":[{"type":"too_long","loc":["body","imageKeys"],
"msg":"List should have at most 10 items after validation, not 13", ...}]}
```

`CreatePostBody` and `UpdatePostBody` both had `max_length=10` on `imageKeys`:

```python
image_keys: Optional[list[str]] = Field(None, alias="imageKeys", max_length=10)
```

### Fix

Raised all three limits from `10` to `16` to match the frontend maximum:

```python
# models.py (applies to UploadUrlsRequest, CreatePostBody, UpdatePostBody)
count: int = Field(..., ge=1, le=16)
image_keys: Optional[list[str]] = Field(None, alias="imageKeys", max_length=16)
```

The fix was built into `lambda.zip` and deployed to
`multicloud-auto-deploy-staging-api` immediately without waiting for CI.

---

## Verified End-to-End Flow (Post-Fix)

```
Browser  →  CloudFront (E1TBH4R432SZBZ, d1tf3uumcm4bo1.cloudfront.net)
              /sns/*  →  frontend-web Lambda (Python/FastAPI, Jinja2 SSR)
              /*.png  →  S3 static assets
              (no /api/* behavior — API Gateway is called server-side only)

frontend-web Lambda env vars (confirmed correct 2026-02-20):
  API_BASE_URL      = https://z42qmqdqac.execute-api.ap-northeast-1.amazonaws.com
  AUTH_DISABLED     = false
  COGNITO_CLIENT_ID = 1k41lqkds4oah55ns8iod30dv2
  COGNITO_DOMAIN    = multicloud-auto-deploy-staging.auth.ap-northeast-1.amazoncognito.com
  COGNITO_REDIRECT_URI = https://d1tf3uumcm4bo1.cloudfront.net/sns/auth/callback
  COGNITO_LOGOUT_URI   = https://d1tf3uumcm4bo1.cloudfront.net/sns/
  STAGE_NAME        = sns
  AUTH_PROVIDER     = aws
  ENVIRONMENT       = staging

API Lambda env vars (confirmed correct 2026-02-20):
  AUTH_DISABLED          = false
  AUTH_PROVIDER          = cognito
  AWS_COGNITO_USER_POOL_ID  = ap-northeast-1_AoDxOvCib
  AWS_COGNITO_CLIENT_ID     = 1k41lqkds4oah55ns8iod30dv2
  POSTS_TABLE_NAME       = multicloud-auto-deploy-staging-posts
  IMAGES_BUCKET_NAME     = multicloud-auto-deploy-staging-images
```

### Verified user flows

| Flow | Result |
|------|--------|
| Landing page `https://d1tf3uumcm4bo1.cloudfront.net/` | ✅ |
| SNS app `https://d1tf3uumcm4bo1.cloudfront.net/sns/` | ✅ |
| Cognito-hosted login → redirect back to `/sns/auth/callback` | ✅ |
| Post feed (list posts, pagination) | ✅ |
| Create post (text only) | ✅ |
| Create post with images (up to 16 files) | ✅ |
| Edit post / delete post | ✅ |
| Profile page (nickname, avatar, bio) | ✅ |
| Logout → Cognito revoke → back to `/sns/` | ✅ |
| API health check `/health` | ✅ |
| S3 presigned URL generation | ✅ |

---

## Files Changed

| File | Change |
|------|--------|
| `.github/workflows/deploy-aws.yml` | Added pre-flight `wait`, post-code `wait`, full frontend-web Lambda update step |
| `services/frontend_web/app/routers/auth.py` | Logout uses Cognito hosted logout URL |
| `services/api/app/models.py` | `count`, `imageKeys` limits raised from 10 → 16 |

---

## Remaining Known Limitations (AWS Staging)

| Item | Detail |
|------|--------|
| Production stack | Staging and production share the same resources; an independent production Pulumi stack is not yet deployed |
| WAF | CloudFront distribution has WAF enabled (`WebAcl` attached), but rule tuning is not complete |
| Comments feature | Not implemented in this version of simple-sns |
| GCP / Azure parity | The `count`/`imageKeys` fix in `models.py` applies to all cloud backends; GCP and Azure should be redeployed if they are running the old code |

---

## See Also

- [AI_AGENT_06_CICD.md](AI_AGENT_06_CICD.md) — Which workflow file to edit
- [AI_AGENT_07_STATUS.md](AI_AGENT_07_STATUS.md) — Current environment status
- [AI_AGENT_08_RUNBOOKS.md](AI_AGENT_08_RUNBOOKS.md) — Manual Lambda deploy procedures
- [scripts/test-sns-aws.sh](../scripts/test-sns-aws.sh) — E2E test script for AWS SNS
