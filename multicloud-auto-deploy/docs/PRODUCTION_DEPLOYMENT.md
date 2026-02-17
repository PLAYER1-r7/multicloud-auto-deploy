# Production Deployment Guide

本番環境へのデプロイ手順とベストプラクティス

## 📋 デプロイ前チェックリスト

- [ ] 環境変数の設定確認
- [ ] シークレットの安全な保管（AWS Secrets Manager / Azure Key Vault / GCP Secret Manager）
- [ ] Docker イメージのビルドとテスト
- [ ] ヘルスチェックエンドポイントの確認
- [ ] ログ設定の確認
- [ ] バックアップ戦略の確立

## 🐳 Docker イメージの準備

### 1. イメージのビルド

```bash
# APIのビルド
cd services/api
docker build -t mcad-api:latest .

# Reflexフロントエンドのビルド
cd services/frontend_reflex
docker build -t mcad-frontend:latest .
```

### 2. イメージのプッシュ

```bash
# AWS ECR
aws ecr get-login-password --region ap-northeast-1 | \
  docker login --username AWS --password-stdin <account-id>.dkr.ecr.ap-northeast-1.amazonaws.com

docker tag mcad-api:latest <account-id>.dkr.ecr.ap-northeast-1.amazonaws.com/mcad-api:latest
docker push <account-id>.dkr.ecr.ap-northeast-1.amazonaws.com/mcad-api:latest

docker tag mcad-frontend:latest <account-id>.dkr.ecr.ap-northeast-1.amazonaws.com/mcad-frontend:latest
docker push <account-id>.dkr.ecr.ap-northeast-1.amazonaws.com/mcad-frontend:latest
```

## ☁️ AWS デプロイ

### Option 1: Lambda (API のみ - 現在の構成)

```bash
cd infrastructure/pulumi/aws/simple-sns
pulumi up
```

**特徴：**
- サーバーレス、自動スケーリング
- 従量課金（リクエストベース）
- コールドスタート有り

### Option 2: App Runner (推奨 - フロントエンド用)

AWS App Runnerを使用してReflexフロントエンドをデプロイ:

```bash
# ECRリポジトリ作成
aws ecr create-repository --repository-name mcad-frontend --region ap-northeast-1

# イメージプッシュ（上記参照）

# App Runnerサービス作成
aws apprunner create-service \
  --service-name mcad-frontend-staging \
  --source-configuration '{
    "ImageRepository": {
      "ImageIdentifier": "<account-id>.dkr.ecr.ap-northeast-1.amazonaws.com/mcad-frontend:latest",
      "ImageRepositoryType": "ECR",
      "ImageConfiguration": {
        "Port": "3002",
        "RuntimeEnvironmentVariables": {
          "API_URL": "https://your-api-gateway-url.amazonaws.com"
        }
      }
    },
    "AutoDeploymentsEnabled": true
  }' \
  --instance-configuration '{
    "Cpu": "1024",
    "Memory": "2048"
  }' \
  --region ap-northeast-1
```

**特徴：**
- フルマネージド
- 自動スケーリング
- HTTPS証明書自動管理
- 月額約$5〜（アイドル時）

### Option 3: ECS Fargate (高度な制御が必要な場合)

```bash
# ECSクラスターとサービスの作成（Pulumi推奨）
cd infrastructure/pulumi/aws/simple-sns
# __main__.pyにECS設定を追加
pulumi up
```

**特徴：**
- より細かい制御
- VPC、セキュリティグループの管理
- 複数コンテナのオーケストレーション

## 🔐 環境変数とシークレット

### AWS Secrets Manager

```bash
# APIシークレット作成
aws secretsmanager create-secret \
  --name mcad-api-secrets \
  --secret-string '{
    "MINIO_ACCESS_KEY": "your-access-key",
    "MINIO_SECRET_KEY": "your-secret-key"
  }' \
  --region ap-northeast-1

# 取得
aws secretsmanager get-secret-value \
  --secret-id mcad-api-secrets \
  --region ap-northeast-1
```

### 環境変数の設定

**API (Lambda):**
- Pulumi `__main__.py`の環境変数セクションで設定

