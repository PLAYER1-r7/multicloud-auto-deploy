# 05 — CI/CDパイプライン

> Part II — Architecture & Design | Parent: [AI_AGENT_GUIDE.md](AI_AGENT_GUIDE.md)

---

## ワークフロー一覧

> ⚠️ リポジトリルートの `.github/workflows/` を常に編集してください。
> `multicloud-auto-deploy/.github/workflows/` は CI から無視されます。

| ファイル                        | トリガー条件             | ターゲット                       | 環境                 |
| ------------------------------- | ------------------------ | -------------------------------- | -------------------- |
| `deploy-aws.yml`                | push: develop/main, 手動 | Lambda + API                     | staging / production |
| `deploy-azure.yml`              | push: develop/main, 手動 | Functions + API                  | staging / production |
| `deploy-gcp.yml`                | push: develop/main, 手動 | Cloud Run (API)                  | staging / production |
| `deploy-frontend-aws.yml`       | push: develop/main, 手動 | S3 `sns/`                        | staging / production |
| `deploy-frontend-azure.yml`     | push: develop/main, 手動 | Blob `$web/sns/`                 | staging / production |
| `deploy-frontend-gcp.yml`       | push: develop/main, 手動 | GCS `sns/`                       | staging / production |
| `deploy-frontend-web-aws.yml`   | push: develop/main, 手動 | Lambda (frontend-web)            | staging / production |
| `deploy-frontend-web-azure.yml` | push: develop/main, 手動 | Functions (frontend-web)         | staging / production |
| `deploy-frontend-web-gcp.yml`   | push: develop/main, 手動 | Cloud Run (frontend-web, Docker) | staging / production |
| `deploy-landing-aws.yml`        | push: develop/main, 手動 | S3 `/`                           | staging / production |
| `deploy-landing-azure.yml`      | push: develop/main, 手動 | Blob `$web/`                     | staging / production |
| `deploy-landing-gcp.yml`        | push: develop/main, 手動 | GCS `/`                          | staging / production |

---

## ブランチ → 環境マッピング

```
develop  →  staging
main     →  production  ⚠️ すぐに本番環境に反映されます
```

---

## トリガー条件 (パスフィルタ)

| 変更されたパス               | トリガーされるワークフロー              |
| ---------------------------- | --------------------------------------- |
| `services/api/**`            | deploy-{aws,azure,gcp}.yml              |
| `infrastructure/pulumi/**`   | deploy-{aws,azure,gcp}.yml              |
| `services/frontend_react/**` | deploy-frontend-{aws,azure,gcp}.yml     |
| `services/frontend_web/**`   | deploy-frontend-web-{aws,azure,gcp}.yml |
| `static-site/**`             | deploy-landing-{aws,azure,gcp}.yml      |

---

## クラウド設定ファイル (.github/config/)

> **単一の信頼できるソース** として機能する、環境ごとの安定した値。以前は GitHub Secrets、インラインの `case/esac` ブロック、gitignore された `Pulumi.*.yaml` ファイルに分散していました。

### 保存先

```
.github/config/
  aws.production.env
  aws.staging.env
  azure.production.env
  azure.staging.env
  gcp.production.env
  gcp.staging.env
```

### 保存内容

| クラウド | キー                               | 例                                   |
| -------- | ---------------------------------- | ------------------------------------ |
| すべて   | `CLOUD_CUSTOM_DOMAIN`              | `www.gcp.ashnova.jp`                 |
| Azure    | `CLOUD_AZURE_CLIENT_ID`            | `0b926ff6-...` (AD app registration) |
| Azure    | `CLOUD_AZURE_TENANT_ID`            | `a3182bec-...`                       |
| AWS      | `CLOUD_ACM_CERT_ARN`               | `arn:aws:acm:us-east-1:...`          |
| AWS      | `CLOUD_CLOUDFRONT_DOMAIN`          | `d1qob7569mn5nw.cloudfront.net`      |
| AWS      | `CLOUD_CLOUDFRONT_DISTRIBUTION_ID` | `E214XONKTXJEJD`                     |

