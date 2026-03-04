# 05 — CI/CD Pipelines

> Part II — Architecture & Design | Parent: [AI_AGENT_GUIDE.md](AI_AGENT_GUIDE.md)

---

## Workflow List

> ⚠️ Always edit the repo-root `.github/workflows/`.
> `multicloud-auto-deploy/.github/workflows/` is ignored by CI.

| File                            | Trigger                    | Target                           | Environment          |
| ------------------------------- | -------------------------- | -------------------------------- | -------------------- |
| `deploy-aws.yml`                | push: develop/main, manual | Lambda + API                     | staging / production |
| `deploy-azure.yml`              | push: develop/main, manual | Functions + API                  | staging / production |
| `deploy-gcp.yml`                | push: develop/main, manual | Cloud Run (API)                  | staging / production |
| `deploy-frontend-aws.yml`       | push: develop/main, manual | S3 `sns/`                        | staging / production |
| `deploy-frontend-azure.yml`     | push: develop/main, manual | Blob `$web/sns/`                 | staging / production |
| `deploy-frontend-gcp.yml`       | push: develop/main, manual | GCS `sns/`                       | staging / production |
| `deploy-frontend-web-aws.yml`   | push: develop/main, manual | Lambda (frontend-web)            | staging / production |
| `deploy-frontend-web-azure.yml` | push: develop/main, manual | Functions (frontend-web)         | staging / production |
| `deploy-frontend-web-gcp.yml`   | push: develop/main, manual | Cloud Run (frontend-web, Docker) | staging / production |
| `deploy-landing-aws.yml`        | push: develop/main, manual | S3 `/`                           | staging / production |
| `deploy-landing-azure.yml`      | push: develop/main, manual | Blob `$web/`                     | staging / production |
| `deploy-landing-gcp.yml`        | push: develop/main, manual | GCS `/`                          | staging / production |

---

## Branch → Environment Mapping

```
develop  →  staging
main     →  production  ⚠️ goes live immediately
```

---

## Trigger Conditions (path filters)

> ⚠️ **Cloud-specific deployments**: Each workflow monitors only cloud-specific paths to prevent unnecessary deployments.

### Backend API (`deploy-{aws,azure,gcp}.yml`)

| Changed path                         | Workflow triggered      |
| ------------------------------------ | ----------------------- |
| `services/api/**`                    | All clouds (shared API) |
| `infrastructure/pulumi/aws/**`       | AWS only                |
| `infrastructure/pulumi/azure/**`     | Azure only              |
| `infrastructure/pulumi/gcp/**`       | GCP only                |
| `.github/config/aws.*.env`           | AWS only                |
| `.github/config/azure.*.env`         | Azure only              |
| `.github/config/gcp.*.env`           | GCP only                |
| `.github/workflows/deploy-aws.yml`   | AWS only                |
| `.github/workflows/deploy-azure.yml` | Azure only              |
| `.github/workflows/deploy-gcp.yml`   | GCP only                |

### Frontend React SPA (`deploy-frontend-web-{aws,azure,gcp}.yml`)

| Changed path                              | Workflow triggered      |
| ----------------------------------------- | ----------------------- |
| `services/frontend_react/**`              | All clouds (shared)     |
| `.github/config/aws.*.env`                | AWS only                |
| `.github/config/azure.*.env`              | Azure only              |
| `.github/config/gcp.*.env`                | GCP only                |
| `.github/workflows/deploy-frontend-web-*` | Respective cloud only   |

### Landing Page (`deploy-landing-{aws,azure,gcp}.yml`)

| Changed path                           | Workflow triggered      |
| -------------------------------------- | ----------------------- |
| `static-site/**`                       | All clouds (shared)     |
| `.github/config/aws.*.env`             | AWS only                |
| `.github/config/azure.*.env`           | Azure only              |
| `.github/config/gcp.*.env`             | GCP only                |
| `.github/workflows/deploy-landing-*`   | Respective cloud only   |

