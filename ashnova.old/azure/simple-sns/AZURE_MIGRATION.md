# Azure Simple-SNS Migration Guide

> 注意: 本ドキュメントは旧 Azure AD B2C 前提のため古い内容を含みます。最新の構成は README.md を参照してください。

AWS版Simple-SNSからAzure版への移行ガイドです。

## アーキテクチャ比較

| コンポーネント | AWS                  | Azure                          |
| -------------- | -------------------- | ------------------------------ |
| 認証           | Amazon Cognito       | Azure AD B2C                   |
| API            | Lambda + API Gateway | Azure Functions (HTTP Trigger) |
| データベース   | DynamoDB             | Cosmos DB (NoSQL API)          |
| ストレージ     | S3                   | Blob Storage                   |
| CDN            | CloudFront           | Front Door (予定)              |

## フロントエンド変更点

### 1. 認証ライブラリ

**AWS版 (Cognito)**

```typescript
// 手動でOAuth 2.0 PKCE フローを実装
import { login, logout, exchangeCodeForToken } from "./services/auth";
```

**Azure版 (MSAL)**

```typescript
// MSALライブラリが認証フローを自動処理
import { useMsalAuth } from "./hooks/useMsalAuth";

const { login, logout, getAccessToken } = useMsalAuth();
```

### 2. 主な変更ファイル

#### src/App.tsx

- `MsalProvider`でアプリケーション全体をラップ
- `PublicClientApplication`インスタンスを初期化

#### src/hooks/useMsalAuth.ts (新規)

- MSAL認証フックを作成
- login/logout/getAccessToken/getUserIdメソッドを提供

#### src/services/api.ts

- `setMsalTokenGetter()`で依存性注入パターンを実装
- `getToken()`を同期→非同期に変更
- Cognito固有のJWT検証ロジックを削除

#### src/components/Header.tsx

- `useMsalAuth`フックを使用
- タイトルを「Cognito ログイン」→「Azure AD B2C」に変更

#### src/pages/HomePage.tsx

- `setMsalTokenGetter()`と`setMsalUserIdGetter()`を初期化
- Cognitoの手動OAuthコールバック処理を削除（MSALが自動処理）

## バックエンド変更点

### Azure Functions API エンドポイント

#### POST /api/posts

- 投稿を作成
- リクエストボディ: `{ content, images?, tags? }`
- Azure AD B2Cトークンで認証

#### GET /api/posts

- 投稿一覧を取得
- クエリパラメータ: `limit`, `continuationToken`, `tag`
- 画像URLにはSASトークン付与（5分間有効）

#### DELETE /api/posts/{postId}

- 投稿を削除
- 投稿者本人のみ削除可能

#### GET /api/upload-urls

- 画像アップロード用のSAS URLを生成
- クエリパラメータ: `count` (最大5)
- 5分間有効の書き込み専用SASトークン

### Cosmos DB スキーマ

```typescript
interface PostDocument {
  id: string; // nanoid生成
  userId: string; // Azure AD B2C oid/sub
  content: string;
  images?: string[]; // Blob Storage パス
  tags?: string[];
  createdAt: string; // ISO 8601
}
```

パーティションキー: `userId`

## セットアップ手順

### 1. Azure AD B2Cテナントの作成

```bash
# Azure CLIでB2Cテナントを作成
az ad b2c tenant create \
  --tenant-name <tenant-name> \
  --resource-group <resource-group> \
  --location "Japan East"
```

### 2. アプリケーション登録

1. Azure Portal → Azure AD B2C → App registrations → New registration
2. Name: `simple-sns-frontend`
3. Redirect URIs:
   - `http://localhost:5173` (開発環境)
   - `https://sns.azure.ashnova.jp` (本番環境)
4. Client IDをコピー

### 3. サインアップ/サインインポリシーの作成

1. Azure AD B2C → User flows → New user flow
2. Type: Sign up and sign in
3. Name: `B2C_1_signupsignin1`
4. Identity providers: Email signup
5. User attributes: Email Address, Display Name

### 4. 環境変数の設定

`.env.local`を作成:

```env
# Azure AD B2C
VITE_AZURE_AD_B2C_TENANT_NAME=<your-tenant-name>
VITE_AZURE_AD_B2C_CLIENT_ID=<your-client-id>
VITE_AZURE_AD_B2C_POLICY_NAME=B2C_1_signupsignin1

# API
VITE_API_URL=https://<function-app-name>.azurewebsites.net/api
VITE_API_SCOPE=https://<tenant-name>.onmicrosoft.com/<client-id>/access_as_user
```

### 5. Terraformでインフラをデプロイ

```bash
cd terraform

# 初期化
tofu init

# プランの確認
tofu plan

# デプロイ
tofu apply
```

### 6. Azure Functionsのデプロイ

```bash
cd functions

# 依存パッケージのインストール
npm install

# ビルド
npm run build

# Azure Functionsにデプロイ
func azure functionapp publish <function-app-name>
```

### 7. フロントエンドのビルド&デプロイ

```bash
cd frontend

# 依存パッケージのインストール
npm install

# ビルド
npm run build

# Azure Blob Storageにデプロイ
./deploy.sh
```

## トラブルシューティング

### CORS エラー

Azure Functionsの`host.json`で許可するオリジンを設定:

```json
{
  "extensions": {
    "http": {
      "routePrefix": "api",
      "cors": {
        "allowedOrigins": [
          "https://sns.azure.ashnova.jp",
          "http://localhost:5173"
        ],
        "supportCredentials": true
      }
    }
  }
}
```

### 認証トークンが取得できない

- Azure AD B2CのリダイレクトURIが正しく設定されているか確認
- `authConfig.ts`のtenant名、client ID、policy名を確認
- ブラウザのコンソールでMSALエラーログを確認

### Cosmos DB接続エラー

- `COSMOS_DB_ENDPOINT`と`COSMOS_DB_KEY`環境変数が設定されているか確認
- Terraformで作成したCosmos DBアカウントのキーを使用
- ネットワークアクセスルール（ファイアウォール）を確認

## パフォーマンス最適化

### Cosmos DB

- サーバーレスモード使用（小規模アプリ向け）
- パーティションキーを`userId`に設定（ユーザー単位でスケール）

### Blob Storage

- SASトークンの有効期限を5分に設定（セキュリティ強化）
- 静的Webサイトホスティング機能を使用

### Azure Functions

- Consumption Planを使用（使用量課金）
- Node.js 20 LTS使用

## セキュリティ考慮事項

1. **認証**: Azure AD B2Cで多要素認証を有効化可能
2. **トークン**: MSALがトークンの自動更新とキャッシングを処理
3. **CORS**: 必要なオリジンのみ許可
4. **画像アップロード**: SASトークンで時間制限付きアクセス
5. **投稿削除**: 投稿者本人のみ削除可能（ownershipチェック）

## 今後の改善案

- [ ] Azure Front Doorの導入（CDN + WAF）
- [ ] Application Insightsでログ・監視
- [ ] Key Vaultでシークレット管理
- [ ] CI/CDパイプライン（GitHub Actions）
- [ ] ロールベースアクセス制御（管理者機能）