### ワークフローでの使用方法

すべてのメインデプロイワークフロー (`deploy-aws.yml`, `deploy-azure.yml`, `deploy-gcp.yml`) は、**Pulumi スタック名の決定**の直後に**クラウド設定を読み込む**ステップを含みます。

```bash
CONFIG_FILE=".github/config/aws.${STACK_NAME}.env"
source "$CONFIG_FILE"
echo "custom_domain=$CLOUD_CUSTOM_DOMAIN" >> $GITHUB_OUTPUT
# ... その他の出力
```

その後のすべてのステップは、フォールバックロジックの代わりに `${{ steps.cloud_config.outputs.custom_domain }}` などを参照します。

### 更新時期

| イベント              | アクション                                              |
| --------------------- | ------------------------------------------------------- |
| カスタムドメイン変更  | 関連する `.env` ファイルの `CLOUD_CUSTOM_DOMAIN` を更新 |
| ACM 証明書更新 (AWS)  | `CLOUD_ACM_CERT_ARN` を更新                             |
| Azure AD アプリ再登録 | `CLOUD_AZURE_CLIENT_ID` を更新                          |
| 新しいスタック追加    | 新しい `<cloud>.<stack>.env` ファイルを追加             |

### GitHub Secrets に保存しない理由

リポジトリレベルの GitHub Secrets は**環境に依存しません**。リポジトリレベルで `AZURE_CUSTOM_DOMAIN=www.azure.ashnova.jp` を設定すると、ステージングデプロイも本番環境のドメインを受け取ります。環境レベルの Secrets はこの問題を解決しますが、GitHub UI で設定する必要があり、コード レビューには表示されません。`.github/config/` のコンフィグファイルは git でトラッキングされ、diff で表示され、GitHub UI のメンテナンスは不要です。

---

## 必要な GitHub Secrets

### AWS

| Secret                  | 用途                      |
| ----------------------- | ------------------------- |
| `AWS_ACCESS_KEY_ID`     | IAM アクセスキー          |
| `AWS_SECRET_ACCESS_KEY` | IAM シークレットキー      |
| `PULUMI_ACCESS_TOKEN`   | Pulumi Cloud 認証トークン |

> ⚠️ `AWS_CUSTOM_DOMAIN`, `AWS_ACM_CERTIFICATE_ARN`, `AWS_CLOUDFRONT_DOMAIN` は**使用されなくなりました**。
> これらの値は `.github/config/aws.<stack>.env` から読み込まれます。

### Azure

| Secret                  | 用途                                                           |
| ----------------------- | -------------------------------------------------------------- |
| `AZURE_CREDENTIALS`     | Service Principal JSON (`az ad sp create-for-rbac --sdk-auth`) |
| `AZURE_SUBSCRIPTION_ID` | サブスクリプション ID                                          |
| `AZURE_RESOURCE_GROUP`  | リソースグループ名                                             |
| `PULUMI_ACCESS_TOKEN`   | Pulumi Cloud 認証トークン                                      |

> ⚠️ `AZURE_CUSTOM_DOMAIN` は **`deploy-azure.yml` では使用されなくなりました**。
> `CLOUD_CUSTOM_DOMAIN`, `CLOUD_AZURE_CLIENT_ID`, `CLOUD_AZURE_TENANT_ID` は `.github/config/azure.<stack>.env` から読み込まれます。

### GCP

