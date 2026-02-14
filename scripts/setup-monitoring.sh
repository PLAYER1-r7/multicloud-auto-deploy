#!/bin/bash

# CloudWatch監視設定スクリプト
# Lambda + API Gatewayの包括的な監視とアラートを設定

set -e

# カラー定義
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 設定
PROJECT_NAME="${PROJECT_NAME:-multicloud-auto-deploy}"
ENVIRONMENT="${ENVIRONMENT:-staging}"
AWS_REGION="${AWS_REGION:-ap-northeast-1}"
FUNCTION_NAME="${FUNCTION_NAME:-${PROJECT_NAME}-${ENVIRONMENT}-api}"
SNS_TOPIC_NAME="${SNS_TOPIC_NAME:-${PROJECT_NAME}-${ENVIRONMENT}-alerts}"
EMAIL="${ALERT_EMAIL:-}"

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}CloudWatch 監視設定${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""

# 前提チェック
if ! command -v aws &> /dev/null; then
    echo -e "${RED}❌ AWS CLIがインストールされていません${NC}"
    exit 1
fi

ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
echo "AWSアカウントID: $ACCOUNT_ID"
echo "プロジェクト: $PROJECT_NAME"
echo "環境: $ENVIRONMENT"
echo ""

# SNSトピックの作成
echo -e "${YELLOW}1. SNSトピックの作成...${NC}"

TOPIC_ARN=$(aws sns list-topics --query "Topics[?contains(TopicArn, '$SNS_TOPIC_NAME')].TopicArn | [0]" --output text)

if [ "$TOPIC_ARN" == "None" ] || [ -z "$TOPIC_ARN" ]; then
    TOPIC_ARN=$(aws sns create-topic --name "$SNS_TOPIC_NAME" --query TopicArn --output text)
    echo -e "${GREEN}✅ SNSトピック作成完了${NC}"
    echo "   ARN: $TOPIC_ARN"
    
    # メールアドレスが指定されている場合はサブスクリプション作成
    if [ -n "$EMAIL" ]; then
        aws sns subscribe \
            --topic-arn "$TOPIC_ARN" \
            --protocol email \
            --notification-endpoint "$EMAIL" \
            > /dev/null
        
        echo -e "${GREEN}✅ メールサブスクリプション作成完了${NC}"
        echo "   メールに確認リンクが送信されます: $EMAIL"
    fi
else
    echo -e "${GREEN}✅ 既存のSNSトピックを使用${NC}"
    echo "   ARN: $TOPIC_ARN"
fi

echo ""

# Lambda関数のエラーアラーム
echo -e "${YELLOW}2. Lambda エラーアラームの作成...${NC}"

aws cloudwatch put-metric-alarm \
    --alarm-name "${FUNCTION_NAME}-errors" \
    --alarm-description "Lambda関数でエラーが発生しました" \
    --metric-name Errors \
    --namespace AWS/Lambda \
    --statistic Sum \
    --period 300 \
    --evaluation-periods 1 \
    --threshold 1 \
    --comparison-operator GreaterThanOrEqualToThreshold \
    --dimensions Name=FunctionName,Value="$FUNCTION_NAME" \
    --alarm-actions "$TOPIC_ARN" \
    --treat-missing-data notBreaching

echo -e "${GREEN}✅ エラーアラーム作成完了${NC}"

# Lambda関数のスロットリングアラーム
echo -e "${YELLOW}3. Lambda スロットリングアラームの作成...${NC}"

aws cloudwatch put-metric-alarm \
    --alarm-name "${FUNCTION_NAME}-throttles" \
    --alarm-description "Lambda関数がスロットリングされました" \
    --metric-name Throttles \
    --namespace AWS/Lambda \
    --statistic Sum \
    --period 300 \
    --evaluation-periods 1 \
    --threshold 1 \
    --comparison-operator GreaterThanOrEqualToThreshold \
    --dimensions Name=FunctionName,Value="$FUNCTION_NAME" \
    --alarm-actions "$TOPIC_ARN" \
    --treat-missing-data notBreaching

echo -e "${GREEN}✅ スロットリングアラーム作成完了${NC}"

# Lambda関数の実行時間アラーム
echo -e "${YELLOW}4. Lambda 実行時間アラームの作成...${NC}"

aws cloudwatch put-metric-alarm \
    --alarm-name "${FUNCTION_NAME}-duration" \
    --alarm-description "Lambda関数の実行時間が長すぎます" \
    --metric-name Duration \
    --namespace AWS/Lambda \
    --statistic Average \
    --period 300 \
    --evaluation-periods 2 \
    --threshold 25000 \
    --comparison-operator GreaterThanThreshold \
    --dimensions Name=FunctionName,Value="$FUNCTION_NAME" \
    --alarm-actions "$TOPIC_ARN" \
    --treat-missing-data notBreaching

echo -e "${GREEN}✅ 実行時間アラーム作成完了${NC}"

# Lambda関数の同時実行数アラーム
echo -e "${YELLOW}5. Lambda 同時実行数アラームの作成...${NC}"

aws cloudwatch put-metric-alarm \
    --alarm-name "${FUNCTION_NAME}-concurrent-executions" \
    --alarm-description "Lambda関数の同時実行数が高すぎます" \
    --metric-name ConcurrentExecutions \
    --namespace AWS/Lambda \
    --statistic Maximum \
    --period 60 \
    --evaluation-periods 2 \
    --threshold 100 \
    --comparison-operator GreaterThanThreshold \
    --dimensions Name=FunctionName,Value="$FUNCTION_NAME" \
    --alarm-actions "$TOPIC_ARN" \
    --treat-missing-data notBreaching

echo -e "${GREEN}✅ 同時実行数アラーム作成完了${NC}"

# API Gatewayの5XXエラーアラーム
echo -e "${YELLOW}6. API Gateway エラーアラームの作成...${NC}"

API_ID=$(aws apigatewayv2 get-apis --query "Items[?Name=='${PROJECT_NAME}-${ENVIRONMENT}-api'].ApiId | [0]" --output text)

if [ "$API_ID" != "None" ] && [ -n "$API_ID" ]; then
    aws cloudwatch put-metric-alarm \
        --alarm-name "${PROJECT_NAME}-${ENVIRONMENT}-api-5xx-errors" \
        --alarm-description "API Gateway 5XXエラーが発生しています" \
        --metric-name 5XXError \
        --namespace AWS/ApiGateway \
        --statistic Sum \
        --period 300 \
        --evaluation-periods 1 \
        --threshold 5 \
        --comparison-operator GreaterThanOrEqualToThreshold \
        --dimensions Name=ApiId,Value="$API_ID" \
        --alarm-actions "$TOPIC_ARN" \
        --treat-missing-data notBreaching
    
    echo -e "${GREEN}✅ API Gateway エラーアラーム作成完了${NC}"
    
    # API Gatewayのレイテンシアラーム
    aws cloudwatch put-metric-alarm \
        --alarm-name "${PROJECT_NAME}-${ENVIRONMENT}-api-latency" \
        --alarm-description "API Gatewayのレスポンスが遅すぎます" \
        --metric-name Latency \
        --namespace AWS/ApiGateway \
        --statistic Average \
        --period 300 \
        --evaluation-periods 2 \
        --threshold 3000 \
        --comparison-operator GreaterThanThreshold \
        --dimensions Name=ApiId,Value="$API_ID" \
        --alarm-actions "$TOPIC_ARN" \
        --treat-missing-data notBreaching
    
    echo -e "${GREEN}✅ API Gateway レイテンシアラーム作成完了${NC}"
else
    echo -e "${YELLOW}⚠️  API Gatewayが見つかりません。スキップします${NC}"
fi

# DynamoDBのスロットリングアラーム
echo -e "${YELLOW}7. DynamoDB アラームの作成...${NC}"

TABLE_NAME="${PROJECT_NAME}-${ENVIRONMENT}-messages"

if aws dynamodb describe-table --table-name "$TABLE_NAME" &> /dev/null; then
    aws cloudwatch put-metric-alarm \
        --alarm-name "${TABLE_NAME}-read-throttles" \
        --alarm-description "DynamoDBの読み込みがスロットリングされました" \
        --metric-name ReadThrottleEvents \
        --namespace AWS/DynamoDB \
        --statistic Sum \
        --period 300 \
        --evaluation-periods 1 \
        --threshold 1 \
        --comparison-operator GreaterThanOrEqualToThreshold \
        --dimensions Name=TableName,Value="$TABLE_NAME" \
        --alarm-actions "$TOPIC_ARN" \
        --treat-missing-data notBreaching
    
    aws cloudwatch put-metric-alarm \
        --alarm-name "${TABLE_NAME}-write-throttles" \
        --alarm-description "DynamoDBの書き込みがスロットリングされました" \
        --metric-name WriteThrottleEvents \
        --namespace AWS/DynamoDB \
        --statistic Sum \
        --period 300 \
        --evaluation-periods 1 \
        --threshold 1 \
        --comparison-operator GreaterThanOrEqualToThreshold \
        --dimensions Name=TableName,Value="$TABLE_NAME" \
        --alarm-actions "$TOPIC_ARN" \
        --treat-missing-data notBreaching
    
    echo -e "${GREEN}✅ DynamoDB アラーム作成完了${NC}"
else
    echo -e "${YELLOW}⚠️  DynamoDBテーブルが見つかりません。スキップします${NC}"
fi

# CloudWatch Logsのメトリクスフィルター
echo -e "${YELLOW}8. CloudWatch Logs メトリクスフィルターの作成...${NC}"

LOG_GROUP_NAME="/aws/lambda/$FUNCTION_NAME"

# ERRORレベルのログをカウント
aws logs put-metric-filter \
    --log-group-name "$LOG_GROUP_NAME" \
    --filter-name "${FUNCTION_NAME}-error-count" \
    --filter-pattern "[ERROR]" \
    --metric-transformations \
        metricName=ErrorCount,metricNamespace=CustomMetrics/$PROJECT_NAME,metricValue=1,defaultValue=0 \
    2>/dev/null || echo "メトリクスフィルターは既に存在します"

# エラーカウントのアラーム
aws cloudwatch put-metric-alarm \
    --alarm-name "${FUNCTION_NAME}-log-errors" \
    --alarm-description "Lambda関数のログにERRORが見つかりました" \
    --metric-name ErrorCount \
    --namespace "CustomMetrics/$PROJECT_NAME" \
    --statistic Sum \
    --period 300 \
    --evaluation-periods 1 \
    --threshold 5 \
    --comparison-operator GreaterThanOrEqualToThreshold \
    --alarm-actions "$TOPIC_ARN" \
    --treat-missing-data notBreaching

echo -e "${GREEN}✅ メトリクスフィルターとアラーム作成完了${NC}"

# ダッシュボードの作成
echo -e "${YELLOW}9. CloudWatch ダッシュボードの作成...${NC}"

DASHBOARD_NAME="${PROJECT_NAME}-${ENVIRONMENT}-dashboard"

cat > /tmp/dashboard-body.json <<EOF
{
  "widgets": [
    {
      "type": "metric",
      "properties": {
        "metrics": [
          ["AWS/Lambda", "Invocations", {"stat": "Sum", "label": "呼び出し回数"}],
          [".", "Errors", {"stat": "Sum", "label": "エラー"}],
          [".", "Throttles", {"stat": "Sum", "label": "スロットリング"}]
        ],
        "period": 300,
        "stat": "Sum",
        "region": "$AWS_REGION",
        "title": "Lambda: $FUNCTION_NAME",
        "dimensions": {"FunctionName": ["$FUNCTION_NAME"]},
        "yAxis": {"left": {"min": 0}}
      }
    },
    {
      "type": "metric",
      "properties": {
        "metrics": [
          ["AWS/Lambda", "Duration", {"stat": "Average", "label": "平均実行時間"}],
          ["...", {"stat": "Maximum", "label": "最大実行時間"}]
        ],
        "period": 300,
        "stat": "Average",
        "region": "$AWS_REGION",
        "title": "Lambda実行時間 (ms)",
        "dimensions": {"FunctionName": ["$FUNCTION_NAME"]},
        "yAxis": {"left": {"min": 0}}
      }
    },
    {
      "type": "metric",
      "properties": {
        "metrics": [
          ["AWS/ApiGateway", "Count", {"stat": "Sum", "label": "リクエスト数"}],
          [".", "4XXError", {"stat": "Sum", "label": "4XXエラー"}],
          [".", "5XXError", {"stat": "Sum", "label": "5XXエラー"}]
        ],
        "period": 300,
        "stat": "Sum",
        "region": "$AWS_REGION",
        "title": "API Gateway",
        "dimensions": {"ApiId": ["$API_ID"]},
        "yAxis": {"left": {"min": 0}}
      }
    },
    {
      "type": "metric",
      "properties": {
        "metrics": [
          ["AWS/ApiGateway", "Latency", {"stat": "Average", "label": "平均レイテンシ"}],
          ["...", {"stat": "p99", "label": "p99レイテンシ"}]
        ],
        "period": 300,
        "stat": "Average",
        "region": "$AWS_REGION",
        "title": "API Gatewayレイテンシ (ms)",
        "dimensions": {"ApiId": ["$API_ID"]},
        "yAxis": {"left": {"min": 0}}
      }
    }
  ]
}
EOF

aws cloudwatch put-dashboard \
    --dashboard-name "$DASHBOARD_NAME" \
    --dashboard-body file:///tmp/dashboard-body.json

echo -e "${GREEN}✅ ダッシュボード作成完了${NC}"
echo "   https://console.aws.amazon.com/cloudwatch/home?region=$AWS_REGION#dashboards:name=$DASHBOARD_NAME"

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}監視設定完了！${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo "作成されたリソース:"
echo "  - SNSトピック: $SNS_TOPIC_NAME"
echo "  - CloudWatchアラーム: 10個"
echo "  - CloudWatchダッシュボード: $DASHBOARD_NAME"
echo ""

if [ -n "$EMAIL" ]; then
    echo -e "${YELLOW}⚠️  メールアドレス ($EMAIL) にサブスクリプション確認が送信されます${NC}"
    echo "   確認リンクをクリックしてアラートを有効化してください"
    echo ""
fi

echo "アラーム一覧:"
aws cloudwatch describe-alarms --alarm-name-prefix "$PROJECT_NAME-$ENVIRONMENT" --query 'MetricAlarms[*].[AlarmName,StateValue]' --output table

echo ""
