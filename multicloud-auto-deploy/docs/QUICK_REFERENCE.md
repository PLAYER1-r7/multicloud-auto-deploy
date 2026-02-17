# クイックリファレンス

AWS/Azure/GCP マルチクラウド環境の運用で頻繁に使用するコマンドをまとめたものです。

## 📋 目次

- [エンドポイント一覧](#エンドポイント一覧)
- [デプロイ](#デプロイ)
- [テストとデバッグ](#テストとデバッグ)
- [ログ確認](#ログ確認)
- [監視とメトリクス](#監視とメトリクス)
- [トラブルシューティング](#トラブルシューティング)
- [リソース管理](#リソース管理)

---

## エンドポイント一覧

### AWS
```bash
API: https://z42qmqdqac.execute-api.ap-northeast-1.amazonaws.com
CDN: https://dx3l4mbwg1ade.cloudfront.net
```

### Azure
```bash
API: https://multicloud-auto-deploy-staging-func-d8a2guhfere0etcq.japaneast-01.azurewebsites.net/api/HttpTrigger
CDN: https://multicloud-frontend-f9cvamfnauexasd8.z01.azurefd.net
```

### GCP
```bash
API: https://multicloud-auto-deploy-staging-api-899621454670.asia-northeast1.run.app
CDN: http://34.120.43.83
```

---

## デプロイ

### Lambda関数のデプロイ

```bash
# GitHub Actions経由でデプロイ（推奨）
gh workflow run deploy-aws.yml

# または Pulumi CLI を使用
cd infrastructure/pulumi/aws
pulumi up
```

### 手動デプロイ

```bash
# ZIPパッケージ作成
cd services/api
pip3 install -r requirements.txt -t .build/package/ --platform manylinux2014_x86_64 --only-binary=:all:
cp -r app .build/package/
cd .build/package && zip -r9 ../lambda.zip .

# S3アップロード
aws s3 cp .build/lambda.zip s3://YOUR_BUCKET/lambda-deployments/lambda.zip

# Lambda関数更新
aws lambda update-function-code \
  --function-name YOUR_FUNCTION_NAME \
  --s3-bucket YOUR_BUCKET \
  --s3-key lambda-deployments/lambda.zip \
  --publish
```

### フロントエンドのデプロイ

```bash
# React SPAビルドとS3デプロイ
cd services/frontend_react
npm run build
aws s3 sync dist/ s3://YOUR_FRONTEND_BUCKET/ --delete

# CloudFrontキャッシュ無効化
aws cloudfront create-invalidation \
  --distribution-id YOUR_DISTRIBUTION_ID \
  --paths "/*"
```

---

## テストとデバッグ

### API統合テスト

```bash
# 完全なCRUDテスト
./scripts/test-api.sh -e https://YOUR_API_ID.execute-api.ap-northeast-1.amazonaws.com

# 詳細モード
./scripts/test-api.sh -e https://YOUR_API.amazonaws.com --verbose
```

### Lambda直接呼び出しテスト

```bash
# HTTP API v2ペイロード形式
aws lambda invoke \
  --function-name YOUR_FUNCTION_NAME \
  --payload '{
    "version": "2.0",
    "routeKey": "$default",
    "rawPath": "/api/messages/",
    "headers": {"accept": "application/json"},
    "requestContext": {
      "http": {
        "method": "GET",
        "path": "/api/messages/"
      }
    }
  }' \
  --cli-binary-format raw-in-base64-out \
  /tmp/response.json

cat /tmp/response.json | jq .
```

### curlでAPI直接テスト

```bash
# GET
curl -v https://YOUR_API.amazonaws.com/api/messages/

# POST
curl -X POST https://YOUR_API.amazonaws.com/api/messages/ \
  -H "Content-Type: application/json" \
  -d '{"content":"Test message","author":"Tester"}'

# PUT
curl -X PUT https://YOUR_API.amazonaws.com/api/messages/MESSAGE_ID \
  -H "Content-Type: application/json" \
  -d '{"content":"Updated message"}'

# DELETE
curl -X DELETE https://YOUR_API.amazonaws.com/api/messages/MESSAGE_ID
```

---

## ログ確認

### Lambda実行ログ

```bash
# リアルタイムログ
aws logs tail /aws/lambda/YOUR_FUNCTION_NAME --follow

# 過去10分のログ
aws logs tail /aws/lambda/YOUR_FUNCTION_NAME --since 10m

# エラーのみフィルタ
aws logs tail /aws/lambda/YOUR_FUNCTION_NAME --follow --filter-pattern "ERROR"

# JSONフォーマット
aws logs tail /aws/lambda/YOUR_FUNCTION_NAME --format json
```

### API Gatewayアクセスログ

```bash
# リアルタイムアクセスログ
aws logs tail /aws/apigateway/YOUR_API_NAME --follow

# 過去5分のログ
aws logs tail /aws/apigateway/YOUR_API_NAME --since 5m

# エラーのみ
aws logs tail /aws/apigateway/YOUR_API_NAME --filter-pattern "5XX"
```

### CloudWatch Logs Insights（高度なクエリ）

```bash
# エラー集計
aws logs start-query \
  --log-group-name /aws/lambda/YOUR_FUNCTION_NAME \
  --start-time $(date -u -d '1 hour ago' +%s) \
  --end-time $(date -u +%s) \
  --query-string 'fields @timestamp, @message | filter @message like /ERROR/ | stats count() by bin(5m)'

# 実行時間統計
aws logs start-query \
  --log-group-name /aws/lambda/YOUR_FUNCTION_NAME \
  --start-time $(date -u -d '1 hour ago' +%s) \
  --end-time $(date -u +%s) \
  --query-string 'fields @timestamp, @duration | stats avg(@duration), max(@duration), min(@duration)'
```

---

## 監視とメトリクス

### Lambda メトリクス

```bash
# 呼び出し回数
aws cloudwatch get-metric-statistics \
  --namespace AWS/Lambda \
  --metric-name Invocations \
  --dimensions Name=FunctionName,Value=YOUR_FUNCTION_NAME \
  --start-time $(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 300 \
  --statistics Sum

# エラー回数
aws cloudwatch get-metric-statistics \
  --namespace AWS/Lambda \
  --metric-name Errors \
  --dimensions Name=FunctionName,Value=YOUR_FUNCTION_NAME \
  --start-time $(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 300 \
  --statistics Sum

# 実行時間
aws cloudwatch get-metric-statistics \
  --namespace AWS/Lambda \
  --metric-name Duration \
  --dimensions Name=FunctionName,Value=YOUR_FUNCTION_NAME \
  --start-time $(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 300 \
  --statistics Average,Maximum

# スロットリング
aws cloudwatch get-metric-statistics \
  --namespace AWS/Lambda \
  --metric-name Throttles \
  --dimensions Name=FunctionName,Value=YOUR_FUNCTION_NAME \
  --start-time $(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 300 \
  --statistics Sum
```

### API Gateway メトリクス

```bash
# リクエスト数
aws cloudwatch get-metric-statistics \
  --namespace AWS/ApiGateway \
  --metric-name Count \
  --dimensions Name=ApiId,Value=YOUR_API_ID \
  --start-time $(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 300 \
  --statistics Sum

# 5XXエラー
aws cloudwatch get-metric-statistics \
  --namespace AWS/ApiGateway \
  --metric-name 5XXError \
  --dimensions Name=ApiId,Value=YOUR_API_ID \
  --start-time $(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 300 \
  --statistics Sum

# レイテンシ
aws cloudwatch get-metric-statistics \
  --namespace AWS/ApiGateway \
  --metric-name Latency \
  --dimensions Name=ApiId,Value=YOUR_API_ID \
  --start-time $(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 300 \
  --statistics Average,p99
```

### アラーム作成

```bash
# 監視設定の一括作成
./scripts/setup-monitoring.sh

# メール通知付き
ALERT_EMAIL=your@email.com ./scripts/setup-monitoring.sh

# アラーム一覧
aws cloudwatch describe-alarms --alarm-name-prefix YOUR_PROJECT

# アラーム状態確認
aws cloudwatch describe-alarms --state-value ALARM
```

---

## トラブルシューティング

### Lambda権限確認

```bash
# リソースポリシー確認
aws lambda get-policy \
  --function-name YOUR_FUNCTION_NAME \
  --query Policy \
  --output text | jq .

# 実行ロール確認
aws lambda get-function-configuration \
  --function-name YOUR_FUNCTION_NAME \
  --query Role

# 実行ロールのポリシー確認
ROLE_NAME=$(aws lambda get-function-configuration --function-name YOUR_FUNCTION_NAME --query Role --output text | awk -F/ '{print $NF}')
aws iam list-attached-role-policies --role-name $ROLE_NAME
```

### API Gateway権限設定（HTTP API）

```bash
# 正しい権限追加
aws lambda add-permission \
  --function-name YOUR_FUNCTION_NAME \
  --statement-id apigateway-http-api \
  --action lambda:InvokeFunction \
  --principal apigateway.amazonaws.com \
  --source-arn "arn:aws:execute-api:REGION:ACCOUNT_ID:API_ID/*/*"

# 誤った権限削除
aws lambda remove-permission \
  --function-name YOUR_FUNCTION_NAME \
  --statement-id OLD_STATEMENT_ID
```

### API Gatewayアクセスログ有効化

```bash
# ロググループ作成
aws logs create-log-group \
  --log-group-name /aws/apigateway/YOUR_API_NAME

# アクセスログ有効化
aws apigatewayv2 update-stage \
  --api-id YOUR_API_ID \
  --stage-name '$default' \
  --access-log-settings "DestinationArn=arn:aws:logs:REGION:ACCOUNT_ID:log-group:/aws/apigateway/YOUR_API_NAME:*,Format=\$context.requestId \$context.error.message \$context.integrationErrorMessage \$context.status"

# ログ確認
aws logs tail /aws/apigateway/YOUR_API_NAME --follow
```

### Lambda関数の状態確認

```bash
# 関数情報
aws lambda get-function --function-name YOUR_FUNCTION_NAME

# 設定情報
aws lambda get-function-configuration --function-name YOUR_FUNCTION_NAME

# 環境変数確認
aws lambda get-function-configuration \
  --function-name YOUR_FUNCTION_NAME \
  --query Environment

# タイムアウトとメモリ確認
aws lambda get-function-configuration \
  --function-name YOUR_FUNCTION_NAME \
  --query '[Timeout,MemorySize]' \
  --output table
```

---

## リソース管理

### Lambda関数の削除

```bash
aws lambda delete-function --function-name YOUR_FUNCTION_NAME
```

### API Gatewayの削除

```bash
# HTTP API
aws apigatewayv2 delete-api --api-id YOUR_API_ID

# REST API
aws apigateway delete-rest-api --rest-api-id YOUR_API_ID
```

### CloudWatch Logsの削除

```bash
# ロググループ削除
aws logs delete-log-group --log-group-name /aws/lambda/YOUR_FUNCTION_NAME
aws logs delete-log-group --log-group-name /aws/apigateway/YOUR_API_NAME
```

### S3バケットのクリーンアップ

```bash
# バケット内のオブジェクト削除
aws s3 rm s3://YOUR_BUCKET/ --recursive

# バケット削除
aws s3 rb s3://YOUR_BUCKET
```

### DynamoDBテーブルの削除

```bash
aws dynamodb delete-table --table-name YOUR_TABLE_NAME
```

### CloudWatch アラームの削除

```bash
# 特定のアラーム削除
aws cloudwatch delete-alarms --alarm-names ALARM_NAME1 ALARM_NAME2

# プロジェクト全体のアラーム削除
aws cloudwatch describe-alarms \
  --alarm-name-prefix YOUR_PROJECT \
  --query 'MetricAlarms[*].AlarmName' \
  --output text | xargs -n 1 aws cloudwatch delete-alarms --alarm-names
```

---

## 環境変数設定例

プロジェクト全体で使用する環境変数:

```bash
# ~/.bashrc または ~/.zshrc に追加
export PROJECT_NAME="multicloud-auto-deploy"
export ENVIRONMENT="staging"
export AWS_REGION="ap-northeast-1"
export FUNCTION_NAME="${PROJECT_NAME}-${ENVIRONMENT}-api"
export API_ID="abc123def4"
export DISTRIBUTION_ID="EXXXXXXXXXXXX"
export FRONTEND_BUCKET="${PROJECT_NAME}-${ENVIRONMENT}-frontend"
export ALERT_EMAIL="your@email.com"

# エイリアス設定
alias lambda-logs='aws logs tail /aws/lambda/$FUNCTION_NAME --follow'
alias api-logs='aws logs tail /aws/apigateway/$PROJECT_NAME-$ENVIRONMENT-api --follow'
alias api-test='~/projects/multicloud-auto-deploy/scripts/test-api.sh -e https://$API_ID.execute-api.$AWS_REGION.amazonaws.com'
```

---

## 関連ドキュメント

- [トラブルシューティングガイド](TROUBLESHOOTING.md)
- [エンドポイント一覧](ENDPOINTS.md)
- [メインREADME](../README.md)

---

## 便利なワンライナー

```bash
# Lambda関数一覧
aws lambda list-functions --query 'Functions[*].[FunctionName,Runtime,LastModified]' --output table

# API Gateway一覧
aws apigatewayv2 get-apis --query 'Items[*].[Name,ApiId,ApiEndpoint]' --output table

# CloudWatch アラーム状態一覧
aws cloudwatch describe-alarms --query 'MetricAlarms[*].[AlarmName,StateValue]' --output table

# DynamoDB テーブル一覧
aws dynamodb list-tables --query 'TableNames' --output table

# S3バケット一覧
aws s3 ls

# 最新のLambda実行ログ（最後の10行）
aws logs tail /aws/lambda/$FUNCTION_NAME --since 5m | tail -n 10

# Lambda関数のURLを取得
aws lambda get-function-url-config --function-name $FUNCTION_NAME --query FunctionUrl --output text

# API Gatewayエンドポイント取得
aws apigatewayv2 get-api --api-id $API_ID --query ApiEndpoint --output text
```