---

## Cloud Config Files (.github/config/)

> **Single source of truth** for stable, per-environment values that were previously fragmented across GitHub Secrets, inline `case/esac` blocks, and gitignored `Pulumi.*.yaml` files.

### Location

```
.github/config/
  aws.production.env
  aws.staging.env
  azure.production.env
  azure.staging.env
  gcp.production.env
  gcp.staging.env
```

### What is stored here

| Cloud | Key                                | Example value                        |
| ----- | ---------------------------------- | ------------------------------------ |
| All   | `CLOUD_CUSTOM_DOMAIN`              | `www.gcp.ashnova.jp`                 |
| Azure | `CLOUD_AZURE_CLIENT_ID`            | `0b926ff6-...` (AD app registration) |
| Azure | `CLOUD_AZURE_TENANT_ID`            | `a3182bec-...`                       |
| AWS   | `CLOUD_ACM_CERT_ARN`               | `arn:aws:acm:us-east-1:...`          |
| AWS   | `CLOUD_CLOUDFRONT_DOMAIN`          | `d1qob7569mn5nw.cloudfront.net`      |
| AWS   | `CLOUD_CLOUDFRONT_DISTRIBUTION_ID` | `E214XONKTXJEJD`                     |

### How workflows use it

Every main deploy workflow (`deploy-aws.yml`, `deploy-azure.yml`, `deploy-gcp.yml`) includes a **`Load Cloud Config`** step immediately after `Determine Pulumi Stack Name`:

```bash
CONFIG_FILE=".github/config/aws.${STACK_NAME}.env"
source "$CONFIG_FILE"
echo "custom_domain=$CLOUD_CUSTOM_DOMAIN" >> $GITHUB_OUTPUT
# ... other outputs
```

All subsequent steps reference `${{ steps.cloud_config.outputs.custom_domain }}` etc. instead of any fallback logic.

### When to update

| Event                      | Action                                              |
| -------------------------- | --------------------------------------------------- |
| Custom domain changes      | Update `CLOUD_CUSTOM_DOMAIN` in the relevant `.env` |
| ACM cert renewed (AWS)     | Update `CLOUD_ACM_CERT_ARN`                         |
| Azure AD app re-registered | Update `CLOUD_AZURE_CLIENT_ID`                      |
| New stack added            | Add a new `<cloud>.<stack>.env` file                |

### Why NOT in GitHub Secrets

Repo-level GitHub Secrets are **environment-agnostic**. Setting `AZURE_CUSTOM_DOMAIN=www.azure.ashnova.jp` at repo level means the staging deploy also receives the production domain. Environment-level Secrets solve this but must be configured in the GitHub UI and are invisible to code review. Config files in `.github/config/` are git-tracked, diff-visible, and require no GitHub UI maintenance.

---

## Required GitHub Secrets

### AWS

| Secret                  | Purpose                 |
| ----------------------- | ----------------------- |
| `AWS_ACCESS_KEY_ID`     | IAM access key          |
| `AWS_SECRET_ACCESS_KEY` | IAM secret key          |
| `PULUMI_ACCESS_TOKEN`   | Pulumi Cloud auth token |

> ⚠️ `AWS_CUSTOM_DOMAIN`, `AWS_ACM_CERTIFICATE_ARN`, `AWS_CLOUDFRONT_DOMAIN` are **no longer used**.
> These values are now read from `.github/config/aws.<stack>.env`.

### Azure

| Secret                  | Purpose                                                        |
| ----------------------- | -------------------------------------------------------------- |
| `AZURE_CREDENTIALS`     | Service Principal JSON (`az ad sp create-for-rbac --sdk-auth`) |
| `AZURE_SUBSCRIPTION_ID` | Subscription ID                                                |
| `AZURE_RESOURCE_GROUP`  | Resource group name                                            |
| `PULUMI_ACCESS_TOKEN`   | Pulumi Cloud auth token                                        |

