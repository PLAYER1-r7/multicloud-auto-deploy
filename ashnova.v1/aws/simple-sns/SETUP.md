# Simple-SNS AWS デプロイメント

## 概要

Simple-SNSは、AWS上で動作するサーバーレスソーシャルネットワーキングサービスです。

## アーキテクチャ

- **Lambda**: Node.js 22.x で実装されたバックエンドAPI
- **API Gateway**: RESTful APIエンドポイント
- **DynamoDB**: 投稿データの保存
- **Cognito**: ユーザー認証とMFA
- **S3**: フロントエンドホスティングと画像保存
- **CloudFront**: CDN配信
- **WAF**: API保護とレート制限

## セットアップ手順

### 1. 前提条件

- Node.js >= 18.x
- OpenTofu >= 1.0
- AWS CLI設定済み
- AWS IAMポリシーが適用済み（`../iam-policy-simple-sns.json`）

### 2. 依存関係のインストール

```bash
npm install
```

### 3. Terraform初期化

```bash
npm run terraform:init
```

### 4. 環境変数の設定

`.env.example`をコピーして`.env.local`を作成：

```bash
cp .env.example .env.local
```

必要な値を設定：

- `VITE_API_URL`: API GatewayのURL（デプロイ後に取得）
- `VITE_USER_POOL_ID`: Cognito User Pool ID
- `VITE_COGNITO_CLIENT_ID`: Cognito Client ID
- `VITE_COGNITO_DOMAIN`: Cognito Domain
- `VITE_REDIRECT_URI`: リダイレクトURI

### 5. Lambda関数のビルド

```bash
npm run build
```

### 6. インフラストラクチャのデプロイ

```bash
npm run terraform:apply
```

デプロイ完了後、以下の出力値が表示されます：

- `api_url`: API GatewayのURL
- `cognito_user_pool_id`: Cognito User Pool ID
- `cognito_client_id`: Cognito Client ID
- `cognito_domain`: Cognito認証ドメイン
- `cloudfront_domain_name`: CloudFrontのドメイン名

### 7. フロントエンドのビルドとデプロイ

`.env.local`に出力値を設定後：

```bash
npm run build:frontend
npm run deploy
```

## ディレクトリ構造

```
aws/simple-sns/
├── terraform/          # Terraformファイル
│   ├── main.tf        # プロバイダーと変数設定
│   ├── lambda.tf      # Lambda関数定義
│   ├── api-gateway.tf # API Gateway設定
│   ├── dynamodb.tf    # DynamoDB設定
│   ├── cognito.tf     # Cognito設定
│   ├── s3.tf          # S3バケット設定
│   ├── frontend-s3.tf # CloudFront設定
│   ├── waf.tf         # WAF設定
│   └── outputs.tf     # 出力値定義
├── src/               # Lambda関数ソースコード
│   ├── createPost.ts
│   ├── listPosts.ts
│   ├── deletePost.ts
│   ├── getUploadUrls.ts
│   ├── common.ts
│   ├── types.ts
│   ├── middleware/
│   └── utils/
├── frontend/          # Reactフロントエンド
│   ├── src/
│   ├── public/
│   └── index.html
└── package.json       # 依存関係とスクリプト
```

## 主要なコマンド

```bash
# 開発サーバー起動
npm run dev

# Lambda関数ビルド
npm run build

# フロントエンドビルド
npm run build:frontend

# インフラ確認
npm run terraform:plan

# インフラデプロイ
npm run terraform:apply

# インフラ削除
npm run terraform:destroy

# フロントエンドデプロイ
npm run deploy
```

## セキュリティ

- すべてのAPI呼び出しはCognito認証が必要
- MFA (TOTP) が有効
- WAFによるレート制限とボット対策
- S3バケットはプライベート
- CloudFrontはHTTPSのみ
- DynamoDBの暗号化有効
- ポイントインタイムリカバリ有効

## トラブルシューティング

### デプロイエラー

IAM権限不足の場合、管理者に以下のポリシーを適用してもらってください：

```bash
aws iam put-user-policy --user-name <your-username> --policy-name SimpleSNSPolicy --policy-document file://../iam-policy-simple-sns.json
```

### 削除保護エラー

リソース削除時、以下のコマンドで削除保護を無効化：

```bash
# DynamoDB
aws dynamodb update-table --table-name simple-sns-Posts --no-deletion-protection-enabled --profile satoshi

# Cognito
aws cognito-idp update-user-pool --user-pool-id <pool-id> --deletion-protection INACTIVE --profile satoshi
```

## ライセンス

Private
