# Simple-SNS for Azure

AWS版Simple-SNSのAzure移植版。

## アーキテクチャ

- **Azure Functions**: サーバーレスAPI（Node.js 20）
- **Azure Cosmos DB**: NoSQL データベース（投稿データ）
- **Azure AD**: 認証・認可 (MSAL)
- **Azure Blob Storage**: 画像保存、フロントエンド静的ホスティング
- **Azure Front Door**: CDN、HTTPSエンドポイント

## AWS vs Azure マッピング

| AWS Service | Azure Service          |
| ----------- | ---------------------- |
| Lambda      | Azure Functions        |
| API Gateway | Functions HTTP Trigger |
| DynamoDB    | Cosmos DB (NoSQL API)  |
| Cognito     | Azure AD               |
| S3          | Blob Storage           |
| CloudFront  | Front Door             |

## デプロイ手順

```bash
cd azure/simple-sns

# 依存関係インストール
npm install

# Azureにログイン
az login

# OpenTofuでインフラ構築
cd terraform
tofu init
tofu plan
tofu apply

# フロントエンドビルド
cd ..
npm run build:frontend

# 静的サイトデプロイ
./deploy.sh

# Functions デプロイ（functions/ 配下を使用）
# 例: zip deploy など
```

## 環境変数

以下の環境変数が必要です（`.env.local`に設定）:

```
VITE_API_BASE_URL=https://your-function-app.azurewebsites.net/api
VITE_AZURE_AD_TENANT_ID=your-tenant-id
VITE_AZURE_AD_CLIENT_ID=your-client-id
VITE_REDIRECT_URI=https://sns.azure.ashnova.jp/
```