> ⚠️ `AZURE_CUSTOM_DOMAIN` is **no longer used** in `deploy-azure.yml`.
> `CLOUD_CUSTOM_DOMAIN`, `CLOUD_AZURE_CLIENT_ID`, `CLOUD_AZURE_TENANT_ID` are read from `.github/config/azure.<stack>.env`.

### GCP

| Secret                 | Purpose                                             |
| ---------------------- | --------------------------------------------------- |
| `GCP_CREDENTIALS`      | Service account JSON                                |
| `GCP_PROJECT_ID`       | Project ID (`ashnova`)                              |
| `GCP_API_ENDPOINT`     | Cloud Run API URL (for frontend-web `API_BASE_URL`) |
| `FIREBASE_API_KEY`     | Firebase Web API key (for frontend-web auth)        |
| `FIREBASE_AUTH_DOMAIN` | Firebase Auth domain (for frontend-web auth)        |
| `FIREBASE_APP_ID`      | Firebase App ID (for frontend-web auth)             |
| `PULUMI_ACCESS_TOKEN`  | Pulumi Cloud auth token                             |

---

## Deploy Flow (AWS backend example)

```yaml
# deploy-aws.yml steps (summary)
1. Checkout
2. AWS auth (aws-actions/configure-aws-credentials)
3. Set up Python 3.13
4. Pulumi login (PULUMI_ACCESS_TOKEN)
5. Determine Pulumi Stack Name  →  STACK_NAME = staging | production
6. Load Cloud Config  →  source .github/config/aws.${STACK_NAME}.env
   # Outputs: custom_domain, acm_cert_arn, cloudfront_domain
7. pulumi up --stack staging  # create/update infrastructure
8. Get Pulumi Outputs  →  bucket name, CloudFront ID, Cognito IDs, etc.
9. Build Lambda Layer (./scripts/build-lambda-layer.sh)
10. Publish Lambda Layer  (name = multicloud-auto-deploy-${STACK_NAME}-dependencies)
11. Package app code as ZIP (app/ + index.py)
12. Update Lambda function code
13. Update Lambda environment variables
    - CLOUD_PROVIDER=aws
    - AUTH_DISABLED=false
    - AUTH_PROVIDER=cognito
    - COGNITO_USER_POOL_ID (from Pulumi output)
    - COGNITO_CLIENT_ID (from Pulumi output)
```

## Deploy Flow (frontend example)

```yaml
# deploy-frontend-aws.yml steps (summary)
1. Checkout
2. AWS auth
3. Set up Node.js
4. npm ci
5. Retrieve S3 bucket name and CloudFront ID from Pulumi output
6. Set VITE_API_URL and run npm run build
   # vite.config.ts: base="/sns/" is already set
7. aws s3 sync dist/ s3://{bucket}/sns/ --delete
8. CloudFront cache invalidation (/*)
```

---

## Manual Deploy (emergency)

```bash
# Trigger a workflow manually via GitHub CLI
gh workflow run deploy-aws.yml \
  --ref develop \
  -f environment=staging

gh workflow run deploy-frontend-gcp.yml \
  --ref main \
  -f environment=production

# Check run status
gh run list --workflow=deploy-aws.yml --limit 5
gh run watch <run-id>
```

---

## CI/CD Current Status (2026-02-24)

| Workflow                     | Branch  | Status | Commit    |
| ---------------------------- | ------- | ------ | --------- |
| Deploy Frontend Web to GCP   | develop | ✅     | `0ed0805` |
| Deploy to GCP (Pulumi + API) | develop | ✅     | `0ed0805` |
| Deploy Frontend to GCP       | develop | ✅     | `591ce0b` |
| Deploy Frontend to AWS       | develop | ✅     | `591ce0b` |
| Deploy Frontend to Azure     | develop | ✅     | `591ce0b` |
| Deploy Landing to GCP        | develop | ✅     | `591ce0b` |
| Deploy Landing to AWS        | develop | ✅     | `591ce0b` |
| Deploy Landing to Azure      | develop | ✅     | `591ce0b` |

