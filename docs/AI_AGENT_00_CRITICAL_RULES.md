# 00 — Critical Rules: Read This First

> **This document MUST be read before any other document in this repository.**  
> It contains the minimum set of rules that, if violated, will cause data loss, production outages,
> or hours of wasted debugging. Every point here was learned from a past incident.

---

## After Reading This Document

Once you have read all 15 rules below, continue in this order:

```
1. AI_AGENT_01_OVERVIEW.md   ← what the project is, live endpoints, tech stack (5 min read)
2. AI_AGENT_02_LAYOUT.md     ← directory tree, where each file lives (5 min read)
3. AI_AGENT_03_ARCHITECTURE.md ← system topology, storage path layout (5 min read)
4. AI_AGENT_07_STATUS.md     ← current health of all 3 cloud environments
5. AI_AGENT_10_TASKS.md      ← prioritised backlog — what to work on next
```

Read these only when the task requires it:

```
AI_AGENT_04_API.md      ← endpoint spec, request/response schema, data model
AI_AGENT_05_INFRA.md    ← Pulumi stacks, resource names, config keys, stack outputs
AI_AGENT_06_CICD.md     ← GitHub Actions workflows, required secrets, trigger conditions
AI_AGENT_08_RUNBOOKS.md ← step-by-step: deploy Lambda, deploy React, GCP Cloud Run, etc.
AI_AGENT_09_SECURITY.md ← auth config per cloud, known security gaps
```

---

## Rule 0 — All Documentation Must Be Written in English

All source code comments, commit messages, pull request descriptions, GitHub Actions workflow
comments, Pulumi stack comments, and documentation files **must be written in English**.

This is a multicloud infrastructure project that may be reviewed by engineers across different
teams. Consistency in English ensures every automated tool (search, grep, AI agents) can
process the content correctly.

---

## Rule 1 — File Operations: Never Create or Edit Many Files in a Single Batch

Creating or editing large numbers of files in a single tool invocation batch can cause network
errors or timeouts. This silently corrupts partial results and is very hard to debug.

**Always work incrementally:**

1. Create or edit **a few files** at a time.
2. Verify each step (compilation check, syntax check, test) before continuing.
3. If a network error occurs mid-way, check what was already written before retrying.

---

## Rule 2 — Dev Container Runs on ARM (aarch64); Production is x86_64

The VS Code dev container is built for `linux/aarch64`. All cloud runtimes (Lambda, Azure
Functions, Cloud Run, Cloud Functions) run on `linux/amd64`. **Native Python packages compiled
on aarch64 are binary-incompatible and will crash at runtime with `.so` import errors.**

**Whenever you install Python packages for deployment, always use Docker with the target
platform explicitly set:**

```bash
docker run --rm --platform linux/amd64 \
  -v /tmp/deploy:/out python:3.12-slim \
  bash -c "pip install --no-cache-dir --target /out -r requirements.txt -q"
```

This applies to:

- Lambda ZIP packaging (`requirements-aws.txt`, `requirements-layer.txt`)
- GCP Cloud Functions ZIP packaging (`requirements-gcp.txt`)
- Azure Functions deployment (`requirements-azure.txt`)

Do **not** use `pip install` on the host machine (inside the dev container) for generating
deployment artifacts.

---

## Rule 3 — `.github/workflows/` Lives in the `ashnova/` Repo Root, Not Here

The GitHub Actions workflow files that CI actually reads are in:

```
/workspaces/ashnova/.github/workflows/
```

When VS Code is opened with `multicloud-auto-deploy/` as the workspace root, there is **no
visible `.github/` folder** — but CI still runs. The `multicloud-auto-deploy/.github/`
subdirectory was deleted on 2026-02-21 to eliminate the duplicate.

**To edit any CI/CD workflow:**

```bash
cd /workspaces/ashnova
# then edit .github/workflows/<name>.yml
```

Editing files inside `multicloud-auto-deploy/.github/` (if it ever reappears) has **zero
effect** on CI.

---

## Rule 4 — `main` Branch = Immediate Production Deployment

```
develop  →  staging
main     →  production  ← goes live immediately on push
```

Never push directly to `main` unless you intend to deploy to production right away.
Always work on `develop` (or a feature branch), confirm staging is green, then merge to `main`.

---

## Rule 5 — `AUTH_DISABLED` Must Always Be `false` in Staging and Production

The environment variable `AUTH_DISABLED` must be `false` at all times. It was accidentally set
to `true` in a past incident, silently allowing unauthenticated access to all API endpoints.

If you see `AUTH_DISABLED=true` anywhere in CI workflows, Pulumi configs, or `.env` files,
treat it as a critical bug and fix it immediately.

---

## Rule 6 — Lambda / Cloud Run Env Vars Must Come from Pulumi Outputs, Not GitHub Secrets

A past bug caused silently empty `API_GATEWAY_ENDPOINT` values because the corresponding
GitHub Secret did not exist in the production environment.

**Pattern to follow** (in `deploy-*.yml`):

```yaml
- name: Get Pulumi outputs
  run: |
    cd infrastructure/pulumi/aws
    echo "API_URL=$(pulumi stack output api_url --stack $STACK)" >> $GITHUB_ENV
```

**Never** use `${{ secrets.API_GATEWAY_ENDPOINT }}` or similar for values that can be derived
from `pulumi stack output`. If the secret is absent, the variable silently becomes an empty
string, and the Lambda/Function starts up using a hardcoded fallback (often `localhost:8000`).

---

## Rule 7 — AWS Staging Frontend Must Be Built with `VITE_BASE_PATH=/sns/`

