# Ashnova AWS Deployments

このディレクトリには、AWS上にデプロイされる複数のプロジェクトが含まれています。

## 📂 プロジェクト一覧

### 1. 静的ウェブサイト (terraform/)

OpenTofuを使用してAWS上に静的ウェブサイトをデプロイします。

- **CloudFront + S3**: グローバルCDN配信
- **カスタムドメイン**: www.aws.ashnova.jp
- **SSL/TLS**: ACM証明書による暗号化

詳細は [terraform/README.md](terraform/README.md) を参照してください。

### 2. Simple-SNS (simple-sns/)

サーバーレスソーシャルネットワーキングサービス。

- **Lambda + API Gateway**: Node.js 22.x バックエンド
- **DynamoDB**: データストレージ
- **Cognito**: 認証とMFA
- **React**: フロントエンド
- **CloudFront + S3**: フロントエンド配信

詳細は [simple-sns/SETUP.md](simple-sns/SETUP.md) を参照してください。

## 🚀 クイックスタート

### 静的ウェブサイトのデプロイ

```bash
cd terraform
tofu init
tofu apply
```

### Simple-SNSのデプロイ

```bash
cd simple-sns
./quickstart.sh
```

## 📋 前提条件

- OpenTofu がインストールされていること
- AWS CLI が設定されていること（プロファイル: `satoshi`）
- 適切なAWS権限（S3、CloudFront、IAMの作成権限）

## 🚀 デプロイ手順

### 1. OpenTofuの初期化

```bash
cd aws/terraform
tofu init
```

### 2. 設定の確認

`variables.tf`で設定を確認・変更できます：

- `aws_region`: AWSリージョン（デフォルト: ap-northeast-1）
- `aws_profile`: AWS CLIプロファイル（デフォルト: satoshi）
- `project_name`: プロジェクト名
- `enable_cloudfront`: CloudFrontの有効/無効

### 3. 実行プランの確認

```bash
tofu plan
```

### 4. リソースのデプロイ

```bash
tofu apply
```

### 5. ウェブサイトファイルのアップロード

デプロイ完了後、出力されるS3バケット名を使用してファイルをアップロードします：

```bash
# S3バケット名を取得
BUCKET_NAME=$(tofu output -raw s3_bucket_name)

# ウェブサイトファイルをアップロード
aws s3 sync ../website/ s3://$BUCKET_NAME/ --profile satoshi

# CloudFrontのキャッシュをクリア（CloudFrontを使用している場合）
DISTRIBUTION_ID=$(tofu output -raw cloudfront_distribution_id)
aws cloudfront create-invalidation \
  --distribution-id $DISTRIBUTION_ID \
  --paths "/*" \
  --profile satoshi
```

### 6. ウェブサイトにアクセス

```bash
# ウェブサイトのURLを取得
tofu output website_url
```

出力されたURLにアクセスしてウェブサイトを確認できます。

## 📁 ディレクトリ構造

```
aws/
├── terraform/          # OpenTofu設定ファイル
│   ├── provider.tf    # プロバイダー設定
│   ├── variables.tf   # 変数定義
│   ├── main.tf        # メインリソース定義
│   └── outputs.tf     # 出力値
└── website/           # 静的ウェブサイトファイル
    ├── index.html     # トップページ
    └── error.html     # エラーページ
```

## 🔧 リソース構成

- **S3 Bucket**: 静的ウェブサイトホスティング
- **CloudFront**: グローバルCDN（オプション）
- **Origin Access Control**: S3への安全なアクセス制御

## 💰 コスト削減のヒント

- CloudFrontを無効にする場合: `enable_cloudfront = false`
- 不要な時はリソースを削除: `tofu destroy`

## 🗑️ リソースの削除

```bash
cd aws/terraform
tofu destroy
```

## 📝 カスタマイズ

### ドメインの設定

カスタムドメインを使用する場合は、`variables.tf`の`domain_name`を設定し、Route 53の設定を追加します。

### キャッシュ設定の変更

`main.tf`のCloudFront設定でTTL値を調整できます。

## 🔒 セキュリティ

- S3バケットへの直接アクセスは制限されています
- CloudFront経由のみアクセス可能（OAC使用）
- HTTPSを強制（redirect-to-https）
