# Multi-Cloud Auto Deploy Platform

**マルチクラウド対応の自動デプロイシステム** - AWS/Azure/GCP対応のフルスタックアプリケーション自動デプロイプラットフォーム

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

- Node.js 18+ / Python 3.9+
- Docker & Docker Compose
- Terraform 1.5+ または Pulumi 3.0+
- AWS CLI / Azure CLI / gcloud CLI
- GitHub アカウント

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

- [セットアップガイド](docs/SETUP.md)
- [AWS デプロイ](docs/AWS_DEPLOYMENT.md)
- [Azure デプロイ](docs/AZURE_DEPLOYMENT.md)
- [GCP デプロイ](docs/GCP_DEPLOYMENT.md)
- [アーキテクチャ](docs/ARCHITECTURE.md)

## 🔄 GitHub Actions 自動デプロイ

プッシュやPRで自動的にビルド・デプロイが実行されます：

- `main`ブランチへのプッシュ → 本番環境へデプロイ
- PRの作成/更新 → ステージング環境へデプロイ
- タグのプッシュ → リリースとデプロイ

## 🏗️ サポートされるアーキテクチャ

### AWS
- Frontend: S3 + CloudFront
- Backend: Lambda + API Gateway
- Database: DynamoDB / RDS
- Auth: Cognito

### Azure
- Frontend: Static Web Apps / Storage Account
- Backend: Azure Functions
- Database: Cosmos DB / Azure SQL
- Auth: Azure AD B2C

### GCP
- Frontend: Cloud Storage + Cloud CDN
- Backend: Cloud Functions / Cloud Run
- Database: Firestore / Cloud SQL
- Auth: Firebase Auth

## 🤝 貢献

コントリビューションを歓迎します！詳細は [CONTRIBUTING.md](CONTRIBUTING.md) をご覧ください。

## 📄 ライセンス

MIT License - 詳細は [LICENSE](LICENSE) をご覧ください。

## 🔗 関連リンク

- [GitHub Actions Documentation](https://docs.github.com/en/actions)
- [Terraform Documentation](https://www.terraform.io/docs)
- [Pulumi Documentation](https://www.pulumi.com/docs/)
