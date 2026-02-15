# AWS デプロイメントガイド


![AWS](images/icons/aws.svg)

このドキュメントでは、Multi-Cloud Auto Deploy アプリケーションをAWSにデプロイする詳細な手順を説明します。

## アーキテクチャ

```
┌─────────────┐
│   Route 53  │ (オプション)
└──────┬──────┘
       │
┌──────▼──────────┐
│   CloudFront    │ CDN
└──────┬──────────┘
       │
┌──────▼──────────┐
│   S3 Bucket     │ 静的ホスティング
└─────────────────┘

┌─────────────────┐
│  API Gateway    │ HTTP API
└──────┬──────────┘
       │
┌──────▼──────────┐
│   Lambda        │ Python 3.11
└──────┬──────────┘
       │
┌──────▼──────────┐
│   DynamoDB      │ NoSQL DB
└─────────────────┘
```

## デプロイ方法

### 方法1: スクリプトによる自動デプロイ

```bash
# 環境設定
export AWS_REGION=us-east-1
export ENVIRONMENT=staging

# デプロイ実行
./scripts/deploy-aws.sh staging
```

### 方法2: GitHub Actions

1. GitHub Secretsの設定
2. `main`ブランチへプッシュまたは手動トリガー

### 方法3: 手動デプロイ

#### ステップ1: フロントエンドのビルド

```bash
cd services/frontend
npm install
VITE_API_URL="https://your-api-id.execute-api.us-east-1.amazonaws.com" npm run build
```

#### ステップ2: Terraformでインフラ構築

```bash
cd infrastructure/terraform/aws

# プレースホルダーLambdaの作成
echo "print('placeholder')" > lambda_placeholder.py
zip lambda_placeholder.zip lambda_placeholder.py
rm lambda_placeholder.py

# Terraform実行
terraform init
terraform apply -var="environment=staging"
```

#### ステップ3: フロントエンドをS3にアップロード

```bash
# Terraformの出力からバケット名を取得
BUCKET_NAME=$(cd infrastructure/terraform/aws && terraform output -raw frontend_bucket_name)

# アップロード
aws s3 sync services/frontend/dist/ "s3://${BUCKET_NAME}/" --delete
```

#### ステップ4: Lambda関数をデプロイ

```bash
# Lambdaパッケージを作成
cd services/backend
pip install -r requirements.txt -t package/
cp -r src/* package/
cd package && zip -r ../lambda.zip . && cd ..

# デプロイ
FUNCTION_NAME=$(cd ../../infrastructure/terraform/aws && terraform output -raw lambda_function_name)
aws lambda update-function-code \
    --function-name "$FUNCTION_NAME" \
    --zip-file fileb://lambda.zip
```

#### ステップ5: CloudFrontキャッシュの無効化

```bash
DISTRIBUTION_ID=$(cd infrastructure/terraform/aws && terraform output -raw cloudfront_distribution_id)
aws cloudfront create-invalidation \
    --distribution-id "$DISTRIBUTION_ID" \
    --paths "/*"
```

## リソース

生成されるAWSリソース：

- **S3 Bucket**: フロントエンドホスティング
- **CloudFront Distribution**: CDN
- **Lambda Function**: バックエンドAPI
- **API Gateway (HTTP API)**: APIエンドポイント
- **DynamoDB Table**: データストレージ
- **IAM Roles**: Lambda実行ロール
- **CloudWatch Logs**: ログストリーム

## コスト見積もり

月額概算（us-east-1、小規模使用時）：

- S3: ~$1
- CloudFront: ~$1-5
- Lambda: ~$0-1（無料枠内）
- API Gateway: ~$1
- DynamoDB: ~$0-1（無料枠内）

**合計: ~$3-10/月**

## カスタムドメインの設定

### 1. Route 53でドメインを管理

```bash
# ホストゾーンID取得
HOSTED_ZONE_ID=$(aws route53 list-hosted-zones-by-name \
    --dns-name example.com \
    --query "HostedZones[0].Id" \
    --output text)
```

### 2. ACM証明書の取得

```bash
# us-east-1リージョンで証明書をリクエスト（CloudFront用）
aws acm request-certificate \
    --domain-name "app.example.com" \
    --validation-method DNS \
    --region us-east-1
```

### 3. Terraformに追加

`terraform.tfvars`を作成：

```hcl
domain_name = "app.example.com"
certificate_arn = "arn:aws:acm:us-east-1:123456789012:certificate/..."
hosted_zone_id = "Z1234567890ABC"
```

## モニタリング

### CloudWatch Logs

```bash
# Lambda ログの確認
aws logs tail /aws/lambda/multicloud-auto-deploy-staging-api \
    --follow \
    --region us-east-1
```

### メトリクス

- Lambda実行回数
- API Gatewayリクエスト数
- CloudFrontヒット率
- DynamoDB読み書き

## トラブルシューティング

### Lambda関数が動作しない

```bash
# ログ確認
aws logs tail /aws/lambda/your-function-name --follow

# 関数の設定確認
aws lambda get-function --function-name your-function-name
```

### S3アクセスエラー

```bash
# バケットポリシー確認
aws s3api get-bucket-policy --bucket your-bucket-name

# パブリックアクセス設定確認
aws s3api get-public-access-block --bucket your-bucket-name
```

### API Gateway CORS エラー

Lambda関数が正しいCORSヘッダーを返しているか確認：

```python
return {
    'statusCode': 200,
    'headers': {
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Headers': '*',
        'Access-Control-Allow-Methods': '*'
    },
    'body': json.dumps(data)
}
```

## クリーンアップ

```bash
cd infrastructure/terraform/aws
terraform destroy -var="environment=staging"
```

## 次のステップ

- [カスタムドメインの設定](../DNS_SETUP.md)
- [CI/CD パイプラインの最適化](../CICD_OPTIMIZATION.md)
- [セキュリティベストプラクティス](../SECURITY.md)