The SNS React app is deployed to `s3://bucket/sns/`. Building without `VITE_BASE_PATH=/sns/`
causes all JS/CSS assets to reference `/assets/...`, resulting in 404s. CloudFront then serves
`index.html` with `Content-Type: text/html` for every asset request — breaking the entire app
with a MIME type error.

```bash
cd services/frontend_react
set -a && source .env.aws.staging && set +a
VITE_BASE_PATH=/sns/ npm run build
```

CloudFront custom error pages must also point to `/sns/index.html`, not `/index.html`.

---

## Rule 8 — S3 Images Bucket Is Private: Always Return Presigned GET URLs

`multicloud-auto-deploy-staging-images` has all public access blocked. The backend
must call `_resolve_image_urls()` before returning posts to the frontend. This converts stored
S3 keys (`imageKeys`) to presigned GET URLs with a 1-hour expiry.

Returning raw S3 keys or caching presigned URLs in the database will result in broken image
links after one hour.

---

## Rule 9 — AWS Production CloudFront: Set Pulumi Config Before Any `pulumi up`

Without the following config, `pulumi up --stack production` will revert CloudFront to the
default certificate, causing `NET::ERR_CERT_COMMON_NAME_INVALID` for all HTTPS visitors.

```bash
cd infrastructure/pulumi/aws
pulumi config set customDomain www.aws.ashnova.jp --stack production
pulumi config set acmCertificateArn \
  arn:aws:acm:us-east-1:278280499340:certificate/914b86b1-4c10-4354-91cf-19c4460dcde5 \
  --stack production
```

Always verify these two config values are present before running `pulumi up` on the production
AWS stack.

---

## Rule 10 — Cognito `id_token` Verification: Set `verify_at_hash: False`

When the frontend sends only the `id_token` (without the companion `access_token`), the JWT
library cannot compute or verify `at_hash`. The call to `jwt_verifier.py` must pass
`verify_at_hash=False`. Reverting this setting breaks all authenticated API calls.

See: `services/api/app/jwt_verifier.py`

---

## Rule 11 — GCP: Always Copy `function.py` as `main.py` in the Deployment ZIP

Cloud Build fails with `missing main.py` even when `--entry-point` names a different function.
The fix is to include `main.py` in the deployment source:

```bash
cp services/api/function.py /tmp/deploy_gcp/.deployment/main.py
```

Always include both `function.py` and `main.py` in the ZIP. Failing to do so causes Cloud
Build to reject the source and the function will not be updated.

---

## Rule 12 — GCP: `generate_signed_url()` Requires `service_account_email` + `access_token`

Cloud Run and Cloud Functions use Compute Engine credentials (access token only — no private
key). Calling `blob.generate_signed_url()` without the extra arguments raises:

```
AttributeError: you need a private key to sign credentials
```

The correct call:

```python
blob.generate_signed_url(
    expiration=3600,
    method="GET",
    service_account_email=settings.gcp_service_account,
    access_token=credentials.token,
)
```

The service account email is provided via env var `GCP_SERVICE_ACCOUNT` on the Cloud Run
service. The SA must also have `roles/iam.serviceAccountTokenCreator`.

---

## Rule 13 — GCP: Firebase Authorized Domains Must Be Registered via Identity Toolkit API

When a new Cloud Run URL or custom domain is added, it must be explicitly registered in
Firebase Auth. Use the Identity Toolkit Admin v2 `PATCH` endpoint with the header
`x-goog-user-project: PROJECT_ID` — omitting this header returns `403 PERMISSION_DENIED`
even with a valid admin token.

This step is automated in `deploy-gcp.yml` (`Update Firebase Authorized Domains`).
Do not remove or skip it.

---

## Rule 14 — GCP: CDN Must Send `Cross-Origin-Opener-Policy: same-origin-allow-popups`

Without this response header, Firebase `signInWithPopup` cannot check `popup.closed`, causing
repeated COOP warnings and potentially breaking the login flow in strict browser environments.

Set this as a CDN backend bucket custom response header (in Pulumi and/or via `gcloud`).
After any change, invalidate the CDN cache:

```bash
gcloud compute url-maps invalidate-cdn-cache <URL_MAP_NAME> \
  --path "/*" --project ashnova
```

---

## Quick Reference: Where to Find What

| Topic                      | File                                                       |
| -------------------------- | ---------------------------------------------------------- |
| Live endpoint URLs         | [AI_AGENT_01_OVERVIEW.md](AI_AGENT_01_OVERVIEW.md)         |
| Repository directory tree  | [AI_AGENT_02_LAYOUT.md](AI_AGENT_02_LAYOUT.md)             |
| System architecture        | [AI_AGENT_03_ARCHITECTURE.md](AI_AGENT_03_ARCHITECTURE.md) |
| API routes & data model    | [AI_AGENT_04_API.md](AI_AGENT_04_API.md)                   |
| Pulumi / IaC               | [AI_AGENT_05_INFRA.md](AI_AGENT_05_INFRA.md)               |
| CI/CD pipelines            | [AI_AGENT_06_CICD.md](AI_AGENT_06_CICD.md)                 |
| Current environment health | [AI_AGENT_07_STATUS.md](AI_AGENT_07_STATUS.md)             |
| Step-by-step runbooks      | [AI_AGENT_08_RUNBOOKS.md](AI_AGENT_08_RUNBOOKS.md)         |
| Security configuration     | [AI_AGENT_09_SECURITY.md](AI_AGENT_09_SECURITY.md)         |
| Remaining tasks / backlog  | [AI_AGENT_10_TASKS.md](AI_AGENT_10_TASKS.md)               |
| Everything — entry point   | [AI_AGENT_GUIDE.md](AI_AGENT_GUIDE.md)                     |