---

## Past CI Bugs Fixed (watch for recurrence)

| Bug                                                                 | Symptom                                                                                                                                                                                                 | Fix                                                                                                                                                                                          |
| ------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Workflow file duplication                                           | Editing subdirectory only → not reflected in CI                                                                                                                                                         | Edit root `.github/workflows/`                                                                                                                                                               |
| `deploy-landing-gcp.yml` auth method                                | `workload_identity_provider` (secret not set)                                                                                                                                                           | Changed to `credentials_json: ${{ secrets.GCP_CREDENTIALS }}`                                                                                                                                |
| `deploy-landing-aws.yml` auth method                                | `role-to-assume` (secret not set)                                                                                                                                                                       | Changed to `aws-access-key-id` + `aws-secret-access-key`                                                                                                                                     |
| Frontend overwrote landing page                                     | `dist/` synced to bucket root                                                                                                                                                                           | Changed to sync `dist/` under `sns/` prefix                                                                                                                                                  |
| AWS/Azure staging had `AUTH_DISABLED=true`                          | Auth remained disabled on deployment                                                                                                                                                                    | Removed conditional; always set `AUTH_DISABLED=false`                                                                                                                                        |
| GCP URLMap `Error 412: Invalid fingerprint`                         | Pulumi state out of sync with GCP resource                                                                                                                                                              | Added `pulumi refresh --yes --skip-preview` before `pulumi up` in `deploy-gcp.yml`                                                                                                           |
| GCP Cloud Build `missing main.py`                                   | Cloud Build rejects source even when `--entry-point` is specified                                                                                                                                       | Copy `services/api/function.py` as `main.py` inside the deployment ZIP                                                                                                                       |
| Azure `ModuleNotFoundError: pulumi_azuread`                         | `pulumi-azuread` accidentally deleted from `requirements.txt`                                                                                                                                           | Restore `pulumi-azuread>=6.0.0,<7.0.0` in `infrastructure/pulumi/azure/requirements.txt`                                                                                                     |
| Azure `ModuleNotFoundError: monitoring`                             | `monitoring.py` existed in `main` but not in `develop`                                                                                                                                                  | Add `infrastructure/pulumi/{aws,azure,gcp}/monitoring.py` to `develop`                                                                                                                       |
| Azure FC1: wrong `az functionapp create`                            | `--consumption-plan-location` creates Y1 Dynamic → stale TCP 502 AFD                                                                                                                                    | Use `--flexconsumption-location` to create FC1 FlexConsumption                                                                                                                               |
| GCP `Error 409: uploads-bucket exists`                              | Pulumi tried to create a bucket that already existed in GCP                                                                                                                                             | Add `pulumi import` step for the pre-existing bucket before `pulumi up`                                                                                                                      |
| GCP `ManagedSslCertificate Error 400: in use`                       | SSL cert name hash changed between branches; GCP refused deletion                                                                                                                                       | Add `ignore_changes=["name", "managed"]` to cert resource + `pulumi import` step                                                                                                             |
| Firebase Auth: new domain not authorized                            | `signInWithPopup` fails — domain not in Firebase authorized domains                                                                                                                                     | `deploy-gcp.yml` runs `Update Firebase Authorized Domains` step after Pulumi outputs are read                                                                                                |
| Azure dead CI steps (SSR Lambda)                                    | Old `frontend_web` Lambda/S3 steps ran after React SPA migration                                                                                                                                        | Removed 168 dead lines from `deploy-aws.yml`, `deploy-azure.yml`, `deploy-gcp.yml` (commit `1ae65f5`)                                                                                        |
| Lambda Layer name always `staging`                                  | `github.event.inputs.environment \|\| 'staging'` → push event has no `inputs` → production deploys created layer named `...-staging-dependencies`                                                       | Changed to `steps.set_stack.outputs.stack_name`                                                                                                                                              |
| Env vars wiped / wrong env on each deploy                           | `Pulumi.*.yaml` is gitignored → `grep` always fails → fallback to repo-level Secrets → Secrets are env-agnostic → staging and production share the same domain/client_id                                | Introduced `.github/config/<cloud>.<stack>.env` as committed single source of truth; removed all `case/esac` fallbacks                                                                       |
| Azure AD Client ID empty after CI deploy                            | `pulumi stack output azure_ad_client_id` returned blank → `VITE_AZURE_CLIENT_ID=''` → auth provider became `'none'` → "認証設定が不完全" error on login page                                            | `AZURE_CLIENT_ID` now sourced from `cloud_config` step (config file), never from Pulumi output                                                                                               |
| AWS/Azure/GCP wrong custom domain                                   | `secrets.AZURE_CUSTOM_DOMAIN` (repo-level) contained staging domain → production frontend built with `staging.azure.ashnova.jp` redirect URI                                                            | All custom domain references replaced with `steps.cloud_config.outputs.custom_domain`                                                                                                        |
| AWS `ResourceConflictException` race                                | `update-function-code` issued while Pulumi's config update in progress                                                                                                                                  | Add `aws lambda wait function-updated` before AND after code/config updates                                                                                                                  |
| Azure FC1: `InaccessibleStorageException` on zip deploy             | `config-zip` fails instantly with `BlobUploadFailedException: Name or service not known (xxxxx.blob.core.windows.net:443)` — Kudu `StorageAccessibleCheck` validation fails → status=3 on all attempts  | ARM GET `functionAppConfig.deployment.storage.value` → `az storage account create` to recreate missing account → update `AzureWebJobsStorage__accountName` app setting in `deploy-azure.yml` |
| Azure FC1: `"on-going"` message treated as CI error                 | `config-zip` returns `ERROR: Deployment is still on-going. Navigate to your scm site...` — old `grep ERROR:` pattern matched this FC1 async-accepted response → pipeline exited with code 1 immediately | Detect `on-going` substring **before** generic `ERROR:` check → set `DEPLOY_SUCCESS=true` + `sleep 120` to await completion                                                                  |
| Azure FC1: stale `WEBSITE_RUN_FROM_PACKAGE` causes 404 after deploy | Deploy completes without error but all function routes return 404; old expired SAS URL in setting overrides newly deployed package                                                                      | `az functionapp config appsettings delete --setting-names WEBSITE_RUN_FROM_PACKAGE` before every `config-zip` deploy in `deploy-azure.yml`                                                   |
| Python heredoc in GitHub Actions YAML block scalar                  | `python3 - <<'EOF' ... EOF` inside a `run: \|` block causes `yaml.scanner.ScannerError: while scanning a simple key` — YAML parser chokes on `EOF` at column 0                                          | Always use `jq` for JSON manipulation in shell steps; never use Python heredocs (`<<'EOF'`) inside GitHub Actions `run:` blocks                                                              |
| Azure FC1: `POST /uploads/presigned-urls` → 500                     | `AZURE_STORAGE_ACCOUNT_NAME` / `AZURE_STORAGE_ACCOUNT_KEY` / `AZURE_STORAGE_CONTAINER` missing on production Function App → `generate_blob_sas(account_name=None, account_key=None)` raises exception   | Retrieve key from `frontend_storage_name` Pulumi output; add 3 settings to `az functionapp config appsettings set` in `deploy-azure.yml` (commit `856d6dc`)                                  |

