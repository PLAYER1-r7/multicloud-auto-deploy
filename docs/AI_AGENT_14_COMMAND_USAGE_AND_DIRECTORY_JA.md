# 14 — コマンド使用法とディレクトリ構成ガイド

> Part I — セットアップ＆リファレンス | AI エージェント向け技術仕様書
> よくあるコマンドエラーを防ぐための実践ガイド

---

## 目次

1. [ディレクトリ構成](#ディレクトリ構成)
2. [パス指定の正しい方法](#パス指定の正しい方法)
3. [頻出コマンド集](#頻出コマンド集)
4. [よくあるエラーと解決策](#よくあるエラーと解決策)
5. [環境変数の設定](#環境変数の設定)

---

## ディレクトリ構成

### 完全なファイルツリー

```
/workspaces/multicloud-auto-deploy/
│
├── .github/
│   └── workflows/                    # GitHub CI/CD workflows
│       ├── deploy-aws.yml
│       ├── deploy-azure.yml
│       ├── deploy-gcp.yml
│       ├── deploy-frontend-web-aws.yml
│       ├── deploy-frontend-web-azure.yml
│       ├── deploy-frontend-web-gcp.yml
│       ├── deploy-landing-aws.yml
│       ├── deploy-landing-azure.yml
│       ├── deploy-landing-gcp.yml
│       ├── version-bump.yml
│       └── codeql.yml
│
├── infrastructure/                   # Infrastructure as Code
│   ├── aws/                          # AWS 固有リソース（IAM など）
│   ├── iam/                          # 共通 IAM ロール
│   └── pulumi/                       # IaC 主体（Python）
│       ├── aws/                      # AWS Pulumi スタック
│       │   ├── __main__.py           # Lambda, API GW, DynamoDB の定義
│       │   └── Pulumi.staging.yaml   # スタック設定（環境ごと）
│       ├── azure/                    # Azure Pulumi スタック
│       │   ├── __main__.py           # Azure Functions, Cosmos DB の定義
│       │   └── Pulumi.staging.yaml
│       └── gcp/                      # GCP Pulumi スタック
│           ├── __main__.py           # Cloud Run, Firestore, GCS の定義
│           └── Pulumi.staging.yaml
│
├── services/                         # アプリケーションコード
│   ├── api/                          # FastAPI バックエンド（全クラウド対応）
│   │   ├── app/                      # FastAPI アプリケーション
│   │   │   ├── __init__.py
│   │   │   ├── main.py               # FastAPI インスタンスと routes 統合
│   │   │   ├── config.py             # 环境設定、AWS/Azure/GCP の判定
│   │   │   ├── models.py             # Pydantic モデル（リクエスト/レスポンス）
│   │   │   ├── auth.py               # 認証・JWT検証ロジック
│   │   │   └── routes/               # エンドポイント定義
│   │   │       ├── __init__.py
│   │   │       ├── posts.py          # POST /posts, GET /posts など
│   │   │       ├── auth.py           # POST /auth/login など
│   │   │       └── health.py         # GET /health（ヘルスチェック）
│   │   ├── backends/                 # クラウド固有の実装
│   │   │   ├── aws_backend.py        # Lambda + DynamoDB + S3
│   │   │   ├── azure_backend.py      # Azure Functions + Cosmos DB + Blob
│   │   │   └── gcp_backend.py        # Cloud Functions + Firestore + GCS
│   │   ├── index.py                  # AWS Lambda エントリーポイント
│   │   ├── function.py               # GCP Cloud Functions エントリーポイント
│   │   ├── function_app.py           # Azure Functions エントリーポイント
│   │   ├── Dockerfile                # コンテナイメージ
│   │   ├── Dockerfile.lambda         # Lambda 用 コンテナイメージ
│   │   ├── requirements.txt           # 共通依存関係（FastAPI など）
│   │   ├── requirements-aws.txt       # AWS 固有（boto3 など）
│   │   ├── requirements-azure.txt     # Azure 固有（azure-cosmos など）
│   │   ├── requirements-gcp.txt       # GCP 固有（google-cloud など）
│   │   ├── requirements-dev.txt       # 開発用（pytest など）
│   │   ├── requirements-layer.txt     # Lambda Layer 用
│   │   ├── pytest.ini                 # pytest 設定
│   │   ├── tests/                     # ユニットテスト＆統合テスト
│   │   │   ├── test_api.py
│   │   │   ├── test_auth.py
│   │   │   ├── test_posts.py
│   │   │   └── conftest.py
│   │   └── .venv/                     # Python 仮想環境（git ignored）
│   │
│   ├── frontend_react/               # React SPA フロントエンド（Vite）
│   │   ├── src/
│   │   │   ├── main.tsx               # React エントリーポイント
│   │   │   ├── App.tsx                # ルートコンポーネント
│   │   │   ├── vite-env.d.ts          # Vite 型定義
│   │   │   ├── api/                   # API クライアント
│   │   │   │   └── client.ts          # fetch/axios ベース HTTP クライアント
│   │   │   ├── components/            # React コンポーネント
│   │   │   ├── pages/                 # ページコンポーネント（SNS 関連など）
│   │   │   ├── store/                 # グローバルステート（Zustand など）
│   │   │   ├── styles/                # CSS/Tailwind スタイル
│   │   │   └── utils/                 # ユーティリティ関数
│   │   ├── public/                    # 静的アセット（logo など）
│   │   ├── index.html                 # HTML テンプレート
│   │   ├── vite.config.ts             # Vite 設定（base="/sns/" など）
│   │   ├── package.json               # npm 依存関係
│   │   ├── package-lock.json          # npm lock file
│   │   ├── tsconfig.json              # TypeScript 設定
│   │   ├── tailwind.config.js         # Tailwind CSS 設定
│   │   ├── eslint.config.js           # ESLint 設定
│   │   ├── postcss.config.js          # PostCSS 設定
│   │   ├── nginx.conf                 # nginx 設定（Docker 用）
│   │   ├── Dockerfile                 # React コンテナイメージ
│   │   ├── dist/                      # ビルド出力（git ignored）
│   │   ├── node_modules/              # npm packages（git ignored）
│   │   ├── .env.example               # 環境変数テンプレート
│   │   ├── .env.aws.staging           # AWS staging 用（git ignored）
│   │   └── .env.local                 # ローカル開発用（git ignored）
│   │
│   ├── frontend_web/                  # Python SSR フロントエンド（レガシー —未使用）
│   │   ├── app.py
│   │   ├── requirements.txt
│   │   └── .venv/
│   │
│   ├── frontend_exam/                 # 試験対応フロントエンド（実験的）
│   │   └── ...
│   │
│   └── michinoeki-scraper/            # サンプルスクレイパー
│       └── ...
│
├── scripts/                           # デプロイ・テスト・管理スクリプト
│   ├── deploy-aws.sh                  # AWS デプロイスクリプト
│   ├── deploy-azure.sh                # Azure デプロイスクリプト
│   ├── deploy-gcp.sh                  # GCP デプロイスクリプト
│   ├── deploy-static-site.sh          # 静的サイト（ランディング）デプロイ
│   ├── test-api.sh                    # API 統合テスト
│   ├── test-deployment.sh             # デプロイメントテスト
│   ├── test-sns-aws.sh                # AWS SNS エンドポイントテスト
│   ├── test-sns-azure.sh              # Azure SNS エンドポイントテスト
│   ├── test-sns-gcp.sh                # GCP SNS エンドポイントテスト
│   ├── test-cloud-env.sh              # クラウド環境テスト
│   ├── build-lambda-layer.sh          # Lambda Layer ビルド
│   ├── bump-version.sh                # バージョンコマンド（git hooks から自動実行）
│   ├── generate-changelog.sh           # チェンジログ生成
│   ├── monitor-cicd.sh                # CI/CD 監視
│   ├── audit-cdn-cache.sh             # CDN キャッシュ監査
│   ├── manage-github-secrets.sh        # GitHub Secrets 管理
│   └── ...
│
├── static-site/                       # 静的サイト資源（ランディングページ）
│   ├── index.html                     # ランディングページ HTML
│   ├── styles.css                     # CSS スタイル
│   ├── aws/                           # AWS 説明ページ
│   ├── azure/                         # Azure 説明ページ
│   ├── gcp/                           # GCP 説明ページ
│   └── images/                        # 画像資源
│
├── docs/                              # ドキュメント(md)
│   ├── AI_AGENT_00_CRITICAL_RULES_JA.md
│   ├── AI_AGENT_01_CONTEXT_JA.md
│   ├── AI_AGENT_02_ARCHITECTURE_JA.md
│   ├── AI_AGENT_03_API_JA.md
│   ├── AI_AGENT_04_INFRA_JA.md
│   ├── AI_AGENT_05_CICD_JA.md
│   ├── AI_AGENT_07_RUNBOOKS_JA.md
│   ├── AI_AGENT_08_SECURITY_JA.md
│   ├── AI_AGENT_13_TESTING_JA.md
│   ├── AI_AGENT_14_COMMAND_USAGE_AND_DIRECTORY_JA.md  # ← このファイル
│   ├── REFACTORING_REPORT_20260222.md
│   └── ...
│
├── .devcontainer/                    # Dev Container 設定
│   ├── docker-compose.yml
│   └── devcontainer.json
│
├── .github/                          # GitHub 設定
│   ├── dependabot.yml
│   └── workflows/（上記参照）
│
├── .githooks/                        # Git hooks（version bump など）
│   └── pre-commit
│
├── .venv/                            # プロジェクトルートの仮想環境（git ignored）
│
├── htmlcov/                          # pytest カバレッジレポート出力先
│
├── Makefile                          # Make ターゲット（よく使うコマンド集）
├── docker-compose.yml                # Local development Docker Compose
├── versions.json                     # バージョン管理ファイル（git tracked）
├── CHANGELOG.md                      # チェンジログ（自動生成）
├── README.md                         # プロジェクト README
├── PRODUCTION_CHECKLIST.md           # 本番環境でのチェックリスト
├── TROUBLESHOOTING.md                # トラブルシューティングガイド
└── LICENSE                           # MIT License
```

---

## パス指定の正しい方法

### ✅ 正しい例

#### 相対パス（推奨）

```bash
# プロジェクトルートから相対パス
cd services/api
cd services/frontend_react
cd infrastructure/pulumi/aws

# パスの移動時は -r オプションで確認
find services -name "*.py" -type f
```

#### 絶対パス（スクリプト・CI/CD 用）

```bash
# スクリプト内で環境に依存しない方法
PROJECT_ROOT="/workspaces/multicloud-auto-deploy"
API_DIR="${PROJECT_ROOT}/services/api"
FRONTEND_DIR="${PROJECT_ROOT}/services/frontend_react"
SCRIPTS_DIR="${PROJECT_ROOT}/scripts"

# スクリプト実行時
cd "${API_DIR}" || exit 1
```

### ❌ よくあるエラー

| エラー                                        | 原因                              | 解決策                                                          |
| --------------------------------------------- | --------------------------------- | --------------------------------------------------------------- |
| `No such file or directory: services/api`     | 現在のディレクトリを間違えている  | `pwd` で確認、プロジェクトルートに移動                          |
| `frontend` ディレクトリが見つからない         | 正式名は `frontend_react`         | 正しいパス: `services/frontend_react`                           |
| `backend` ディレクトリが見つからない          | 正式名は `api`                    | 正しいパス: `services/api`                                      |
| `infrastructure/terraform/aws` が見つからない | Terraform は使用せず、Pulumi 推奨 | 正しいパス: `infrastructure/pulumi/aws`                         |
| `requirements.txt` が複数存在                 | 環境ごとに異なる                  | `requirements.txt`, `-aws.txt`, `-azure.txt`, `-gcp.txt` を確認 |

---

## 頻出コマンド集

### 1. マスター Makefile コマンド

仕事のルートディレクトリで実行：

```bash
# プロジェクトルートで実行
cd /workspaces/multicloud-auto-deploy

# ヘルプを表示
make help

# インストール（フロントエンド + バックエンド全体）
make install

# フロントエンドビルド
make build-frontend

# バックエンドビルド（AWS Lambda x86_64 用）
make build-backend

# デプロイ
make deploy-aws              # AWS Lambda + Frontend
make deploy-azure            # Azure Functions + Frontend
make deploy-gcp              # GCP Cloud Run + Frontend

# テスト
make test-aws                # AWS エンドポイントテスト
make test-azure              # Azure エンドポイントテスト
make test-gcp                # GCP エンドポイントテスト
make test-all                # 全クラウドテスト

# Terraform（AWS IaC）
make terraform-init          # Terraform を初期化
make terraform-plan          # 反映予定の変更を表示
make terraform-apply         # Terraform で インフラをデプロイ

# 環境クリーンアップ
make clean                   # ビルド成果物を削除

# バージョン管理
make hooks-install           # git hooks 有効化（初回セットアップ）
make version                 # 現在のバージョン表示
make version-major COMPONENT=all           # メジャー(X) インクリメント
make version-minor COMPONENT=aws-static-site  # マイナー(Y) インクリメント
```

### 2. API サービスコマンド

```bash
cd /workspaces/multicloud-auto-deploy/services/api

# Python 仮想環境を作成＆有効化
python3 -m venv .venv
source .venv/bin/activate  # Unix/Mac
# .venv\Scripts\activate   # Windows

# 共通依存関係をインストール
pip install -r requirements.txt

# AWS 専用の依存関係を追加
pip install -r requirements-aws.txt

# 開発用の依存関係をインストール（テスト実行時）
pip install -r requirements-dev.txt

# テストを実行
pytest tests/ -v            # 詳細出力
pytest tests/ --cov=app     # カバレッジレポート
pytest tests/ -k "test_posts"  # 特定テストを実行

# API をローカルで実行（開発用）
# AWS Lambda 環境をシミュレート
python3 index.py            # Lambda ハンドラー

# または FastAPI を直接実行
python3 -c "from app.main import app; import uvicorn; uvicorn.run(app, host='0.0.0.0', port=8000)"

# Lambda ZIP パッケージを作成
cd services/api
rm -rf .build && mkdir -p .build/package
cp -r app .build/package/
cp index.py .build/package/
cd .build/package && zip -r ../../lambda.zip . && cd ../..

# Lambda を AWS にアップロード（aws cli 必須）
aws lambda update-function-code \
  --function-name multicloud-auto-deploy-staging-api \
  --zip-file fileb://lambda.zip \
  --region ap-northeast-1
```

### 3. React フロントエンド コマンド

```bash
cd /workspaces/multicloud-auto-deploy/services/frontend_react

# npm 依存関係をインストール
npm install
# または lock ファイルから (CI/CD 推奨)
npm ci

# 開発サーバーを起動（http://localhost:5173）
npm run dev

# ビルド（本番用）
# API URL を指定してビルド
VITE_API_URL=https://z42qmqdqac.execute-api.ap-northeast-1.amazonaws.com npm run build

# AWS S3 にアップロード（aws cli 必須）
aws s3 sync dist/ s3://multicloud-auto-deploy-staging-frontend/sns/ \
  --delete --region ap-northeast-1

# CloudFront キャッシュを無効化
aws cloudfront create-invalidation \
  --distribution-id E1TBH4R432SZBZ \
  --paths "/*"

# ローカルプレビュー（ビルド後）
npm run preview
```

### 4. Pulumi インフラ管理コマンド

```bash
# AWS スタック
cd /workspaces/multicloud-auto-deploy/infrastructure/pulumi/aws
pulumi stack list                # 利用可能なスタック表示
pulumi stack select staging       # スタックを選択
pulumi preview                    # デプロイ前のプレビュー
pulumi up --yes                   # インフラをデプロイ
pulumi destroy --yes              # リソースを削除

# Azure スタック
cd ../azure
pulumi stack select staging
pulumi up --yes

# GCP スタック
cd ../gcp
pulumi stack select staging
pulumi up --yes
```

### 5. テストスクリプト

```bash
# API エンドポイントテスト（curl + jq 必須）
./scripts/test-api.sh -e https://z42qmqdqac.execute-api.ap-northeast-1.amazonaws.com --verbose

# AWS SNS ページテスト
./scripts/test-sns-aws.sh

# Azure SNS ページテスト
./scripts/test-sns-azure.sh

# GCP SNS ページテスト
./scripts/test-sns-gcp.sh

# 全クラウド デプロイテスト
./scripts/test-deployments.sh

# 統合テスト実行
./scripts/run-integration-tests.sh
```

### 6. デプロイスクリプト

```bash
# AWS デプロイ（Terraform 使用）
./scripts/deploy-aws.sh staging

# Azure デプロイ
./scripts/deploy-azure.sh staging

# GCP デプロイ
./scripts/deploy-gcp.sh staging

# 静的サイト（ランディングページ）デプロイ
./scripts/deploy-static-site.sh aws staging
./scripts/deploy-static-site.sh azure staging
./scripts/deploy-static-site.sh gcp staging
```

### 7. バージョン管理コマンド

```bash
# git hooks を初回セットアップ
make hooks-install

# 現在のバージョン表示
make version

# 手動でメジャーバージョンをインクリメント
make version-major COMPONENT=all

# 手動でマイナーバージョンをインクリメント
make version-minor COMPONENT=aws-static-site

# 手動でパッチバージョンをインクリメント
make version-patch COMPONENT=all
```

---

## よくあるエラーと解決策

### 🔴 Error: `cd: services/frontend: No such file or directory`

**原因**: フロントエンドディレクトリ名が間違っている

**解決策**:

```bash
# ❌ 誤り
cd services/frontend

# ✅ 正しい
cd services/frontend_react
```

---

### 🔴 Error: `requirements.txt: No such module`

**原因**: 仮想環境が有効化されていないか、インストールフォルダが異なる

**解決策**:

```bash
# 1. 仮想環境を確認
which python3  # /workspaces/multicloud-auto-deploy/services/api/.venv/bin/python3 と表示されるはず

# 2. 有効化されていなければ再実行
source /workspaces/multicloud-auto-deploy/services/api/.venv/bin/activate

# 3. 再度インストール
pip install -r requirements.txt
```

---

### 🔴 Error: `aws lambda update-function-code: parameter validation failed`

**原因**: Lambda 関数名やリージョンが間違っている

**解決策**:

```bash
# 1. デプロイ対象を確認
aws lambda list-functions --region ap-northeast-1 | jq '.Functions[].FunctionName'

# 2. 正しい関数名を確認してコマンドを実行
aws lambda update-function-code \
  --function-name multicloud-auto-deploy-staging-api \
  --zip-file fileb://lambda.zip \
  --region ap-northeast-1  # リージョンは ap-northeast-1（東京）
```

---

### 🔴 Error: `VITE_API_URL is not defined` (React ビルド時)

**原因**: 環境変数が設定されていない

**解決策**:

```bash
cd services/frontend_react

# ❌ 誤り（環境変数が指定されていない）
npm run build

# ✅ 正しい（API URL を指定）
VITE_API_URL=https://z42qmqdqac.execute-api.ap-northeast-1.amazonaws.com npm run build
```

---

### 🔴 Error: `CloudFront distribution ID not found`

**原因**: CloudFront Distribution ID が間違っているか、リージョンが異なる

**解決策**:

```bash
# CloudFront 存在確認
aws cloudfront list-distributions | jq '.DistributionList.Items[].Id'

# 正しい Distribution ID を確認（通常 E で始まる）
# ステージング: E1TBH4R432SZBZ
# 本番: E214XONKTXJEJD

# 正しいコマンド
aws cloudfront create-invalidation \
  --distribution-id E1TBH4R432SZBZ \
  --paths "/*"
```

---

### 🔴 Error: `pulumi: stack not found`

**原因**: Pulumi スタックが選択されていない

**解決策**:

```bash
# 1. 利用可能なスタック確認
cd infrastructure/pulumi/aws
pulumi stack list

# 2. スタック選択
pulumi stack select staging

# 3. スタックが存在しなければ新規作成
pulumi stack init staging
```

---

### 🔴 Error: `npm ERR! 404 package not found`

**原因**: npm レジストリから削除されたパッケージがある

**解決策**:

```bash
# キャッシュクリア
npm cache clean --force

# lock ファイル削除
rm package-lock.json

# 再インストール
npm install
```

---

## 環境変数の設定

### AWS バックエンド

**ローカル開発用（`.env.aws.staging`）**:

```env
# AWS
AWS_REGION=ap-northeast-1
AWS_POSTS_TABLE_NAME=multicloud-auto-deploy-staging-posts
AWS_IMAGES_BUCKET_NAME=multicloud-auto-deploy-staging-images

# API
CLOUD_PROVIDER=aws
API_ENDPOINT=https://z42qmqdqac.execute-api.ap-northeast-1.amazonaws.com
```

**Lambda 環境変数（AWS Management Console または aws cli）**:

```bash
aws lambda update-function-configuration \
  --function-name multicloud-auto-deploy-staging-api \
  --environment Variables="{
    CLOUD_PROVIDER=aws,
    AWS_REGION=ap-northeast-1,
    AWS_POSTS_TABLE_NAME=multicloud-auto-deploy-staging-posts,
    AWS_IMAGES_BUCKET_NAME=multicloud-auto-deploy-staging-images
  }" \
  --region ap-northeast-1
```

---

### Azure バックエンド

**ローカル開発用（`local.settings.json`）**:

```json
{
  "IsEncrypted": false,
  "Values": {
    "AZURE_COSMOS_ENDPOINT": "https://multicloud-auto-deploy-staging.documents.azure.com:443/",
    "AZURE_COSMOS_KEY": "****",
    "AZURE_COSMOS_DATABASE": "simple-sns",
    "AZURE_COSMOS_CONTAINER": "items",
    "AZURE_STORAGE_ACCOUNT_NAME": "mcadwebd45ihd",
    "AZURE_STORAGE_ACCOUNT_KEY": "****",
    "AZURE_STORAGE_CONTAINER": "images",
    "CLOUD_PROVIDER": "azure"
  }
}
```

**Azure Functions（Azure Portal または az cli）**:

```bash
az functionapp config appsettings set \
  --name multicloud-auto-deploy-staging-func \
  --resource-group multicloud-auto-deploy-staging-rg \
  --settings \
    AZURE_COSMOS_ENDPOINT=https://multicloud-auto-deploy-staging.documents.azure.com:443/ \
    AZURE_COSMOS_KEY='****' \
    CLOUD_PROVIDER=azure
```

---

### GCP バックエンド

**ローカル開発用（`.env.gcp`）**:

```env
# GCP
GCP_PROJECT_ID=ashnova
GCP_FIRESTORE_COLLECTION=posts
GCP_BUCKET_NAME=ashnova-multicloud-auto-deploy-staging-frontend

# API
CLOUD_PROVIDER=gcp
API_ENDPOINT=https://multicloud-auto-deploy-staging-api-son5b3ml7a-an.a.run.app
```

**Cloud Run（gcloud cli）**:

```bash
gcloud run deploy multicloud-auto-deploy-staging-api \
  --region asia-northeast1 \
  --set-env-vars CLOUD_PROVIDER=gcp,GCP_PROJECT_ID=ashnova,GCP_FIRESTORE_COLLECTION=posts
```

---

## チェックリスト

コマンド実行前に確認：

- [ ] 正しいディレクトリ（`pwd`）か確認
- [ ] 環境変数（`echo $VITE_API_URL` など）が設定されているか確認
- [ ] 仮想環境が有効か確認（`which python3` で `.venv/bin/python3` を参照）
- [ ] AWS CLI/Azure CLI/gcloud が認証されているか確認（`aws sts get-caller-identity` など）
- [ ] 必要なファイル（requirements.txt など）が存在するか確認
- [ ] インターネット接続が正常か確認（特に package install 時）

---

## クイックリファレンス

| 作業内容            | コマンド                                   | 場所                             |
| ------------------- | ------------------------------------------ | -------------------------------- |
| ヘルプ表示          | `make help`                                | プロジェクトルート               |
| API テスト          | `./scripts/test-api.sh -e <URL> --verbose` | プロジェクトルート               |
| Lambda アップロード | `aws lambda update-function-code ...`      | `services/api/`                  |
| React ビルド        | `VITE_API_URL=... npm run build`           | `services/frontend_react/`       |
| Pulumi デプロイ     | `pulumi up --yes`                          | `infrastructure/pulumi/<cloud>/` |
| バージョン確認      | `make version`                             | プロジェクトルート               |
| テスト実行          | `pytest tests/ -v`                         | `services/api/`                  |

---

**更新日**: 2026-03-04
**バージョン**: 1.0.0
**対象**: AI エージェント向け実装ガイド
