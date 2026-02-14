# Multi-Cloud Auto Deploy Platform

[![Deploy to AWS](https://github.com/PLAYER1-r7/multicloud-auto-deploy/actions/workflows/deploy-aws.yml/badge.svg)](https://github.com/PLAYER1-r7/multicloud-auto-deploy/actions/workflows/deploy-aws.yml)
[![Deploy to Azure](https://github.com/PLAYER1-r7/multicloud-auto-deploy/actions/workflows/deploy-azure.yml/badge.svg)](https://github.com/PLAYER1-r7/multicloud-auto-deploy/actions/workflows/deploy-azure.yml)
[![Deploy to GCP](https://github.com/PLAYER1-r7/multicloud-auto-deploy/actions/workflows/deploy-gcp.yml/badge.svg)](https://github.com/PLAYER1-r7/multicloud-auto-deploy/actions/workflows/deploy-gcp.yml)

**マルチクラウド対応の自動デプロイシステム** - AWS/Azure/GCP対応のフルスタックアプリケーション自動デプロイプラットフォーム

> 🐍 **NEW: Python Full Stack版が利用可能になりました！** Pulumi + FastAPI + Reflex による完全Python実装。詳細は [docs/PYTHON_MIGRATION.md](docs/PYTHON_MIGRATION.md) を参照。

## 🌐 Live Demos

| Cloud Provider | API Endpoint | Frontend |
|---------------|--------------|----------|
| **AWS** (ap-northeast-1) | [API](https://52z731x570.execute-api.ap-northeast-1.amazonaws.com/) | [CloudFront](https://dx3l4mbwg1ade.cloudfront.net) ✅ |
| **Azure** (japaneast) | [Container Apps API](https://mcad-staging-api.livelycoast-fa9d3350.japaneast.azurecontainerapps.io) 🆕 | [Container Apps Frontend](https://mcad-staging-frontend.livelycoast-fa9d3350.japaneast.azurecontainerapps.io) ✅ 🆕 |
| **GCP** (asia-northeast1) | [Cloud Run API](https://mcad-staging-api-son5b3ml7a-an.a.run.app) 🆕 | [Cloud Run Frontend](https://mcad-staging-frontend-son5b3ml7a-an.a.run.app) ✅ 🆕 |

> 🐍 **Azure & GCP**: Pure Python Full Stack（FastAPI + Reflex）がContainer AppsとCloud Runで稼働中！
> 
> 📋 詳細なエンドポイント情報は [docs/ENDPOINTS.md](docs/ENDPOINTS.md) を参照してください

## 🚀 特徴

- **マルチクラウド対応**: AWS、Azure、GCPに対応
- **フルスタック**: フロントエンド、バックエンド、データベースの完全なスタック
- **自動デプロイ**: GitHub Actionsによる完全自動化
- **IaC統合**: TerraformとPulumiの両方に対応 🆕
- **完全Python版**: Pulumi + FastAPI + Reflexによる統一スタック 🆕
- **CI/CD**: プッシュやPRで自動的にビルド・デプロイ
- **簡単セットアップ**: スクリプト一つで環境構築

## 📁 プロジェクト構造

```
multicloud-auto-deploy/
├── .github/workflows/     # GitHub Actionsワークフロー
├── infrastructure/        # インフラストラクチャコード
│   ├── terraform/        # Terraformコード（AWS/Azure/GCP）
│   └── pulumi/           # 🆕 Pulumiコード（Python - AWS/Azure/GCP）
├── services/             # アプリケーションコード
│   ├── api/              # 🆕 FastAPI バックエンド（Python）
│   ├── frontend_reflex/  # ✨ Reflex フロントエンド（Python）
│   └── backend/          # Legacy バックエンド（Python）
├── scripts/              # デプロイスクリプト
└── docs/                 # ドキュメント
    └── PYTHON_MIGRATION.md  # 🆕 Python完全版移行ガイド
```

## 🛠️ セットアップ

### 前提条件

- Python 3.12+
- Docker & Docker Compose
- Pulumi 3.0+ または Terraform 1.5+
- AWS CLI 2.x / Azure CLI 2.x / gcloud CLI 556.0+
- GitHub アカウント

### 技術スタック

**🐍 Python Full Stack**
- **IaC**: Pulumi (Python) / Terraform (HCL)
- **Backend**: FastAPI 1.0+ 
- **Frontend**: Reflex 0.8+ (Pure Python, no JavaScript/React)
- **Database**: DynamoDB / Cosmos DB / Firestore
- **Storage**: S3 / Azure Blob / Cloud Storage / MinIO (local)

**Infrastructure**
- Pulumi 3.0+ / Terraform 1.14+
- AWS Lambda (x86_64) / Azure Container Apps / Cloud Run
- API Gateway v2 (HTTP)
- S3 + CloudFront
- DynamoDB

**CI/CD**
- GitHub Actions
- Automated builds and deployments
- Docker-based deployments
- S3-based Lambda deployment

### クイックスタート

#### 🐍 Python Full Stack版（推奨）

1. **リポジトリをクローン**
```bash
git clone https://github.com/PLAYER1-r7/multicloud-auto-deploy.git
cd multicloud-auto-deploy
```

2. **ローカル開発環境起動**
```bash
# Python Full Stack（FastAPI + Reflex + MinIO）
docker-compose up -d api frontend_reflex minio

# アクセス先:
# - Reflex Frontend: http://localhost:3002
# - FastAPI API Docs: http://localhost:8000/docs
# - MinIO Console: http://localhost:9001 (admin/minioadmin)
```

3. **Pulumiでデプロイ**
```bash
# AWS例
cd infrastructure/pulumi/aws/simple-sns
pip install -r requirements.txt
pulumi stack init staging
pulumi config set aws:region ap-northeast-1
pulumi up
```

> 📚 詳細な移行ガイドは [docs/PYTHON_MIGRATION.md](docs/PYTHON_MIGRATION.md) を参照

#### Terraform版

1. **リポジトリをクローン**
```bash
git clone https://github.com/PLAYER1-r7/multicloud-auto-deploy.git
cd multicloud-auto-deploy
```

2. **環境変数を設定**
```bash
cp .env.example .env
# .envファイルを編集して認証情報を設定
```

3. **クラウドプロバイダー別デプロイ**

#### AWS
```bash
./scripts/deploy-aws.sh
```

#### Azure
```bash
./scripts/deploy-azure.sh
```

#### GCP
```bash
./scripts/deploy-gcp.sh
```

## 📚 ドキュメント

### 必読ガイド
- 📖 [セットアップガイド](docs/SETUP.md) - 初期セットアップ手順
- 🚀 [CI/CD設定](docs/CICD_SETUP.md) - GitHub Actions自動デプロイ設定
- ✅ [CI/CDテスト結果](docs/CICD_TEST_RESULTS.md) - パイプライン検証レポート ⭐ NEW
- 🔧 [トラブルシューティング](docs/TROUBLESHOOTING.md) - よくある問題と解決策
- 🌐 [エンドポイント一覧](docs/ENDPOINTS.md) - 全環境のエンドポイント情報
- 📝 [クイックリファレンス](docs/QUICK_REFERENCE.md) - よく使うコマンド集 ⭐ NEW

### プロバイダー別デプロイ
- [AWS デプロイ](docs/AWS_DEPLOYMENT.md)
- [Azure デプロイ](docs/AZURE_DEPLOYMENT.md)
- [GCP デプロイ](docs/GCP_DEPLOYMENT.md)

### アーキテクチャ
- [システムアーキテクチャ](docs/ARCHITECTURE.md) - 完全版システム設計

## 🔄 GitHub Actions 自動デプロイ

プッシュやPRで自動的にビルド・デプロイが実行されます：

- `main`ブランチへのプッシュ → ステージング環境へ自動デプロイ
- PRの作成/更新 → ビルド検証
- 手動トリガー → 任意の環境へデプロイ

### ワークフロー

| ワークフロー | トリガー | デプロイ先 | 説明 |
|------------|---------|-----------|------|
| **deploy-multicloud.yml** | `main`へのpush / 手動 | Azure + GCP | Container Apps/Cloud Runへの統合デプロイ 🆕 |
| **deploy-aws.yml** | `main`へのpush / 手動 | AWS Lambda | Lambda関数の更新 |
| **deploy-azure.yml** | `main`へのpush / 手動 | Azure | Terraform使用 |
| **deploy-gcp.yml** | `main`へのpush / 手動 | GCP | Terraform使用 |

### マルチクラウドデプロイフロー 🆕

1. **Build Images**: 
   - APIとFrontendのDockerイメージをビルド（linux/amd64）
   - Azure ACRとGCP Artifact Registryにプッシュ

2. **Deploy Azure** (並列実行):
   - Container Apps（API + Frontend）を更新

3. **Deploy GCP** (並列実行):
   - Cloud Run（API + Frontend）を更新

4. **Health Check**:
   - デプロイされたAPIのヘルスチェック

### 必要なGitHub Secrets

以下のシークレットを設定してください（詳細は [CI/CD設定ガイド](docs/CI_CD_SETUP.md) 参照）：

**Azure Container Apps** 🆕
- `AZURE_CREDENTIALS` - Service Principal認証情報
- `AZURE_CONTAINER_REGISTRY` - ACRログインサーバー
- `AZURE_CONTAINER_REGISTRY_USERNAME/PASSWORD` - ACR認証情報
- `AZURE_RESOURCE_GROUP` - リソースグループ名
- `AZURE_CONTAINER_APP_API` - APIのContainer App名
- `AZURE_CONTAINER_APP_FRONTEND` - FrontendのContainer App名

**GCP Cloud Run** 🆕
- `GCP_CREDENTIALS` - サービスアカウントキー（JSON）
- `GCP_PROJECT_ID` - プロジェクトID
- `GCP_ARTIFACT_REGISTRY_REPO` - Artifact Registryリポジトリ名
- `GCP_CLOUD_RUN_API` - APIのCloud Runサービス名
- `GCP_CLOUD_RUN_FRONTEND` - FrontendのCloud Runサービス名

**AWS Lambda**
- `AWS_ACCESS_KEY_ID`
- `AWS_SECRET_ACCESS_KEY`

### デプロイ状況

最新のデプロイ状況は[GitHub Actions](https://github.com/PLAYER1-r7/multicloud-auto-deploy/actions)で確認できます。

### 手動デプロイ

GitHub Actionsページから手動でワークフローを実行：

```bash
# GitHub上で
Actions > Deploy to Multi-Cloud > Run workflow

# オプション:
- environment: staging / production
- deploy_target: all / azure / gcp
```

## 🏗️ サポートされるアーキテクチャ

### AWS (ap-northeast-1) ✅ 運用中
- **Frontend**: S3 (Static Hosting) + CloudFront (CDN)
- **Backend**: Lambda (Python 3.12, x86_64) + API Gateway v2 (HTTP)
- **Database**: DynamoDB
- **Auth**: Cognito (予定)
- **Infrastructure**: Terraform 1.14.5
- **Deployment**: GitHub Actions (S3-based Lambda deployment)

### Azure (japaneast) ✅ 運用中
- **Frontend**: Container Apps (Reflex - Pure Python) 🆕
- **Backend**: Container Apps (FastAPI) 🆕
- **Database**: Cosmos DB / Azure SQL
- **Storage**: Azure Blob Storage
- **Auth**: Azure AD B2C (予定)
- **Infrastructure**: Pulumi / Terraform
- **Deployment**: GitHub Actions (Azure Container Registry)
- **Container Registry**: Azure Container Registry (ACR)

### GCP (asia-northeast1) ✅ 運用中
- **Frontend**: Cloud Run (Reflex - Pure Python) 🆕
- **Backend**: Cloud Run (FastAPI) 🆕
- **Database**: Firestore / Cloud SQL
- **Storage**: Cloud Storage
- **Auth**: Firebase Auth (予定)
- **Infrastructure**: Pulumi / Terraform
- **Deployment**: GitHub Actions (Artifact Registry)
- **Container Registry**: Artifact Registry

## 🛠️ 開発ツール

### 便利なスクリプト

プロジェクトには以下の便利なスクリプトが含まれています：

```bash
# エンドポイントテスト（全環境）
./scripts/test-endpoints.sh

# GitHub Secrets設定ガイド
./scripts/setup-github-secrets.sh

# GCPリソースインポート
./scripts/import-gcp-resources.sh

# システム診断
./scripts/diagnostics.sh

# デプロイスクリプト
./scripts/deploy-aws.sh
./scripts/deploy-azure.sh
./scripts/deploy-gcp.sh
```

### Makefile

```bash
make install         # 依存関係をインストール
make build-frontend  # フロントエンドをビルド
make build-backend   # Lambda パッケージを作成
make test-all        # 全クラウドのデプロイメントをテスト
make deploy-aws      # AWSへデプロイ
make terraform-init  # Terraform初期化
make terraform-apply # Terraformリソースを適用
make clean           # ビルド成果物を削除
```

### Dev Container

VS Codeの Dev Containerに対応しています：

```bash
# 必要なツールが全てプリインストール
- Terraform 1.7.5
- Node.js 18
- Python 3.12
- AWS CLI, Azure CLI, gcloud CLI
- Docker in Docker

# 便利なエイリアス
tf              # terraform
deploy-aws      # AWS環境にデプロイ
deploy-azure    # Azure環境にデプロイ  
deploy-gcp      # GCP環境にデプロイ
test-all        # 全エンドポイントテスト
```

### 診断スクリプト

システムの健全性をチェック：

```bash
./scripts/diagnostics.sh
```

- ✅ インストール済みツールの確認
- ✅ クラウドプロバイダー認証状態
- ✅ デプロイメントエンドポイントのテスト
- ✅ Terraformリソース状態の確認

## 🧪 テストとデバッグ

### エンドポイントテスト

```bash
# すべてのクラウドプロバイダーをテスト
./scripts/test-endpoints.sh

# 個別テスト
curl https://52z731x570.execute-api.ap-northeast-1.amazonaws.com/
curl https://mcad-staging-api--0000004.livelycoast-fa9d3350.japaneast.azurecontainerapps.io/
curl https://mcad-staging-api-son5b3ml7a-an.a.run.app/
```

### ローカル開発

```bash
# フロントエンド
cd services/frontend
npm install
npm run dev

# バックエンド（Python）
cd services/backend
pip install -r requirements.txt
uvicorn src.main:app --reload
```

## 🛠️ デプロイツール

### Lambda デプロイスクリプト

Lambda + API Gatewayの完全自動デプロイメント:

```bash
# AWS Lambda デプロイ
cd scripts
./deploy-lambda-aws.sh

# 環境変数でカスタマイズ可能
PROJECT_NAME=myproject ENVIRONMENT=production ./deploy-lambda-aws.sh
```

スクリプトは以下を自動実行します:
- 依存関係のインストール（manylinux2014_x86_64）
- ZIPパッケージ作成とS3アップロード
- Lambda関数の作成/更新
- API Gateway統合設定
- Lambda権限設定（HTTP API用の正しいSourceArn）
- CloudWatch Logsアクセスログ有効化

### API統合テスト

エンドポイントの完全なCRUDテスト:

```bash
# テスト実行
./scripts/test-api.sh -e https://YOUR_API_ID.execute-api.ap-northeast-1.amazonaws.com

# 詳細モード
./scripts/test-api.sh -e https://YOUR_API_ID.execute-api.ap-northeast-1.amazonaws.com --verbose
```

テスト項目:
- ヘルスチェック
- メッセージCRUD操作（作成、取得、更新、削除）
- ページネーション
- エラーハンドリング
- バリデーション

### CloudWatch監視設定

包括的な監視とアラートを自動設定:

```bash
# 監視設定
./scripts/setup-monitoring.sh

# メール通知付き
ALERT_EMAIL=your@email.com ./scripts/setup-monitoring.sh
```

設定内容:
- SNSトピックとメール通知
- Lambda エラー/スロットリング/実行時間/同時実行数アラーム
- API Gateway 5XXエラー/レイテンシアラーム
- DynamoDB スロットリングアラーム
- CloudWatch Logs メトリクスフィルター
- CloudWatch ダッシュボード自動作成

### 推奨: 追加すべきAWSサービス

本番運用のために以下のサービス追加を推奨します:

#### 1. AWS X-Ray（分散トレーシング）

Lambda関数のトレーシング有効化:
```bash
aws lambda update-function-configuration \
  --function-name YOUR_FUNCTION_NAME \
  --tracing-config Mode=Active
```

FastAPIにX-Ray統合:
```python
# requirements.txtに追加
aws-xray-sdk==2.12.0

# main.pyで有効化
from aws_xray_sdk.core import xray_recorder
from aws_xray_sdk.ext.fastapi.middleware import XRayMiddleware

app.add_middleware(XRayMiddleware, recorder=xray_recorder)
```

#### 2. AWS WAF（セキュリティ）

API Gatewayへの攻撃防御:
```bash
# WAF Web ACL作成
aws wafv2 create-web-acl \
  --name multicloud-auto-deploy-waf \
  --scope REGIONAL \
  --default-action Allow={} \
  --rules file://waf-rules.json

# API Gatewayに関連付け
aws wafv2 associate-web-acl \
  --web-acl-arn YOUR_WEB_ACL_ARN \
  --resource-arn YOUR_API_GATEWAY_ARN
```

#### 3. Route 53 + カスタムドメイン

プロダクション用ドメイン設定:
```bash
# ACM証明書作成
aws acm request-certificate \
  --domain-name api.yourdomain.com \
  --validation-method DNS

# API Gatewayカスタムドメイン
aws apigatewayv2 create-domain-name \
  --domain-name api.yourdomain.com \
  --domain-name-configurations CertificateArn=YOUR_CERT_ARN

# Route 53レコード作成
aws route53 change-resource-record-sets \
  --hosted-zone-id YOUR_ZONE_ID \
  --change-batch file://route53-changes.json
```

#### 4. Parameter Store / Secrets Manager

環境変数の安全な管理:
```bash
# Secrets Managerに保存
aws secretsmanager create-secret \
  --name multicloud-auto-deploy/staging/db-config \
  --secret-string '{"host":"dynamodb","region":"ap-northeast-1"}'

# Lambda関数で使用
# requirements.txtに追加: boto3
```

```python
import boto3
import json

def get_secret():
    client = boto3.client('secretsmanager')
    response = client.get_secret_value(SecretId='multicloud-auto-deploy/staging/db-config')
    return json.loads(response['SecretString'])
```

#### 5. Lambda Layers（依存関係最適化）

共通ライブラリの分離でコールドスタート改善:
```bash
# Lambda Layer作成
mkdir python
pip install -r requirements.txt -t python/
zip -r layer.zip python/

aws lambda publish-layer-version \
  --layer-name multicloud-auto-deploy-dependencies \
  --zip-file fileb://layer.zip \
  --compatible-runtimes python3.12

# Lambda関数に紐付け
aws lambda update-function-configuration \
  --function-name YOUR_FUNCTION_NAME \
  --layers YOUR_LAYER_ARN
```

#### 6. CloudFront Functions（エッジ処理）

リクエスト/レスポンスのエッジ処理:
```javascript
// CloudFront Function: セキュリティヘッダ追加
function handler(event) {
    var response = event.response;
    response.headers['strict-transport-security'] = { value: 'max-age=31536000; includeSubdomains' };
    response.headers['x-content-type-options'] = { value: 'nosniff' };
    response.headers['x-frame-options'] = { value: 'DENY' };
    return response;
}
```

#### 7. AWS Backup（データ保護）

DynamoDBの自動バックアップ:
```bash
aws backup create-backup-plan \
  --backup-plan file://backup-plan.json

aws backup create-backup-selection \
  --backup-plan-id YOUR_PLAN_ID \
  --backup-selection file://backup-selection.json
```

### トラブルシューティング

問題が発生した場合は [トラブルシューティングガイド](docs/TROUBLESHOOTING.md) を参照してください：

- Azure認証問題（Service Principal、Terraform Wrapper等）
- GCPリソース競合（State管理、リソースインポート）
- フロントエンドAPI接続問題（ビルド順序、API URL設定）
- 権限エラー（IAM、RBAC設定）

## 🤝 貢献

コントリビューションを歓迎します！詳細は [CONTRIBUTING.md](CONTRIBUTING.md) をご覧ください。

## 📄 ライセンス

MIT License - 詳細は [LICENSE](LICENSE) をご覧ください。

## 🔗 関連リンク

- [GitHub Actions Documentation](https://docs.github.com/en/actions)
- [Terraform Documentation](https://www.terraform.io/docs)
- [Pulumi Documentation](https://www.pulumi.com/docs/)
