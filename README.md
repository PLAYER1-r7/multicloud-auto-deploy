# Multi-Cloud Auto Deploy Platform

[![Deploy to AWS](https://github.com/PLAYER1-r7/multicloud-auto-deploy/actions/workflows/deploy-aws.yml/badge.svg)](https://github.com/PLAYER1-r7/multicloud-auto-deploy/actions/workflows/deploy-aws.yml)
[![Deploy to Azure](https://github.com/PLAYER1-r7/multicloud-auto-deploy/actions/workflows/deploy-azure.yml/badge.svg)](https://github.com/PLAYER1-r7/multicloud-auto-deploy/actions/workflows/deploy-azure.yml)
[![Deploy to GCP](https://github.com/PLAYER1-r7/multicloud-auto-deploy/actions/workflows/deploy-gcp.yml/badge.svg)](https://github.com/PLAYER1-r7/multicloud-auto-deploy/actions/workflows/deploy-gcp.yml)

**マルチクラウド対応の自動デプロイシステム** - AWS/Azure/GCP対応のフルスタックアプリケーション自動デプロイプラットフォーム

## 🌐 Live Demos

| Cloud Provider | API Endpoint | Frontend |
|---------------|--------------|----------|
| **AWS** (ap-northeast-1) | [API](https://52z731x570.execute-api.ap-northeast-1.amazonaws.com/) | [CloudFront](https://dx3l4mbwg1ade.cloudfront.net) |
| **Azure** (japaneast) | [API](https://mcad-staging-api--0000003.livelycoast-fa9d3350.japaneast.azurecontainerapps.io/) | Coming Soon |
| **GCP** (asia-northeast1) | [API](https://mcad-staging-api-son5b3ml7a-an.a.run.app/) | Coming Soon |

## 🚀 特徴

- **マルチクラウド対応**: AWS、Azure、GCPに対応
- **フルスタック**: フロントエンド、バックエンド、データベースの完全なスタック
- **自動デプロイ**: GitHub Actionsによる完全自動化
- **IaC統合**: TerraformとPulumiの両方に対応
- **CI/CD**: プッシュやPRで自動的にビルド・デプロイ
- **簡単セットアップ**: スクリプト一つで環境構築

## 📁 プロジェクト構造

```
multicloud-auto-deploy/
├── .github/workflows/     # GitHub Actionsワークフロー
├── infrastructure/        # インフラストラクチャコード
│   ├── terraform/        # Terraformコード（AWS/Azure/GCP）
│   └── pulumi/           # Pulumiコード（AWS/Azure/GCP）
├── services/             # アプリケーションコード
│   ├── frontend/         # Reactフロントエンド
│   ├── backend/          # Node.js/Python バックエンドAPI
│   └── database/         # データベーススキーマ
├── scripts/              # デプロイスクリプト
└── docs/                 # ドキュメント
```

## 🛠️ セットアップ

### 前提条件

- Node.js 18+ / Python 3.11+ or 3.12+
- Docker & Docker Compose
- Terraform 1.5+ または Pulumi 3.0+
- AWS CLI 2.x / Azure CLI 2.x / gcloud CLI 556.0+
- GitHub アカウント

### 技術スタック

**Frontend**
- React 18
- TypeScript 5
- Vite 5
- TailwindCSS 3

**Backend**
- Python 3.12
- FastAPI 0.109
- Pydantic 2.5
- Mangum (AWS Lambda adapter)

**Infrastructure**
- Terraform 1.14.5
- AWS Lambda (x86_64)
- API Gateway v2 (HTTP)
- S3 + CloudFront
- DynamoDB

**CI/CD**
- GitHub Actions
- Automated builds and deployments
- S3-based Lambda deployment

### クイックスタート

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

### セットアップ・デプロイ
- [セットアップガイド](docs/SETUP.md)
- [AWS デプロイ](docs/AWS_DEPLOYMENT.md)
- [Azure デプロイ](docs/AZURE_DEPLOYMENT.md)
- [GCP デプロイ](docs/GCP_DEPLOYMENT.md)

### アーキテクチャ・運用
- [アーキテクチャ](docs/ARCHITECTURE.md) - 完全版システムアーキテクチャ
- [CI/CD設定](docs/CICD_SETUP.md) - GitHub Actions自動デプロイ設定

## 🔄 GitHub Actions 自動デプロイ

プッシュやPRで自動的にビルド・デプロイが実行されます：

- `main`ブランチへのプッシュ → ステージング環境へ自動デプロイ
- PRの作成/更新 → ビルド検証
- 手動トリガー → 任意の環境へデプロイ

### デプロイフロー

1. **Build Frontend**: React アプリケーションをビルド
2. **Package Backend**: Lambda パッケージを作成（x86_64、~4.3MB）
3. **Update Lambda**: S3経由でLambda関数を更新
4. **Deploy Frontend**: S3にフロントエンドをアップロード
5. **Invalidate Cache**: CloudFront キャッシュを無効化

### 必要なGitHub Secrets

以下のシークレットを設定してください（詳細は [CI/CD設定ガイド](docs/CICD_SETUP.md) 参照）：

**AWS**
- `AWS_ACCESS_KEY_ID`
- `AWS_SECRET_ACCESS_KEY`

**Azure**
- `AZURE_CREDENTIALS`
- `AZURE_ACR_LOGIN_SERVER`

**GCP**
- `GCP_CREDENTIALS`

### デプロイ状況

最新のデプロイ状況は[GitHub Actions](https://github.com/PLAYER1-r7/multicloud-auto-deploy/actions)で確認できます。

## 🏗️ サポートされるアーキテクチャ

### AWS (ap-northeast-1) ✅ 運用中
- **Frontend**: S3 (Static Hosting) + CloudFront (CDN)
- **Backend**: Lambda (Python 3.12, x86_64) + API Gateway v2 (HTTP)
- **Database**: DynamoDB
- **Auth**: Cognito (予定)
- **Infrastructure**: Terraform 1.14.5
- **Deployment**: GitHub Actions (S3-based Lambda deployment)

### Azure (japaneast) ✅ 運用中
- **Frontend**: Static Web Apps / Storage Account
- **Backend**: Container Apps
- **Database**: Cosmos DB / Azure SQL
- **Auth**: Azure AD B2C (予定)
- **Infrastructure**: Pulumi
- **Deployment**: GitHub Actions (Azure Container Registry)

### GCP (asia-northeast1) ✅ 運用中
- **Frontend**: Cloud Storage + Cloud CDN
- **Backend**: Cloud Run
- **Database**: Firestore / Cloud SQL
- **Auth**: Firebase Auth (予定)
- **Infrastructure**: Pulumi
- **Deployment**: GitHub Actions (Artifact Registry)

## 🛠️ 開発ツール

プロジェクトには便利な開発ツールが含まれています：

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

### 診断スクリプト

```bash
./scripts/diagnostics.sh
```

システムの健全性をチェック：
- インストール済みツールの確認（aws, az, gcloud, terraform, gh, node, python, docker, jq）
- クラウドプロバイダー認証状態
- デプロイメントエンドポイントのテスト
- Terraformリソース状態（14リソース）
- AWSリソースの確認

## 🤝 貢献

コントリビューションを歓迎します！詳細は [CONTRIBUTING.md](CONTRIBUTING.md) をご覧ください。

## 📄 ライセンス

MIT License - 詳細は [LICENSE](LICENSE) をご覧ください。

## 🔗 関連リンク

- [GitHub Actions Documentation](https://docs.github.com/en/actions)
- [Terraform Documentation](https://www.terraform.io/docs)
- [Pulumi Documentation](https://www.pulumi.com/docs/)
