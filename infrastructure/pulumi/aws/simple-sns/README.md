# AWS Simple SNS - Pulumi Infrastructure

PulumiによるAWSインフラストラクチャ管理（完全Python実装）

## 📦 リソース

- **API Gateway (HTTP API)** - RESTful API エンドポイント
- **Lambda Function** - Python 3.13 FastAPI アプリケーション
- **DynamoDB Table** - メッセージストレージ（オンデマンド）
- **S3 Bucket** - 画像ストレージ（パブリック読み取り）
- **IAM Roles & Policies** - 最小権限

## 🚀 デプロイ

### 前提条件

```bash
# AWS CLI設定
aws configure

# Pulumiのインストール
curl -fsSL https://get.pulumi.com | sh

# Python依存関係
pip install -r requirements.txt
```

### 初回デプロイ

```bash
# Pulumiスタック作成
pulumi stack init staging

# 設定
pulumi config set aws:region ap-northeast-1
pulumi config set environment staging

# プレビュー
pulumi preview

# デプロイ
pulumi up
```

### 更新

```bash
# コード変更後
pulumi up
```

### 削除

```bash
pulumi destroy
```

## 📋 設定

| Key            | Description    | Default          |
| -------------- | -------------- | ---------------- |
| `aws:region`   | AWSリージョン  | `ap-northeast-1` |
| `environment`  | 環境名         | `staging`        |
| `project_name` | プロジェクト名 | `simple-sns`     |

設定方法：

```bash
pulumi config set aws:region ap-northeast-1
pulumi config set environment production
```

## 📤 Outputs

デプロイ後、以下の情報が出力されます：

```bash
# API URL取得
pulumi stack output api_url

# 全outputs表示
pulumi stack output
```

| Output                 | Description                |
| ---------------------- | -------------------------- |
| `api_url`              | API Gateway エンドポイント |
| `messages_table_name`  | DynamoDB テーブル名        |
| `images_bucket_name`   | S3 バケット名              |
| `lambda_function_name` | Lambda 関数名              |

## 🧪 テスト

```bash
# API URLを取得
API_URL=$(pulumi stack output api_url)

# ヘルスチェック
curl $API_URL/health

# メッセージ一覧
curl $API_URL/api/messages
```

## 💰 コスト見積もり

**月間想定（低トラフィック）**:

- Lambda: ~$1（100万リクエスト無料枠内）
- DynamoDB: ~$1（オンデマンド）
- S3: ~$0.5（ストレージ + 転送）
- API Gateway: ~$1（100万リクエスト）

**合計: ~$3-5/月**

## 🔧 Terraformからの移行

既存のTerraform stateから移行する場合：

```bash
# Terraform state確認
cd ../../../../infrastructure/terraform/aws
terraform show

# Pulumi import（手動で必要なリソースをインポート）
pulumi import aws:dynamodb/table:Table messages-table simple-sns-messages-staging
pulumi import aws:s3/bucketV2:BucketV2 images-bucket simple-sns-images-staging
```

## 🔗 関連リンク

- [Pulumi AWS Provider](https://www.pulumi.com/registry/packages/aws/)
- [Pulumi Python SDK](https://www.pulumi.com/docs/languages-sdks/python/)