| Secret                 | 用途                                               |
| ---------------------- | -------------------------------------------------- |
| `GCP_CREDENTIALS`      | Service Account JSON                               |
| `GCP_PROJECT_ID`       | プロジェクト ID (`ashnova`)                        |
| `GCP_API_ENDPOINT`     | Cloud Run API URL (frontend-web `API_BASE_URL` 用) |
| `FIREBASE_API_KEY`     | Firebase Web API キー (frontend-web 認証用)        |
| `FIREBASE_AUTH_DOMAIN` | Firebase Auth ドメイン (frontend-web 認証用)       |
| `FIREBASE_APP_ID`      | Firebase App ID (frontend-web 認証用)              |
| `PULUMI_ACCESS_TOKEN`  | Pulumi Cloud 認証トークン                          |

---

## デプロイフロー (AWS バックエンド例)

```yaml
# deploy-aws.yml ステップ (要約)
1. Checkout
2. AWS 認証 (aws-actions/configure-aws-credentials)
3. Python 3.12 セットアップ
4. Pulumi ログイン (PULUMI_ACCESS_TOKEN)
5. Pulumi スタック名決定  →  STACK_NAME = staging | production
6. クラウド設定を読み込む  →  source .github/config/aws.${STACK_NAME}.env
   # 出力: custom_domain, acm_cert_arn, cloudfront_domain
7. pulumi up --stack staging  # インフラストラクチャ作成/更新
8. Pulumi 出力取得  →  バケット名、CloudFront ID、Cognito ID など
9. Lambda Layer ビルド (./scripts/build-lambda-layer.sh)
10. Lambda Layer を公開  (name = multicloud-auto-deploy-${STACK_NAME}-dependencies)
11. アプリコードを ZIP でパッケージ (app/ + index.py)
12. Lambda 関数コードを更新
13. Lambda 環境変数を更新
    - CLOUD_PROVIDER=aws
    - AUTH_DISABLED=false
    - AUTH_PROVIDER=cognito
    - COGNITO_USER_POOL_ID (Pulumi 出力から)
    - COGNITO_CLIENT_ID (Pulumi 出力から)
```

## デプロイフロー (フロントエンド例)

```yaml
# deploy-frontend-aws.yml ステップ (要約)
1. Checkout
2. AWS 認証
3. Node.js セットアップ
4. npm ci
5. Pulumi 出力から S3 バケット名と CloudFront ID を取得
6. VITE_API_URL を設定して npm run build を実行
   # vite.config.ts: base="/sns/" は既に設定されています
7. aws s3 sync dist/ s3://{bucket}/sns/ --delete
8. CloudFront キャッシュ無効化 (/*)
```

---

## 手動デプロイ (緊急時)

```bash
# GitHub CLI 経由でワークフローを手動トリガー
gh workflow run deploy-aws.yml \
  --ref develop \
  -f environment=staging

# または production へ
gh workflow run deploy-aws.yml \
  --ref main \
  -f environment=production

# 実行ステータス確認
gh run list --workflow=deploy-aws.yml --limit 5
gh run watch <run-id>
```

---

## 手動デプロイ (緊急時)

```bash
# GitHub CLI経由でワークフローを手動トリガー
gh workflow run deploy-aws.yml \
  --ref develop \
  -f environment=staging

gh workflow run deploy-frontend-gcp.yml \
  --ref main \
  -f environment=production

# 実行ステータス確認
gh run list --workflow=deploy-aws.yml --limit 5
gh run watch <run-id>
```

---

## CI/CD 現在ステータス (2026-02-24)

| ワークフロー                 | ブランチ | ステータス | コミット  |
| ---------------------------- | -------- | ---------- | --------- |
| Deploy Frontend Web to GCP   | develop  | ✅         | `0ed0805` |
| Deploy to GCP (Pulumi + API) | develop  | ✅         | `0ed0805` |
| Deploy Frontend to GCP       | develop  | ✅         | `591ce0b` |
| Deploy Frontend to AWS       | develop  | ✅         | `591ce0b` |
| Deploy Frontend to Azure     | develop  | ✅         | `591ce0b` |
| Deploy Landing to GCP        | develop  | ✅         | `591ce0b` |
| Deploy Landing to AWS        | develop  | ✅         | `591ce0b` |
| Deploy Landing to Azure      | develop  | ✅         | `591ce0b` |

