# セットアップガイド

Multi-Cloud Auto Deploy Platform のセットアップ手順です。

## 前提条件

### 共通
- Git
- Node.js 18+
- Python 3.11+
- Docker & Docker Compose

### クラウド SDK
- **AWS**: AWS CLI v2
- **Azure**: Azure CLI
- **GCP**: gcloud CLI

## 環境変数の設定

プロジェクトルートに`.env`ファイルを作成：

```bash
# AWS
AWS_ACCESS_KEY_ID=your_access_key
AWS_SECRET_ACCESS_KEY=your_secret_key
AWS_REGION=us-east-1

# Azure
AZURE_SUBSCRIPTION_ID=your_subscription_id
AZURE_TENANT_ID=your_tenant_id
AZURE_CLIENT_ID=your_client_id
AZURE_CLIENT_SECRET=your_client_secret

# GCP
GCP_PROJECT_ID=your_project_id
GCP_REGION=us-central1
GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account-key.json

# アプリケーション
PROJECT_NAME=multicloud-auto-deploy
ENVIRONMENT=staging
```

## ローカル開発環境

### 1. フロントエンド

```bash
cd services/frontend
npm install
npm run dev
# http://localhost:3000 でアクセス
```

### 2. バックエンド

```bash
cd services/backend
pip install -r requirements.txt -r requirements-dev.txt
python -m uvicorn src.main:app --reload
# http://localhost:8000 でアクセス
```

### 3. Docker Compose（推奨）

```bash
docker-compose up
# Frontend: http://localhost:3000
# Backend: http://localhost:8000
```

## クラウドデプロイ

### AWS

1. **認証情報の設定**
```bash
aws configure
```

2. **デプロイ**
```bash
./scripts/deploy-aws.sh staging
```

### Azure

1. **ログイン**
```bash
az login
```

2. **デプロイ**
```bash
./scripts/deploy-azure.sh staging
```

### GCP

1. **認証**
```bash
gcloud auth login
gcloud auth application-default login
```

2. **デプロイ**
```bash
./scripts/deploy-gcp.sh staging your-project-id
```

## GitHub Actions

### Secrets設定

GitHubリポジトリの Settings → Secrets and variables → Actions で以下を設定：

#### AWS
- `AWS_ACCESS_KEY_ID`
- `AWS_SECRET_ACCESS_KEY`
- `AWS_S3_BUCKET`
- `AWS_CLOUDFRONT_DISTRIBUTION_ID`
- `AWS_LAMBDA_FUNCTION_NAME`
- `AWS_API_URL`

#### Azure
- `AZURE_CREDENTIALS` (JSON format)
- `AZURE_STORAGE_ACCOUNT`
- `AZURE_RESOURCE_GROUP`
- `AZURE_FUNCTION_APP_NAME`
- `AZURE_API_URL`

#### GCP
- `GCP_CREDENTIALS` (Service Account JSON)
- `GCP_PROJECT_ID`
- `GCP_BUCKET_NAME`
- `GCP_FUNCTION_NAME`
- `GCP_API_URL`

### ワークフローのトリガー

- `main`ブランチへのプッシュで自動デプロイ
- 手動トリガー: Actions → Select workflow → Run workflow

## トラブルシューティング

### AWS Lambda デプロイエラー

```bash
# Lambda用プレースホルダーの再作成
cd infrastructure/pulumi/aws
echo "print('placeholder')" > lambda_placeholder.py
zip lambda_placeholder.zip lambda_placeholder.py
rm lambda_placeholder.py
```

### Azure Functions エラー

```bash
# Azure Functions Core Toolsのインストール
npm install -g azure-functions-core-tools@4
```

### GCP 権限エラー

```bash
# 必要なAPIを有効化
gcloud services enable cloudfunctions.googleapis.com
gcloud services enable cloudbuild.googleapis.com
gcloud services enable storage-api.googleapis.com
```

## 次のステップ

- [AWS デプロイメント詳細](AWS_DEPLOYMENT.md)
- [Azure デプロイメント詳細](AZURE_DEPLOYMENT.md)
- [GCP デプロイメント詳細](GCP_DEPLOYMENT.md)
- [アーキテクチャ](ARCHITECTURE.md)