---

## Version Management

> Each artifact is tracked with a version in **`A.B.C.D`** (4-digit) format.
> Version definition file: [`versions.json`](../versions.json)
> Changed from `X.Y.Z` to `A.B.C.D` (2026-02-24, commit `c2f6870`)

### Current Versions (2026-02-24)

| Component           | Version       | Status |
| ------------------- | ------------- | ------ |
| `aws-static-site`   | `1.0.84.204`  | stable |
| `azure-static-site` | `1.0.84.204`  | stable |
| `gcp-static-site`   | `1.0.84.204`  | stable |
| `simple-sns`        | `1.0.84.204`  | stable |

初期値の根拠: C=84 (`git reflog show origin/develop | grep 'update by push'` 実測値) / D=203 (`git log develop --oneline` 実測値、次コミットで 204 に昇格)

### Version Increment Rules

| 桁 | 記号 | 意味       | インクリメント条件                 | 担当                                          |
| -- | ---- | ---------- | ---------------------------------- | --------------------------------------------- |
| 1  | A    | メジャー   | 手動指示のみ                       | `./scripts/bump-version.sh major all`         |
| 2  | B    | マイナー   | 手動指示のみ                       | `./scripts/bump-version.sh minor all`         |
| 3  | C    | プッシュ数 | `git push` のたびに +1 (リセットなし) | GitHub Actions `version-bump.yml` が自動実行 |
| 4  | D    | コミット数 | `git commit` のたびに +1 (リセットなし) | `.githooks/pre-commit` が自動実行           |

