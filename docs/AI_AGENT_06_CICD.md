# 06 — CI/CD Pipelines

> Parent: [AI_AGENT_GUIDE.md](AI_AGENT_GUIDE.md)

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

| Changed path                 | Workflow triggered                      |
| ---------------------------- | --------------------------------------- |
| `services/api/**`            | deploy-{aws,azure,gcp}.yml              |
| `infrastructure/pulumi/**`   | deploy-{aws,azure,gcp}.yml              |
| `services/frontend_react/**` | deploy-frontend-{aws,azure,gcp}.yml     |
| `services/frontend_web/**`   | deploy-frontend-web-{aws,azure,gcp}.yml |
| `static-site/**`             | deploy-landing-{aws,azure,gcp}.yml      |

---

## Required GitHub Secrets

### AWS

| Secret                  | Purpose                 |
| ----------------------- | ----------------------- |
| `AWS_ACCESS_KEY_ID`     | IAM access key          |
| `AWS_SECRET_ACCESS_KEY` | IAM secret key          |
| `PULUMI_ACCESS_TOKEN`   | Pulumi Cloud auth token |

### Azure

| Secret                  | Purpose                                                        |
| ----------------------- | -------------------------------------------------------------- |
| `AZURE_CREDENTIALS`     | Service Principal JSON (`az ad sp create-for-rbac --sdk-auth`) |
| `AZURE_SUBSCRIPTION_ID` | Subscription ID                                                |
| `AZURE_RESOURCE_GROUP`  | Resource group name                                            |
| `PULUMI_ACCESS_TOKEN`   | Pulumi Cloud auth token                                        |

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
3. Set up Python 3.12
4. Pulumi login (PULUMI_ACCESS_TOKEN)
5. pulumi up --stack staging  # create/update infrastructure
6. Build Lambda Layer (./scripts/build-lambda-layer.sh)
7. Publish Lambda Layer
8. Package app code as ZIP (app/ + index.py)
9. Update Lambda function code
10. Update Lambda environment variables
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

## CI/CD Current Status (2026-02-21)

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

| Bug                                        | Symptom                                         | Fix                                                           |
| ------------------------------------------ | ----------------------------------------------- | ------------------------------------------------------------- |
| Workflow file duplication                  | Editing subdirectory only → not reflected in CI | Edit root `.github/workflows/`                                |
| `deploy-landing-gcp.yml` auth method       | `workload_identity_provider` (secret not set)   | Changed to `credentials_json: ${{ secrets.GCP_CREDENTIALS }}` |
| `deploy-landing-aws.yml` auth method       | `role-to-assume` (secret not set)               | Changed to `aws-access-key-id` + `aws-secret-access-key`      |
| Frontend overwrote landing page            | `dist/` synced to bucket root                   | Changed to sync `dist/` under `sns/` prefix                   |
| AWS/Azure staging had `AUTH_DISABLED=true` | Auth remained disabled on deployment            | Removed conditional; always set `AUTH_DISABLED=false`         |

---

## バージョン管理

> 成果物ごとに `X.Y.Z` 形式でバージョンを追跡する。  
> バージョン定義ファイル: [`versions.json`](../versions.json)

### コンポーネント一覧と初期バージョン

| コンポーネント        | 初期バージョン | 理由                                     |
| --------------------- | -------------- | ---------------------------------------- |
| `aws-static-site`     | `1.0.0`        | 安定稼働中                               |
| `azure-static-site`   | `0.9.0`        | AFD 経由 `/sns/*` 間欠的 502 未解消      |
| `gcp-static-site`     | `1.0.0`        | 安定稼働中 (HTTPS未設定は残課題)         |
| `simple-sns`          | `1.0.0`        | React SNS アプリ、全クラウド共通デプロイ |

### バージョン規則

| 桁 | 名称      | インクリメント条件               | 方法                          |
| -- | --------- | -------------------------------- | ----------------------------- |
| X  | メジャー  | 手動指示のみ                     | `make version-major`          |
| Y  | マイナー  | `develop` / `main` へのプッシュ  | GitHub Actions `version-bump.yml` が自動実行 |
| Z  | パッチ    | コミットのたびに                 | `pre-commit` git hook が自動実行 |

### 実装ファイル

| ファイル                               | 役割                                                  |
| -------------------------------------- | ----------------------------------------------------- |
| `versions.json`                        | 全コンポーネントの現在バージョンを格納                |
| `scripts/bump-version.sh`             | バージョン操作スクリプト (patch / minor / major 対応) |
| `.githooks/pre-commit`                | コミット前にパッチ(Z)を自動インクリメント             |
| `.github/workflows/version-bump.yml`  | push 時にマイナー(Y)を自動インクリメント              |

### セットアップ (初回のみ)

```bash
make hooks-install
# → git config core.hooksPath .githooks を設定
# → コミット時に自動で Z をインクリメント
```

### よく使うコマンド

```bash
# 現在のバージョン一覧
make version

# メジャーバージョンを手動で上げる (X+1)
make version-major COMPONENT=all          # 全コンポーネント
make version-major COMPONENT=simple-sns   # 指定コンポーネントのみ

# Azure AFD 解消後に 0.9.x → 1.0.0 へ昇格
make version-azure-afd-resolved

# スクリプトを直接呼ぶ場合
./scripts/bump-version.sh show
./scripts/bump-version.sh major simple-sns
./scripts/bump-version.sh azure-afd-resolved
```

### バージョンバンプのスキップ

コミットメッセージに `[skip-version-bump]` を含めると pre-commit hook と GitHub Actions の両方がスキップされる。

```bash
git commit -m "docs: update readme [skip-version-bump]"
```

### Azure AFD 解消手順

Azure Front Door の間欠的 502 が解消されたら:

```bash
make version-azure-afd-resolved
git add versions.json
git commit -m "chore: upgrade azure-static-site to 1.0.0 (AFD resolved) [skip-version-bump]"
git push
```

---

## Next Section

→ [07 — Environment Status](AI_AGENT_07_STATUS.md)