**Frontend (App Runner):**
- App Runnerサービス作成時に `RuntimeEnvironmentVariables` で設定
- または、AWSコンソールから更新

## 🔄 CI/CD パイプライン

### GitHub Actions (推奨)

`.github/workflows/deploy-production.yml`:

```yaml
name: Deploy to Production

on:
  push:
    branches: [main]
    tags: ['v*']

jobs:
  deploy-api:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Configure AWS credentials
        uses: aws-actions/configure-aws-credentials@v2
        with:
          aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
          aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
          aws-region: ap-northeast-1
      
      - name: Login to ECR
        run: |
          aws ecr get-login-password | docker login --username AWS --password-stdin ${{ secrets.ECR_REGISTRY }}
      
      - name: Build and push API image
        run: |
          cd services/api
          docker build -t ${{ secrets.ECR_REGISTRY }}/mcad-api:${{ github.sha }} .
          docker push ${{ secrets.ECR_REGISTRY }}/mcad-api:${{ github.sha }}
      
      - name: Deploy with Pulumi
        uses: pulumi/actions@v4
        with:
          work-dir: infrastructure/pulumi/aws/simple-sns
          command: up
          stack-name: production
        env:
          PULUMI_ACCESS_TOKEN: ${{ secrets.PULUMI_ACCESS_TOKEN }}

  deploy-frontend:
    runs-on: ubuntu-latest
    needs: deploy-api
    steps:
      - uses: actions/checkout@v3
      
      - name: Build and push Frontend image
        run: |
          # Similar to API deployment
          
      - name: Update App Runner service
        run: |
          aws apprunner update-service \
            --service-arn ${{ secrets.APPRUNNER_SERVICE_ARN }} \
            --source-configuration ...
```

## 📊 モニタリング

### CloudWatch ログ

```bash
# Lambda ログ
aws logs tail /aws/lambda/simple-sns-api-staging --follow

# App Runner ログ
aws logs tail /aws/apprunner/mcad-frontend-staging/service --follow
```

### メトリクス

- Lambda: 実行時間、エラー率、同時実行数
- App Runner: CPU、メモリ、リクエスト数
- DynamoDB: 読み取り/書き込みキャパシティ
- S3: リクエスト数、データ転送量

## 🔄 ロールバック手順

### Lambda

```bash
# 以前のバージョンに戻す
aws lambda update-function-code \
  --function-name simple-sns-api-staging \
  --image-uri <account-id>.dkr.ecr.ap-northeast-1.amazonaws.com/mcad-api:<previous-tag>
```

### App Runner

```bash
# 以前のデプロイメントに戻す
aws apprunner list-operations --service-arn <service-arn>
aws apprunner start-deployment --service-arn <service-arn>
```

### Pulumi

```bash
# スタックの履歴を表示
pulumi stack history

# 特定のバージョンに戻す
pulumi stack select staging
pulumi refresh
pulumi up --target <specific-resource>
```

## 💰 コスト最適化

1. **Lambda**: 適切なメモリ設定（128MB〜3GB）
2. **DynamoDB**: オンデマンドモード（低トラフィック）またはプロビジョニングモード（高トラフィック）
3. **S3**: ライフサイクルポリシーで古いファイル削除
4. **App Runner**: 最小インスタンス数の調整（0〜複数）
5. **CloudWatch**: ログ保持期間の設定（7日〜90日）

## 🔒 セキュリティベストプラクティス

1. **IAM**: 最小権限の原則
2. **VPC**: プライベートサブネットの使用
3. **WAF**: API GatewayまたはApp Runnerに適用
4. **Secrets**: AWS Secrets Managerの使用
5. **暗号化**: S3バケット暗号化、転送中の暗号化（TLS）

## 📚 参考資料

- [AWS Lambda ベストプラクティス](https://docs.aws.amazon.com/lambda/latest/dg/best-practices.html)
- [AWS App Runner ドキュメント](https://docs.aws.amazon.com/apprunner/)
- [Pulumi AWS プロバイダー](https://www.pulumi.com/registry/packages/aws/)
- [Reflex デプロイメントガイド](https://reflex.dev/docs/hosting/self-hosting/)

