# ソースコード解説書

> 本ドキュメントは `services/api/`・`services/frontend_react/` のアプリコードを解説した [IMPLEMENTATION_GUIDE.md](IMPLEMENTATION_GUIDE.md) の**姉妹ドキュメント**である。
> ここでは **インフラ (Pulumi)**・**CI/CD (GitHub Actions)**・**スクリプト** のソースを扱う。

---

## 目次

1. [インフラ全体の考え方](#1-インフラ全体の考え方)
2. [Pulumi AWS (`infrastructure/pulumi/aws/__main__.py`)](#2-pulumi-aws)
3. [Pulumi Azure (`infrastructure/pulumi/azure/__main__.py`)](#3-pulumi-azure)
4. [Pulumi GCP (`infrastructure/pulumi/gcp/__main__.py`)](#4-pulumi-gcp)
5. [CI/CD ワークフロー (GitHub Actions)](#5-cicd-ワークフロー-github-actions)
6. [フロントエンド SPA デプロイワークフロー](#6-フロントエンド-spa-デプロイワークフロー)
7. [スクリプト群 (`scripts/`)](#7-スクリプト群-scripts)

---

## 1. インフラ全体の考え方

### IaC ツール: Pulumi Python SDK

Terraform ではなく **Pulumi** を使う理由は、Python コードで条件分岐・ループ・関数を自由に使えるためである。設定値は `Pulumi.<stack>.yaml` に記述し、デプロイ状態は **Pulumi Cloud**（リモートステート）で管理する。

### スタック（環境）分離

| スタック名   | ブランチ  | 用途                     |
| ------------ | --------- | ------------------------ |
| `staging`    | `develop` | 自動デプロイ・動作確認用 |
| `production` | `main`    | 本番環境（即時反映）     |

各スタックは独立したクラウドリソースを持つ（S3 バケット名・Lambda 関数名などに `{stack}` サフィックスが付く）。

### リソース命名規則

```python
project_name = "multicloud-auto-deploy"
stack = pulumi.get_stack()   # "staging" または "production"

# 例: "multicloud-auto-deploy-staging-api"
f"{project_name}-{stack}-api"
```

全リソースに `common_tags`（Project / ManagedBy / Environment）を付与してコスト管理・検索を容易にする。

---

## 2. Pulumi AWS

ファイル: [infrastructure/pulumi/aws/**main**.py](../infrastructure/pulumi/aws/__main__.py)（約965行）

### 2-1. リソース構成の全体像

```
IAM Role (Lambda 用)
  └─ AWSLambdaBasicExecutionRole ポリシーアタッチ
  └─ DynamoDB + S3 アクセス用インラインポリシー

Cognito User Pool
  └─ User Pool Client (PKCE コードフロー)
  └─ User Pool Domain (認証ホスト UI)

DynamoDB Table (Single Table Design)
  ├─ PK="PK" / SK="SK"
  ├─ GSI: PostIdIndex (hash=postId)
  └─ GSI: UserPostsIndex (hash=userId, range=createdAt)

S3 Bucket: images（画像アップロード先）
  └─ CORS 設定（ブラウザから直接 PUT できるよう）
  └─ PublicAccessBlock（public 禁止）

Lambda Layer（FastAPI / Mangum / Pydantic 等）
  └─ services/api/lambda-layer.zip から生成

Lambda Function（FastAPI + Mangum）
  └─ ENV: POSTS_TABLE_NAME, IMAGES_BUCKET_NAME, COGNITO_* 等

API Gateway v2 (HTTP API)
  └─ $default ルート → Lambda 統合

S3 Bucket: frontend（React SPA 配信）
  └─ OAC (Origin Access Control) で CloudFront のみ許可

CloudFront Distribution
  ├─ /sns/* → S3 frontend / CloudFront Function で /sns → /sns/index.html リライト
  └─ /*     → S3 frontend (landing pages)
```

### 2-2. Cognito User Pool

```python
user_pool_client = aws.cognito.UserPoolClient(
    allowed_oauth_flows=["code"],         # PKCE コードフロー
    allowed_oauth_scopes=["openid", "email", "profile"],
    callback_urls=(
        ([f"https://{cf_domain}/sns/auth/callback"] if cf_domain else [])
        + ([f"https://{custom_domain}/sns/auth/callback"] if custom_domain else [])
    ),
    access_token_validity=1,   # 1時間
    id_token_validity=1,       # 1時間
    refresh_token_validity=30, # 30日
)
```

`cf_domain`（CloudFront ドメイン）と `custom_domain`（カスタムドメイン）の両方を登録することで、どちらのドメインからでも認証フローが成立する。

### 2-3. Lambda Layer の ZIP パス解決

CI とローカルでは ZIP のパスが異なるため、`GITHUB_WORKSPACE` 環境変数で分岐している。

```python
workspace_root = os.environ.get("GITHUB_WORKSPACE")
if workspace_root:
    layer_zip_path = pathlib.Path(workspace_root) / "services/api/lambda-layer.zip"
else:
    # __file__ から3階層上がリポジトリルート
    layer_zip_path = pathlib.Path(__file__).parent.parent.parent / "services/api/lambda-layer.zip"
```

ZIP が存在しない場合はウォーニングを出してスキップする（初回デプロイ時など）。

### 2-4. CloudFront SPA リライト（CloudFront Function）

React SPA は HTML5 History API でルーティングするため、CDN 側で `/sns` → `/sns/index.html` のリライトが必要。CloudFront Function を Pulumi のコード内にインラインで定義している。

```python
spa_rewrite_function = aws.cloudfront.Function(
    "spa-sns-rewrite",
    name=f"spa-sns-rewrite-{stack}",
    runtime="cloudfront-js-2.0",
    code="""
function handler(event) {
    var uri = event.request.uri;
    if (uri === '/sns' || uri === '/sns/') {
        event.request.uri = '/sns/index.html';
    } else if (uri.startsWith('/sns/') && !uri.includes('.')) {
        event.request.uri = '/sns/index.html';
    }
    return event.request;
}
""",
)
```

---

## 3. Pulumi Azure

ファイル: [infrastructure/pulumi/azure/**main**.py](../infrastructure/pulumi/azure/__main__.py)（約612行）

### 3-1. リソース構成の全体像

```
Resource Group (japaneast)
  ├─ Storage Account: mcadfunc{suffix}  ← Azure Functions 用
  ├─ Storage Account: mcadweb{suffix}   ← フロントエンド静的サイト用
  │    └─ $web コンテナ（静的 Web サイトホスティング）
  ├─ Application Insights（監視）
  ├─ Cosmos DB アカウント
  │    └─ コンテナ: posts / profiles
  ├─ Azure AD アプリ登録（認証）
  │    └─ リダイレクト URI: https://{frontend_domain}/sns/auth/callback
  ├─ Azure Functions（Flex Consumption）
  │    └─ HTTP Trigger: {*route} → FastAPI
  └─ Azure Front Door（CDN）
       ├─ /sns/* → Blob Storage $web/sns/ (React SPA)
       └─ /*     → Blob Storage $web (landing pages)
```

### 3-2. ストレージアカウント名のランダムサフィックス

Azure ストレージアカウント名はグローバル一意が必要なため `pulumi_random` で6文字サフィックスを生成する。同じインスタンスを2つのアカウントで共有することで、識別が容易になる。

```python
storage_suffix = random.RandomString("storage-suffix", length=6, special=False, upper=False)

functions_storage_name = storage_suffix.result.apply(lambda s: f"mcadfunc{s}")
frontend_storage_name  = storage_suffix.result.apply(lambda s: f"mcadweb{s}")
```

### 3-3. Azure AD アプリ登録（暗黙的フロー）

AWS Cognito が PKCE コードフローを使うのに対し、Azure AD は**暗黙的フロー**（`id_token` フラグメント）を使う。

```python
app_registration = azuread.Application(
    "app-registration",
    web=azuread.ApplicationWebArgs(
        redirect_uris=[f"https://{frontend_domain}/sns/auth/callback"],
        implicit_grant=azuread.ApplicationWebImplicitGrantArgs(
            id_token_issuance_enabled=True,   # 暗黙的フロー
        ),
    ),
)
```

フロントエンドのコールバックハンドラーは URL フラグメント（`#id_token=...`）を解析してトークンを取得する。

### 3-4. Front Door SPA ルーティング

AFD の `SpaRuleSet` URL リライトルールで `/sns/*` の非アセットパスを `/sns/index.html` にリライトし、React SPA のクライアントルーティングを実現する。

---

## 4. Pulumi GCP

ファイル: [infrastructure/pulumi/gcp/**main**.py](../infrastructure/pulumi/gcp/__main__.py)（約585行）

### 4-1. リソース構成の全体像

```
GCP API 有効化（Cloud Run / Secret Manager / Firebase 等）
Firebase プロジェクト・Web アプリ登録
Cloud Audit Logs（全サービス対象）

GCS バケット: frontend   ← React SPA + landing pages
GCS バケット: uploads    ← 画像アップロード

Secret Manager（環境変数を秘密として管理）

Cloud Run: api           ← FastAPI (uvicorn)
  └─ サービスアカウント（Firestore / GCS / Secret Manager 権限）

Cloud CDN（Classic External LB）
  └─ /* → GCS バケット（Backend Bucket）
```

### 4-2. GCP API の一括有効化と依存関係

```python
services = ["run.googleapis.com", "secretmanager.googleapis.com", "firebase.googleapis.com", ...]
enabled_services = [gcp.projects.Service(f"enable-{s}", ...) for s in services]

# 全後続リソースが API 有効化完了後に作成されることを保証
firebase_project = gcp.firebase.Project(
    "firebase-project",
    opts=pulumi.ResourceOptions(depends_on=enabled_services),
)
```

### 4-3. Cloud Run のコード / インフラ分離

Pulumi は Cloud Run の**サービス設定**（メモリ・環境変数・サービスアカウント）を管理するが、**コンテナイメージのデプロイ**は CI/CD ワークフロー（`gcloud run deploy`）が担う。Pulumi デプロイ時にコンテナイメージを要求するという制約を回避する設計である。

### 4-4. Firebase 認証の手動設定

Firebase の認証プロバイダー設定（Google サインイン）は OAuth 同意画面の設定が必要で Pulumi から自動化できない。コードにコメントで明示している。

```python
# Note: Authentication providers must be configured manually in Firebase Console
# due to OAuth consent screen requirements.
# Visit: https://console.firebase.google.com/project/{project}/authentication/providers
```

---

## 5. CI/CD ワークフロー (GitHub Actions)

### 5-1. ワークフロー一覧

| ファイル                        | 役割                                                        |
| ------------------------------- | ----------------------------------------------------------- |
| `deploy-aws.yml`                | AWS 全リソース（Pulumi + Lambda + フロントエンド含む）      |
| `deploy-azure.yml`              | Azure 全リソース（Pulumi + Functions + フロントエンド含む） |
| `deploy-gcp.yml`                | GCP 全リソース（Pulumi + Cloud Run + フロントエンド含む）   |
| `deploy-frontend-web-aws.yml`   | React SPA を S3/CloudFront にのみ再デプロイ（差分更新）     |
| `deploy-frontend-web-azure.yml` | React SPA を Blob Storage/AFD にのみ再デプロイ              |
| `deploy-frontend-web-gcp.yml`   | React SPA を GCS/CDN にのみ再デプロイ                       |
| `deploy-landing-*.yml`          | ランディングページ（静的 HTML）の各クラウドへの配信         |
| `version-bump.yml`              | `versions.json` のバージョン自動更新                        |

### 5-2. ブランチ→環境マッピング

3つのワークフローすべてで同じルールを採用している。

```yaml
# develop → staging, main → production, 手動（workflow_dispatch）→ 選択した環境
environment: >-
  ${{ github.event_name == 'workflow_dispatch'
        && github.event.inputs.environment
        || (github.ref == 'refs/heads/main' && 'production' || 'staging') }}
```

### 5-3. 同時実行防止（concurrency）

Pulumi は同一スタックへの並行デプロイで `ResourceConflictException` / `409 Conflict` が発生するため、`concurrency` で直列化している。

```yaml
concurrency:
  group: deploy-aws-${{ ... }}
  cancel-in-progress:
    false # AWS/GCP: 実行中のジョブはキャンセルしない
    # Azure staging: true（コスト削減のため古い Run をキャンセル）
```

---

### 5-4. AWS デプロイの主要ステップ（`deploy-aws.yml`）

```
1. AWS 認証（aws-actions/configure-aws-credentials）
2. Pulumi CLI インストール
3. スタック名の決定（develop→staging / main→production）
4. .github/config/aws.{stack}.env から設定を読込（single source of truth）
5. Pulumi スタック選択 / 初期化
6. Pulumi up（インフラ変更適用）
7. Pulumi outputs 取得（Lambda 名・バケット名・Cognito 設定等）
8. Lambda Layer ZIP ビルド（scripts/build-lambda-layer.sh）
9. Lambda 関数コードの ZIP 化・アップロード（aws lambda update-function-code）
10. CloudFront エイリアス + ACM 証明書の確認・修正（safety net）
11. Cognito コールバック URL の確認・修正（safety net）
12. React SPA ビルド（npm run build）
13. S3 同期（aws s3 sync）
14. CloudFront キャッシュ無効化（aws cloudfront create-invalidation）
```

**「Safety net」ステップの目的:**
Pulumi がカスタムドメイン設定を誤って消してしまうことがあるため、デプロイ後に AWS CLI で直接確認・修正するステップを追加している。Pulumi の宣言的な制御と、より強制力のある命令的な確認の二重構造になっている。

**設定ファイルの一元管理:**
`Pulumi.*.yaml` は gitignore されておりリモートで使えないため、代わりに `.github/config/aws.staging.env` 等のコミット済みファイルに設定値を記述する。CI はこのファイルを `source` して環境変数を読み込む。

---

### 5-5. Azure デプロイの主要ステップ（`deploy-azure.yml`）

```
1. Pulumi（Azure インフラ）
2. Azure Functions 用パッケージビルド
   - linux/amd64 Docker コンテナで pip install（ARM ホストとのアーキテクチャ差異を回避）
   - ZIP 化して Azure CLI でアップロード（az functionapp deployment source config-zip）
3. az storage blob service-properties update で静的 Web サイトホスティング有効化
4. React SPA ビルド・Blob Storage アップロード（az storage blob upload-batch）
5. AFD キャッシュパージ（az afd endpoint purge）
```

**ARM → AMD64 クロスビルド:**
GitHub Actions のランナーは ARM (aarch64) のホストで動作する場合があるため、Lambda / Functions 用の Python パッケージは `--platform linux/amd64` の Docker コンテナ内でインストールする。

```bash
docker run --rm --platform linux/amd64 \
  -v "$(pwd)/package:/package" \
  python:3.12-slim \
  bash -c "pip install -r /package/requirements.txt -t /package"
```

---

### 5-6. GCP デプロイの主要ステップ（`deploy-gcp.yml`）

```
1. google-github-actions/auth で認証（GCP_CREDENTIALS シークレット）
2. Pulumi（GCP インフラ）
3. Docker イメージビルド・Artifact Registry プッシュ
4. Cloud Run サービス更新（gcloud run deploy）
5. React SPA ビルド・GCS アップロード（gsutil rsync）
6. CDN キャッシュ無効化（gcloud compute url-maps invalidate-cdn-cache）
```

---

## 6. フロントエンド SPA デプロイワークフロー

`deploy-frontend-web-*.yml` は API やインフラを触らずに **フロントエンドだけを更新**したい場合に使う差分更新用ワークフローである。React SPA のファイルを変更した際に Pulumi を再実行せずに済むため、デプロイ時間を短縮できる。

### 6-1. AWS (`deploy-frontend-web-aws.yml`)

```
1. Pulumi outputs 取得（バケット名・Cognito 設定・CloudFront ID）
   ← インフラには触れず読み取りのみ
2. npm ci / npm run build
   - VITE_API_URL / VITE_AUTH_PROVIDER=aws / VITE_COGNITO_* を環境変数として注入
3. S3 同期（差分更新）
   - アセット類（JS/CSS）: cache-control max-age=31536000, immutable
   - index.html のみ: max-age=300（ブラウザキャッシュを短くして更新を即反映）
4. Cognito コールバック URL を aws cognito-idp update-user-pool-client で同期
   - CloudFront ドメイン + カスタムドメインの両方を登録
5. CloudFront キャッシュ無効化（/sns/*）
```

**キャッシュ戦略の意図:**
ハッシュ付きアセット（`index-abc123.js` 等）は Vite がファイル名を変えるため長期キャッシュ可。一方 `index.html` は常に最新のアセット名を参照するため短期キャッシュにする。

---

### 6-2. Azure (`deploy-frontend-web-azure.yml`)

```
1. Pulumi outputs 取得（ストレージアカウント名・AFD エンドポイント）
2. npm run build（VITE_AUTH_PROVIDER=azure 等を注入）
3. az storage blob upload-batch で $web/sns/ へアップロード
4. az afd endpoint purge でキャッシュパージ
```

### 6-3. GCP (`deploy-frontend-web-gcp.yml`)

```
1. Pulumi outputs 取得（GCS バケット名）
2. npm run build（VITE_AUTH_PROVIDER=firebase 等を注入）
3. gsutil -m rsync -r dist/ gs://{bucket}/sns/
4. gcloud compute url-maps invalidate-cdn-cache
```

---

## 7. スクリプト群 (`scripts/`)

### 7-1. `build-lambda-layer.sh`

Lambda Layer を `linux/amd64` Docker コンテナでビルドして ZIP 化するスクリプト。
デプロイホストが ARM (Apple M1/M2 / aarch64) でも正しいアーキテクチャのバイナリを生成できる。

```bash
# 主な処理フロー
1. requirements-layer.txt を参照
2. docker run --platform linux/amd64 python:3.12-slim で pip install
3. python/ 以下に配置して ZIP 化 → services/api/lambda-layer.zip
```

Layer には `fastapi`, `mangum`, `pydantic`, `python-jose` 等が含まれる。
`boto3` / `botocore` は Lambda ランタイムに同梱されているため**除外**し、Layer サイズを削減している。

---

### 7-2. `deploy-aws.sh` / `deploy-azure.sh` / `deploy-gcp.sh`

各クラウドに手動デプロイするためのラッパースクリプト。主に開発時の動作確認に使う。CI/CD ワークフロー（`.github/workflows/*.yml`）と同等の処理を行うが、インタラクティブな確認ステップを含む。

---

### 7-3. テストスクリプト群

| スクリプト                 | 内容                                                                          |
| -------------------------- | ----------------------------------------------------------------------------- |
| `test-api.sh`              | 各クラウドの API エンドポイントに curl でリクエストし、ステータスコードを確認 |
| `test-e2e.sh`              | 全クラウドを対象とした E2E テスト（投稿作成→取得→削除）                       |
| `test-sns-aws.sh` 等       | クラウド個別の SNS 機能テスト                                                 |
| `test-auth-crud.sh`        | 認証付き CRUD 操作のテスト                                                    |
| `diagnose-environments.sh` | 各クラウドの設定値・エンドポイントの診断                                      |

---

### 7-4. `bump-version.sh`

`versions.json` のバージョン番号をインクリメントするスクリプト。`version-bump.yml` ワークフローから呼び出される。セマンティックバージョニング（major/minor/patch）に対応。

---

## まとめ：インフラ・CI/CD の設計原則

| 原則                 | 実装箇所                    | 説明                                                                             |
| -------------------- | --------------------------- | -------------------------------------------------------------------------------- |
| **IaC 一元管理**     | `infrastructure/pulumi/`    | クラウドリソースはすべて Pulumi Python コードで定義                              |
| **設定の単一ソース** | `.github/config/*.env`      | `Pulumi.*.yaml` は gitignore されるため、CI 用設定ファイルをリポジトリにコミット |
| **Safety net**       | `deploy-aws.yml`            | Pulumi だけに頼らず AWS CLI で CloudFront / Cognito を事後確認・修正             |
| **ARM/AMD64 分離**   | CI ワークフロー             | Python パッケージは常に `linux/amd64` Docker でビルド                            |
| **キャッシュ戦略**   | `deploy-frontend-web-*.yml` | ハッシュ付きアセット: 永続キャッシュ / `index.html`: 短期キャッシュ              |
| **差分デプロイ**     | `deploy-frontend-web-*.yml` | フロントエンド変更時は Pulumi を再実行しない                                     |
| **同時実行防止**     | `concurrency:` ブロック     | Pulumi の競合エラーを防ぐためスタック単位で直列化                                |