---

## 修正済み CI バグ (再発を監視)

| バグ                                                          | 症状                                                                                                                                                                         | 修正                                                                                                                                                                              |
| ------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| ワークフロー重複                                              | サブディレクトリ編集のみで CI に反映されない                                                                                                                                 | ルート `.github/workflows/` を編集                                                                                                                                                |
| `deploy-landing-gcp.yml` 認証方式                             | `workload_identity_provider` (secret 未設定)                                                                                                                                 | `credentials_json: ${{ secrets.GCP_CREDENTIALS }}` に変更                                                                                                                         |
| `deploy-landing-aws.yml` 認証方式                             | `role-to-assume` (secret 未設定)                                                                                                                                             | `aws-access-key-id` + `aws-secret-access-key` に変更                                                                                                                              |
| フロントエンドがランディングページを上書き                    | `dist/` がバケットルートに同期された                                                                                                                                         | `dist/` を `sns/` プレフィックスの下に同期に変更                                                                                                                                  |
| AWS/Azure staging で `AUTH_DISABLED=true`                     | デプロイ後も認証が無効のまま                                                                                                                                                 | 条件付きを削除；常に `AUTH_DISABLED=false` に設定                                                                                                                                 |
| GCP URLMap `Error 412: Invalid fingerprint`                   | Pulumi 状態と GCP リソースが非同期                                                                                                                                           | `deploy-gcp.yml` で `pulumi up` の前に `pulumi refresh --yes --skip-preview` を追加                                                                                               |
| GCP Cloud Build `missing main.py`                             | Cloud Build が `--entry-point` を指定してもソースを拒否                                                                                                                      | デプロイ ZIP 内に `services/api/function.py` を `main.py` としてコピー                                                                                                            |
| Azure `ModuleNotFoundError: pulumi_azuread`                   | `pulumi-azuread` が誤って `requirements.txt` から削除された                                                                                                                  | `infrastructure/pulumi/azure/requirements.txt` に `pulumi-azuread>=6.0.0,<7.0.0` を復元                                                                                           |
| Azure `ModuleNotFoundError: monitoring`                       | `monitoring.py` が `main` には存在するが `develop` にない                                                                                                                    | `infrastructure/pulumi/{aws,azure,gcp}/monitoring.py` を `develop` に追加                                                                                                         |
| Azure FC1: 誤った `az functionapp create`                     | `--consumption-plan-location` で Y1 Dynamic 作成 → AFD で stale TCP 502                                                                                                      | FC1 FlexConsumption 作成のため `--flexconsumption-location` を使用                                                                                                                |
| GCP `Error 409: uploads-bucket exists`                        | Pulumi が GCP 内に既存のバケットを作成しようとした                                                                                                                           | `pulumi up` 前に既存バケットの `pulumi import` ステップを追加                                                                                                                     |
| GCP `ManagedSslCertificate Error 400: in use`                 | ブランチ間で SSL 証明書名ハッシュが変更；GCP が削除を拒否                                                                                                                    | 証明書リソースに `ignore_changes=["name", "managed"]` を追加 + `pulumi import` ステップ                                                                                           |
| Firebase Auth: 新ドメインが未認可                             | `signInWithPopup` 失敗 — ドメインが Firebase 認可ドメインにない                                                                                                              | `deploy-gcp.yml` で Pulumi 出力読み取り後に「Firebase 認可ドメイン更新」ステップを実行                                                                                            |
| Azure dead CI ステップ (SSR Lambda)                           | React SPA 移行後も古い `frontend_web` Lambda/S3 ステップが実行                                                                                                               | `deploy-aws.yml`, `deploy-azure.yml`, `deploy-gcp.yml` から 168 行の不要コードを削除 (コミット `1ae65f5`)                                                                         |
| Lambda Layer 名が常に `staging`                               | `github.event.inputs.environment \|\| 'staging'` → push イベントには `inputs` がない → production デプロイが `...-staging-dependencies` という名前のレイヤーを作成           | `steps.set_stack.outputs.stack_name` に変更                                                                                                                                       |
| 環境変数が消去される / デプロイごとに誤った環境               | `Pulumi.*.yaml` が gitignore 対象 → `grep` が常に失敗 → リポジトリレベル Secrets へフォールバック → Secrets は環境非依存 → staging と production が同じドメイン/client_id    | コミット版の単一真実源として `.github/config/<cloud>.<stack>.env` を導入；すべての `case/esac` フォールバックを削除                                                               |
| Azure AD Client ID が CI デプロイ後に空                       | `pulumi stack output azure_ad_client_id` が空を返す → `VITE_AZURE_CLIENT_ID=''` → 認証プロバイダーが `'none'` → ログインページで「認証設定が不完全」エラー                   | `AZURE_CLIENT_ID` を `cloud_config` ステップ（設定ファイル）から取得、Pulumi 出力からは取得しない                                                                                 |
| AWS/Azure/GCP の誤ったカスタムドメイン                        | `secrets.AZURE_CUSTOM_DOMAIN` (リポジトリレベル) に staging ドメインが含まれる → production フロントエンドが `staging.azure.ashnova.jp` redirect URI でビルドされる          | すべてのカスタムドメイン参照を `steps.cloud_config.outputs.custom_domain` に置換                                                                                                  |
| AWS `ResourceConflictException` 競合                          | Pulumi の設定更新中に `update-function-code` が発行される                                                                                                                    | コード/設定更新の前後に `aws lambda wait function-updated` を追加                                                                                                                 |
| Azure FC1: zip deploy で `InaccessibleStorageException`       | `config-zip` が `BlobUploadFailedException: Name or service not known` で即座に失敗 — Kudu `StorageAccessibleCheck` 検証失敗 → すべての試行でステータス=3                    | ARM GET `functionAppConfig.deployment.storage.value` → `az storage account create` で欠落アカウントを再作成 → `deploy-azure.yml` で `AzureWebJobsStorage__accountName` 設定を更新 |
| Azure FC1: `"on-going"` メッセージが CI エラー扱い            | `config-zip` が `ERROR: Deployment is still on-going...` を返す — 古い `grep ERROR:` パターンがこの FC1 非同期受付応答にマッチ → パイプラインが即座にコード 1 で終了         | 一般的な `ERROR:` チェックの**前**に `on-going` サブストリングを検出 → `DEPLOY_SUCCESS=true` 設定 + `sleep 120` で完了を待機                                                      |
| Azure FC1: デプロイ後の古い `WEBSITE_RUN_FROM_PACKAGE` で 404 | デプロイがエラーなく完了するが全関数ルートが 404 を返す；設定内の古い期限切れ SAS URL が新デプロイパッケージをオーバーライド                                                 | `deploy-azure.yml` で `config-zip` デプロイの前に毎回 `az functionapp config appsettings delete --setting-names WEBSITE_RUN_FROM_PACKAGE` を実行                                  |
| GitHub Actions YAML ブロックスカラー内の Python heredoc       | `run: \|` ブロック内の `python3 - <<'EOF' ... EOF` が `yaml.scanner.ScannerError: while scanning a simple key` を引き起こす — YAML パーサーが 0 列目の `EOF` でエラー        | シェルステップでの JSON 操作には常に `jq` を使用；GitHub Actions `run:` ブロック内で Python heredoc (`<<'EOF'`) は使用しない                                                      |
| Azure FC1: `POST /uploads/presigned-urls` → 500               | `AZURE_STORAGE_ACCOUNT_NAME` / `AZURE_STORAGE_ACCOUNT_KEY` / `AZURE_STORAGE_CONTAINER` が production Function App で欠落 → `generate_blob_sas(account_name=None)` が例外発生 | `frontend_storage_name` Pulumi 出力からキーを取得；`deploy-azure.yml` の `az functionapp config appsettings set` に 3 設定を追加 (コミット `856d6dc`)                             |

