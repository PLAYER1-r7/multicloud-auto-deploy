# Azure Simple-SNS - ローカル開発ガイド

Azureサブスクリプションのクォータ制限により、Azure Functionsをデプロイできない場合のローカル開発手順です。

## 前提条件

```bash
# Azure Functions Core Tools
brew install azure-functions-core-tools@4

# Azurite (ローカルストレージエミュレーター)
npm install -g azurite

# Cosmos DB Emulator (Linuxのみ / Dockerコンテナ使用)
docker pull mcr.microsoft.com/cosmosdb/linux/azure-cosmos-emulator
```

## 1. Cosmos DB Emulatorの起動

```bash
# macOSの場合、Dockerコンテナで実行
docker run -d \
  --name cosmos-emulator \
  -p 8081:8081 \
  -p 10250-10255:10250-10255 \
  -e AZURE_COSMOS_EMULATOR_PARTITION_COUNT=10 \
  -e AZURE_COSMOS_EMULATOR_ENABLE_DATA_PERSISTENCE=true \
  mcr.microsoft.com/cosmosdb/linux/azure-cosmos-emulator

# Emulator接続文字列
# AccountEndpoint=https://localhost:8081/;AccountKey=C2y6yDjf5/R+ob0N8A7Cgv30VRDJIWEHLM+4QDU5DE2nQ9nDuVTqobD4b8mGGyPMbIZnqyMsEcaGQy67XIw/Jw==
```

## 2. Azuriteの起動 (ローカルストレージ)

```bash
# 別ターミナルで起動
azurite --silent --location /tmp/azurite --debug /tmp/azurite/debug.log
```

## 3. Functions環境変数の設定

`functions/local.settings.json` を作成:

```json
{
  "IsEncrypted": false,
  "Values": {
    "AzureWebJobsStorage": "UseDevelopmentStorage=true",
    "FUNCTIONS_WORKER_RUNTIME": "node",
    "COSMOS_DB_ENDPOINT": "https://localhost:8081",
    "COSMOS_DB_KEY": "C2y6yDjf5/R+ob0N8A7Cgv30VRDJIWEHLM+4QDU5DE2nQ9nDuVTqobD4b8mGGyPMbIZnqyMsEcaGQy67XIw/Jw==",
    "COSMOS_DB_DATABASE": "simple-sns-db",
    "COSMOS_DB_CONTAINER": "posts",
    "STORAGE_ACCOUNT_NAME": "devstoreaccount1",
    "STORAGE_ACCOUNT_KEY": "Eby8vdM02xNOcqFlqUwJPLlmEtlCDXJ1OUzFT50uSRZ6IFsuFq2UVErCz4I6tq/K1SZFPTOtr/KBHBeksoGMGw==",
    "STORAGE_IMAGES_CONTAINER": "post-images",
    "AZURE_AD_TENANT_ID": "local-dev",
    "AZURE_AD_CLIENT_ID": "local-client-id",
    "CORS_ORIGINS": "http://localhost:5173"
  },
  "Host": {
    "LocalHttpPort": 7071,
    "CORS": "http://localhost:5173",
    "CORSCredentials": true
  }
}
```

## 4. Cosmos DBの初期化

```bash
# Azure Data Studioまたはブラウザで https://localhost:8081/_explorer/index.html にアクセス
# 1. データベース "simple-sns-db" を作成
# 2. コンテナ "posts" を作成 (パーティションキー: /postId)
```

または、Azure CLIで:

```bash
# ローカルCosmos DBに接続（証明書エラーを無視）
az cosmosdb sql database create \
  --account-name localhost \
  --name simple-sns-db \
  --url https://localhost:8081 \
  --key C2y6yDjf5/R+ob0N8A7Cgv30VRDJIWEHLM+4QDU5DE2nQ9nDuVTqobD4b8mGGyPMbIZnqyMsEcaGQy67XIw/Jw==

az cosmosdb sql container create \
  --account-name localhost \
  --database-name simple-sns-db \
  --name posts \
  --partition-key-path /postId \
  --url https://localhost:8081 \
  --key C2y6yDjf5/R+ob0N8A7Cgv30VRDJIWEHLM+4QDU5DE2nQ9nDuVTqobD4b8mGGyPMbIZnqyMsEcaGQy67XIw/Jw==
```

## 5. Azure Functionsをローカルで起動

```bash
cd functions
npm install
npm run build
func start --verbose
```

Functions が `http://localhost:7071/api/` で起動します。

## 6. フロントエンドの起動

`.env.local` を編集:

```env
VITE_API_BASE_URL=http://localhost:7071/api
VITE_AZURE_AD_TENANT_ID=local-dev
VITE_AZURE_AD_CLIENT_ID=local-client-id
VITE_REDIRECT_URI=http://localhost:5173/
VITE_LOGOUT_URI=http://localhost:5173/
```

```bash
npm install --legacy-peer-deps
npm run dev
```

ブラウザで `http://localhost:5173` を開きます。

## 7. 認証のモック（開発用）

Azure AD をローカルでエミュレートすることはできないため、以下の選択肢があります:

### オプション1: 認証を一時的に無効化

`functions/src/common.ts` で認証チェックをスキップ:

```typescript
export const extractUserInfo = (request: HttpRequest): UserInfo => {
  // ローカル開発用: 認証をバイパス
  if (process.env.NODE_ENV === "development") {
    return {
      userId: "local-test-user",
      email: "test@example.com",
    };
  }

  // 本番環境の認証ロジック...
};
```

### オプション2: Azure AD テナントを使用

実際のAzure ADテナントで、localhostをリダイレクトURIに追加。

## API エンドポイント (ローカル)

- POST `http://localhost:7071/api/posts` - 投稿作成
- GET `http://localhost:7071/api/listposts` - 投稿一覧
- DELETE `http://localhost:7071/api/posts/{postId}` - 投稿削除
- GET `http://localhost:7071/api/upload-urls?count=3` - アップロードURL取得

## トラブルシューティング

### Cosmos DB接続エラー

```bash
# 証明書エラーの場合、Node.jsの証明書検証を無効化（開発環境のみ）
export NODE_TLS_REJECT_UNAUTHORIZED=0
func start
```

### CORS エラー

`functions/local.settings.json` の `CORS` 設定を確認。

### ストレージ接続エラー

Azuriteが起動しているか確認:

```bash
ps aux | grep azurite
```

## クリーンアップ

```bash
# コンテナ停止
docker stop cosmos-emulator
azurite stop

# データ削除
docker rm cosmos-emulator
rm -rf /tmp/azurite
```

## 次のステップ

### Azure デプロイ準備

1. **クォータ引き上げリクエスト**: Azure Portal > サポート > クォータ
2. **別のサブスクリプション**: 従量課金アカウントを作成
3. **別のリージョン**: `variables.tf` で `azure_location` を変更

### 代替デプロイ方法

- **Azure Container Apps**: Functionsの代わりにコンテナベースAPI
- **Azure Static Web Apps**: 組み込みAPIサポート（制限あり）
- **Azure API Management**: 既存APIの前段プロキシ
