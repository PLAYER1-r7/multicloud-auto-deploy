# Azure Functions Simple-SNS デプロイガイド

## 前提条件

- Node.js 20以上
- Azure CLI
- Azure Functions Core Tools v4

## セットアップ手順

### 1. 依存関係のインストール

```bash
cd functions
npm install
```

### 2. ローカル開発

```bash
# ビルド
npm run build

# ローカルで起動
npm start
```

### 3. Azureへのデプロイ

```bash
# Azure CLIでログイン
az login

# Terraformでインフラ構築
cd ../terraform
tofu init
tofu apply

# Function Appの名前を取得
FUNCTION_APP_NAME=$(tofu output -raw function_app_name)

# Functionsをデプロイ（例: zip deploy）
cd ../functions
npm run build
zip -r functionapp.zip . -x "node_modules/*" -x ".git/*" -x ".vscode/*"
az functionapp deployment source config-zip -g <resource-group> -n $FUNCTION_APP_NAME --src functionapp.zip
```

## API エンドポイント

- `POST /api/posts` - 投稿作成
- `GET /api/listposts` - 投稿一覧取得
- `DELETE /api/posts/{postId}` - 投稿削除
- `GET /api/upload-urls?count=1` - 画像アップロードURL取得

## 環境変数

以下の環境変数がFunction Appに設定されます（Terraformで自動設定）:

- `COSMOS_DB_ENDPOINT`
- `COSMOS_DB_KEY`
- `COSMOS_DB_DATABASE`
- `COSMOS_DB_CONTAINER`
- `STORAGE_ACCOUNT_NAME`
- `STORAGE_ACCOUNT_KEY`
- `STORAGE_IMAGES_CONTAINER`
- `AZURE_AD_TENANT_ID`
- `AZURE_AD_CLIENT_ID`