---

## バージョン管理

> 各アーティファクトは **`A.B.C.D`** (4桁) 形式でバージョン追跡されます。
> バージョン定義ファイル: [`versions.json`](../versions.json)
> `X.Y.Z` から `A.B.C.D` に変更 (2026-02-24, commit `c2f6870`)

### 現在のバージョン (2026-02-24)

| コンポーネント      | バージョン   | ステータス |
| ------------------- | ------------ | ---------- |
| `aws-static-site`   | `1.0.84.204` | stable     |
| `azure-static-site` | `1.0.84.204` | stable     |
| `gcp-static-site`   | `1.0.84.204` | stable     |
| `simple-sns`        | `1.0.84.204` | stable     |

### バージョンインクリメント規則

| 桁  | 記号 | 意味       | インクリメント条件                       | 担当                                         |
| --- | ---- | ---------- | ---------------------------------------- | -------------------------------------------- |
| 1   | A    | メジャー   | 手動指示のみ                             | `./scripts/bump-version.sh major all`        |
| 2   | B    | マイナー   | 手動指示のみ                             | `./scripts/bump-version.sh minor all`        |
| 3   | C    | プッシュ数 | `git push` のたびに +1（リセットなし）   | GitHub Actions `version-bump.yml` が自動実行 |
| 4   | D    | コミット数 | `git commit` のたびに +1（リセットなし） | `.githooks/pre-commit` が自動実行            |