> **重要**: どの桁をインクリメントしても他の桁はリセットしない。
> パスフィルタ: `static-site/aws/**` → A のみ、`services/frontend_react/**` → SNS のみ、それ以外 → 全コンポーネント

### Implementation Files

| File                                 | Role                                                                 |
| ------------------------------------ | -------------------------------------------------------------------- |
| `versions.json`                      | 各コンポーネントの現在バージョンを保持                               |
| `scripts/bump-version.sh`            | バージョン操作スクリプト (`commit` / `push` / `minor` / `major` / `set`) |
| `.githooks/pre-commit`               | コミット前に D (コミット数) を自動インクリメント (パスフィルタあり)  |
| `.github/workflows/version-bump.yml` | push 時に C (プッシュ数) を自動インクリメント                         |

### Setup (first time only)

```bash
make hooks-install
# → runs: git config core.hooksPath .githooks
# → auto-increments D on each commit
```

### Common Commands

```bash
# 現在のバージョンを表示
./scripts/bump-version.sh show

# D (+1) — pre-commit hook が自動実行 (手動実行も可)
./scripts/bump-version.sh commit all

# C (+1) — GitHub Actions が自動実行 (手動実行も可)
./scripts/bump-version.sh push all

# B (+1) — 手動指示で実行
./scripts/bump-version.sh minor all

# A (+1) — 手動指示で実行
./scripts/bump-version.sh major all
./scripts/bump-version.sh major simple-sns   # コンポーネント個別指定

# バージョンを直接設定 (移行・修正時)
./scripts/bump-version.sh set all 1.0.84.204
```

### Skipping Version Bumps

| 対象                         | スキップ方法                                                   |
| ---------------------------- | -------------------------------------------------------------- |
| pre-commit hook (D +=1)      | 環境変数: `SKIP_VERSION_BUMP=1 git commit -m "..."`            |
| GitHub Actions (C +=1)       | コミットメッセージに `[skip-version-bump]` を含める            |

```bash
# pre-commit フックをスキップしてコミット
SKIP_VERSION_BUMP=1 git commit -m "docs: update readme"

# GitHub Actions バンプをスキップ (bot コミットのループ防止に使用)
git commit -m "chore: some change [skip-version-bump]"
```

### Procedure When Azure AFD Issue Is Resolved

Once the intermittent Azure Front Door 502 is fixed:

```bash
make version-azure-afd-resolved
git add versions.json
git commit -m "chore: upgrade azure-static-site to 1.0.0 (AFD resolved) [skip-version-bump]"
git push
```

---

## Next Section

→ [06 — Environment Status](AI_AGENT_06_STATUS.md)
