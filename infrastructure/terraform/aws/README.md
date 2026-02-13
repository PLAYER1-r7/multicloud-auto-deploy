# Multi-Cloud Auto Deploy - AWS Terraform Configuration

この Terraform 設定は、AWS 上に Multi-Cloud Auto Deploy アプリケーションをデプロイします。

## リソース

- **S3**: フロントエンドホスティング
- **CloudFront**: CDN
- **Lambda**: バックエンド API
- **API Gateway**: HTTP API
- **DynamoDB**: データストレージ

## 使用方法

1. **初期化**
```bash
terraform init
```

2. **プラン**
```bash
terraform plan -var="environment=staging"
```

3. **適用**
```bash
terraform apply -var="environment=staging"
```

4. **破棄**
```bash
terraform destroy -var="environment=staging"
```

## 変数

- `aws_region`: AWS リージョン（デフォルト: us-east-1）
- `environment`: 環境名（staging/production）
- `project_name`: プロジェクト名
- `domain_name`: カスタムドメイン（オプション）

## 出力

- `frontend_url`: フロントエンド URL
- `api_endpoint`: API エンドポイント
- `frontend_bucket_name`: S3 バケット名
- `cloudfront_distribution_id`: CloudFront ディストリビューション ID