> **重要**: どの桁をインクリメントしても他の桁はリセットしません。
> パスフィルタ: `static-site/aws/**` → A のみ、`services/frontend_react/**` → SNS のみ、それ以外 → 全コンポーネント

### 実装ファイル

| ファイル                             | 役割                                             |
| ------------------------------------ | ------------------------------------------------ |
| `versions.json`                      | 各コンポーネントの現在バージョンを保持           |
| `scripts/bump-version.sh`            | バージョン操作スクリプト                         |
| `.githooks/pre-commit`               | コミット前に D（コミット数）を自動インクリメント |
| `.github/workflows/version-bump.yml` | push 時に C（プッシュ数）を自動インクリメント    |

### セットアップ (初回のみ)

```bash
make hooks-install
# → git config core.hooksPath .githooks を実行
# → 各コミット時に D を自動インクリメント
```

### よく使うコマンド

```bash
# 現在のバージョンを表示
./scripts/bump-version.sh show

# D (+1) — pre-commit hook が自動実行（手動実行も可）
./scripts/bump-version.sh commit all

# C (+1) — GitHub Actions が自動実行（手動実行も可）
./scripts/bump-version.sh push all

# B (+1) — 手動指示で実行
./scripts/bump-version.sh minor all

# A (+1) — 手動指示で実行
./scripts/bump-version.sh major all

# バージョン直接設定（移行・修正時）
./scripts/bump-version.sh set all 1.0.84.204
```

### バージョンバンプをスキップ

| 対象                    | スキップ方法                                        |
| ----------------------- | --------------------------------------------------- |
| pre-commit hook (D +=1) | 環境変数: `SKIP_VERSION_BUMP=1 git commit -m "..."` |
| GitHub Actions (C +=1)  | コミットメッセージに `[skip-version-bump]` を含める |

```bash
# pre-commit フックをスキップしてコミット
SKIP_VERSION_BUMP=1 git commit -m "docs: update readme"

# GitHub Actions バンプをスキップ
git commit -m "chore: some change [skip-version-bump]"
```

---

## 次のセクション

→ [06 — 環境ステータス](AI_AGENT_06_STATUS_JA.md)
