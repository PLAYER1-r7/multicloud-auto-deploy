# Getting Started - Overview

## プロジェクト概要

**multicloud-auto-deploy** は AWS / Azure / GCP の3つのクラウドに同時にデプロイする SNS アプリケーションプラットフォームです。

### アーキテクチャ概要

```
┌─────────────────────────────────────────────────────────────┐
│                     React SPA Frontend                       │
│  (CloudFront / Front Door / Cloud CDN 経由で配信)            │
└─────────────────────────────────────────────────────────────┘
                 ↓ ↓ ↓
  ┌──────────────┬──────────────┬──────────────┐
  │              │              │              │
  ▼              ▼              ▼
┌─────────┐  ┌─────────┐  ┌─────────┐
│   AWS   │  │  Azure  │  │   GCP   │
├─────────┤  ├─────────┤  ├─────────┤
│Lambda   │  │Function │  │Cloud    │
│API GWv2 │  │Apps     │  │Run      │
│DynamoDB │  │CosmosDB │  │Firestore│
│S3       │  │Storage  │  │Cloud    │
│         │  │         │  │Storage  │
└─────────┘  └─────────┘  └─────────┘
```

### 主な特徴

✅ **3つのクラウドに完全対応**
- AWS: Lambda + API Gateway + DynamoDB + S3
- Azure: Functions + Cosmos DB + Blob Storage
- GCP: Cloud Run + Firestore + Cloud Storage

✅ **完全自動デプロイ**
- GitHub Actions ワークフロー
- Pulumi によるインフラストラクチャ管理
- 同一ビルド成果物で3クラウドにデプロイ

✅ **本番セキュリティ対応**
- CORS 絞り込み
- HTTPS リダイレクト
- CloudTrail / Audit Logs
- IAM ロール + Managed Identity
- Key Vault 診断ログ

✅ **カスタムドメイン対応**
- www.aws.ashnova.jp
- www.azure.ashnova.jp
- www.gcp.ashnova.jp

## 開発環境セットアップ

### 1. 前提条件のインストール

```bash
# macOS (Homebrew)
brew install python@3.12 docker pulumi aws-cli azure-cli

# Ubuntu/Debian
sudo apt-get update
sudo apt-get install -y python3.12 python3.12-venv docker.io
curl -fsSL https://get.pulumi.com | sh
```

### 2. クラウド CLI の設定

```bash
# AWS
aws configure
export AWS_REGION=ap-northeast-1

# Azure
az login
az account set --subscription <SUBSCRIPTION_ID>

# GCP
gcloud auth application-default login
gcloud config set project <PROJECT_ID>
```

### 3. リポジトリのセットアップ

```bash
git clone https://github.com/PLAYER1-r7/multicloud-auto-deploy.git
cd multicloud-auto-deploy

# 仮想環境
python3.12 -m venv .venv
source .venv/bin/activate

# 依存関係
pip install -r requirements.txt
cd infrastructure/pulumi && pip install -r requirements.txt && cd ../..
cd services/api && pip install -r requirements.txt && cd ../..
```

### 4. Pulumi Stack の初期化

```bash
cd infrastructure/pulumi

# AWS Staging
pulumi stack select aws/staging

# Azure Staging
pulumi stack select azure/staging

# GCP Staging
pulumi stack select gcp/staging
```

## トラブルシューティング

### Python バージョンの問題

```bash
# 確認
python3 --version

# 3.12+ が必要です
python3.12 -m venv .venv
```

### Pulumi の認証

```bash
# Pulumi ログイン
pulumi login

# スタック確認
pulumi stack ls
```

## 次のステップ

- [セットアップガイド](setup.md)
- [クイックスタート](quickstart.md)
- [実装ガイド](../implementation-guide.md)
