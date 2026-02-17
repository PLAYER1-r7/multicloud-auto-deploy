# Simple SNS

シンプルなSNS（ソーシャルネットワーキングサービス）アプリケーション

## 技術スタック

### インフラ

- **IaC**: OpenTofu (Terraform互換)
- **クラウド**: AWS
  - API Gateway (REST API)
  - Lambda (Node.js 22.x)
  - DynamoDB (投稿データ)
  - S3 (画像保存、フロントエンド配信)
  - Cognito (認証)
  - CloudFront (CDN)
  - WAF (セキュリティ)

### バックエンド

- **ランタイム**: Node.js 22.x
- **言語**: TypeScript
- **主要ライブラリ**:
  - AWS SDK v3
  - Middy (Lambda middleware)
  - Winston (ログ)
  - Zod (バリデーション)

### フロントエンド

- **フレームワーク**: React 19
- **ビルドツール**: Vite 7
- **言語**: TypeScript
- **主要ライブラリ**:
  - React Query (データフェッチ)
  - React Markdown (Markdown表示)
  - Mermaid (ダイアグラム)
  - KaTeX (数式)

## プロジェクト構造

```
simple-sns/
├── src/                      # Lambda関数ソースコード (TypeScript)
│   ├── createPost.ts         # 投稿作成
│   ├── listPosts.ts          # 投稿一覧取得
│   ├── deletePost.ts         # 投稿削除
│   ├── common.ts             # 共通ロジック
│   ├── middleware/           # Lambda middleware
│   └── utils/                # ユーティリティ
├── frontend/                 # Reactフロントエンド
│   ├── src/
│   └── public/
├── dist/                     # Lambda関数ビルド出力 (生成)
├── dist-frontend/            # フロントエンドビルド出力 (生成)
├── *.tf                      # OpenTofu設定ファイル
│   ├── main.tf               # プロバイダー設定
│   ├── api-gateway.tf        # API Gateway
│   ├── lambda.tf             # Lambda関数
│   ├── dynamodb.tf           # DynamoDB
│   ├── cognito.tf            # Cognito認証
│   ├── s3.tf                 # S3バケット (画像)
│   ├── frontend-s3.tf        # S3バケット (フロントエンド)
│   ├── waf.tf                # WAF
│   └── outputs.tf            # 出力値
└── deploy-frontend.sh        # フロントエンドデプロイスクリプト
```

## セットアップ

### 前提条件

- Node.js 22.x以上
- OpenTofu または Terraform
- AWS CLI
- AWS認証情報の設定

### 1. 依存関係のインストール

```bash
npm install
```

### 2. インフラのデプロイ

```bash
# OpenTofuの初期化
tofu init

# インフラのデプロイ
tofu apply
```

デプロイ後、以下の情報が出力されます：

- `api_url`: API Gateway エンドポイント
- `cognito_user_pool_id`: Cognito ユーザープールID
- `cognito_client_id`: Cognito クライアントID
- `frontend_bucket_name`: フロントエンド用S3バケット名

### 3. フロントエンドの設定

出力された値を使って、フロントエンドの設定を更新します：

```typescript
// frontend/src/config/constants.ts
export const API_CONFIG = {
  BASE_URL: "<api_url>",
};

export const COGNITO_CONFIG = {
  USER_POOL_ID: "<cognito_user_pool_id>",
  CLIENT_ID: "<cognito_client_id>",
  REGION: "ap-northeast-1",
};
```

### 4. フロントエンドのデプロイ

```bash
npm run deploy
```

または手動で：

```bash
# ビルド
npm run build:frontend

# S3にアップロード
aws s3 sync dist-frontend/ s3://<frontend_bucket_name>/ --delete

# CloudFrontキャッシュ無効化
aws cloudfront create-invalidation --distribution-id <distribution_id> --paths "/*"
```

## 開発

### Lambda関数の開発

```bash
# TypeScriptのコンパイル
npm run build

# OpenTofuで Lambda関数を更新
tofu apply
```

### フロントエンドの開発

```bash
# 開発サーバー起動
npm run dev

# プレビュー
npm run preview
```

## API エンドポイント

### 認証不要

- `GET /posts?limit=20&lastKey=...` - 投稿一覧取得

### 認証必要 (Cognitoトークン必須)

- `POST /posts` - 投稿作成
- `DELETE /posts/{postId}` - 投稿削除

## インフラの削除

```bash
# DynamoDBとCognitoの削除保護を無効化
aws dynamodb update-table --table-name simple-sns-Posts --no-deletion-protection-enabled
aws cognito-idp update-user-pool --user-pool-id <user_pool_id> --deletion-protection INACTIVE

# S3バケットを空にする
aws s3 rm s3://<frontend_bucket_name>/ --recursive
aws s3 rm s3://<images_bucket_name>/ --recursive

# インフラを削除
tofu destroy
```

## ライセンス

Private
