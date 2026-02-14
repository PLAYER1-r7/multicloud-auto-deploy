#!/bin/bash

# Lambda Function デプロイスクリプト
# AWS Lambda + API Gateway統合の完全デプロイメント自動化

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
LAMBDA_ROLE_NAME="${LAMBDA_ROLE_NAME:-${PROJECT_NAME}-${ENVIRONMENT}-lambda-role}"
API_NAME="${API_NAME:-${PROJECT_NAME}-${ENVIRONMENT}-api}"

# ディレクトリ設定
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
API_DIR="$PROJECT_ROOT/services/api"
BUILD_DIR="$API_DIR/.build"

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Lambda Function デプロイスクリプト${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo "プロジェクト: $PROJECT_NAME"
echo "環境: $ENVIRONMENT"
echo "リージョン: $AWS_REGION"
echo "関数名: $FUNCTION_NAME"
echo ""

# 前提条件チェック
echo -e "${YELLOW}1. 前提条件のチェック...${NC}"

if ! command -v aws &> /dev/null; then
    echo -e "${RED}❌ AWS CLIがインストールされていません${NC}"
    exit 1
fi

if ! command -v python3 &> /dev/null; then
    echo -e "${RED}❌ Python3がインストールされていません${NC}"
    exit 1
fi

if ! command -v jq &> /dev/null; then
    echo -e "${RED}❌ jqがインストールされていません${NC}"
    exit 1
fi

# AWS認証情報確認
if ! aws sts get-caller-identity &> /dev/null; then
    echo -e "${RED}❌ AWS認証情報が設定されていません${NC}"
    exit 1
fi

ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
echo -e "${GREEN}✅ AWS認証情報OK (Account: $ACCOUNT_ID)${NC}"

# ビルドディレクトリのクリーンアップ
echo -e "${YELLOW}2. ビルドディレクトリのクリーンアップ...${NC}"
rm -rf "$BUILD_DIR"
mkdir -p "$BUILD_DIR/package"
echo -e "${GREEN}✅ クリーンアップ完了${NC}"

# 依存関係のインストール
echo -e "${YELLOW}3. 依存関係のインストール...${NC}"
cd "$API_DIR"
pip3 install -r requirements.txt \
    -t "$BUILD_DIR/package/" \
    --upgrade \
    --platform manylinux2014_x86_64 \
    --only-binary=:all: \
    2>&1 | grep -v "Requirement already satisfied" || true
echo -e "${GREEN}✅ 依存関係インストール完了${NC}"

# アプリケーションコードのコピー
echo -e "${YELLOW}4. アプリケーションコードのコピー...${NC}"
cp -r app "$BUILD_DIR/package/"
echo -e "${GREEN}✅ コピー完了${NC}"

# ZIPパッケージの作成
echo -e "${YELLOW}5. ZIPパッケージの作成...${NC}"
cd "$BUILD_DIR/package"
zip -r9 ../lambda.zip . > /dev/null
cd "$API_DIR"
PACKAGE_SIZE=$(du -h "$BUILD_DIR/lambda.zip" | cut -f1)
echo -e "${GREEN}✅ ZIPパッケージ作成完了 (サイズ: $PACKAGE_SIZE)${NC}"

# S3へのアップロード
echo -e "${YELLOW}6. S3へのZIPパッケージアップロード...${NC}"
S3_BUCKET="${PROJECT_NAME}-${ENVIRONMENT}-frontend"
S3_KEY="lambda-deployments/lambda-$(date +%Y%m%d-%H%M%S).zip"
S3_LATEST_KEY="lambda-deployments/lambda.zip"

aws s3 cp "$BUILD_DIR/lambda.zip" "s3://$S3_BUCKET/$S3_KEY"
aws s3 cp "$BUILD_DIR/lambda.zip" "s3://$S3_BUCKET/$S3_LATEST_KEY"
echo -e "${GREEN}✅ S3アップロード完了${NC}"
echo "   - バージョン付き: s3://$S3_BUCKET/$S3_KEY"
echo "   - 最新版: s3://$S3_BUCKET/$S3_LATEST_KEY"

# Lambda関数の存在確認
echo -e "${YELLOW}7. Lambda関数の確認...${NC}"
if aws lambda get-function --function-name "$FUNCTION_NAME" &> /dev/null; then
    echo "既存のLambda関数を更新します"
    
    # 関数コードの更新
    aws lambda update-function-code \
        --function-name "$FUNCTION_NAME" \
        --s3-bucket "$S3_BUCKET" \
        --s3-key "$S3_LATEST_KEY" \
        --publish \
        --output json > /tmp/lambda-update.json
    
    VERSION=$(jq -r '.Version' /tmp/lambda-update.json)
    echo -e "${GREEN}✅ Lambda関数更新完了 (Version: $VERSION)${NC}"
    
    # 設定の更新（念のため）
    aws lambda update-function-configuration \
        --function-name "$FUNCTION_NAME" \
        --timeout 30 \
        --memory-size 512 \
        --environment "Variables={STAGE=$ENVIRONMENT,AWS_REGION=$AWS_REGION}" \
        > /dev/null
    
    echo -e "${GREEN}✅ Lambda設定更新完了${NC}"
else
    echo "新しいLambda関数を作成します"
    
    # IAMロールの確認/作成
    if ! aws iam get-role --role-name "$LAMBDA_ROLE_NAME" &> /dev/null; then
        echo "Lambda実行ロールを作成します..."
        
        cat > /tmp/lambda-trust-policy.json <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Service": "lambda.amazonaws.com"
      },
      "Action": "sts:AssumeRole"
    }
  ]
}
EOF
        
        aws iam create-role \
            --role-name "$LAMBDA_ROLE_NAME" \
            --assume-role-policy-document file:///tmp/lambda-trust-policy.json \
            > /dev/null
        
        # 基本実行ロールのアタッチ
        aws iam attach-role-policy \
            --role-name "$LAMBDA_ROLE_NAME" \
            --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole
        
        # DynamoDBアクセス権限のアタッチ
        aws iam attach-role-policy \
            --role-name "$LAMBDA_ROLE_NAME" \
            --policy-arn arn:aws:iam::aws:policy/AmazonDynamoDBFullAccess
        
        echo "IAMロール作成完了。10秒待機..."
        sleep 10
    fi
    
    ROLE_ARN="arn:aws:iam::$ACCOUNT_ID:role/$LAMBDA_ROLE_NAME"
    
    # Lambda関数の作成
    aws lambda create-function \
        --function-name "$FUNCTION_NAME" \
        --runtime python3.12 \
        --handler app.main.handler \
        --role "$ROLE_ARN" \
        --code "S3Bucket=$S3_BUCKET,S3Key=$S3_LATEST_KEY" \
        --timeout 30 \
        --memory-size 512 \
        --environment "Variables={STAGE=$ENVIRONMENT,AWS_REGION=$AWS_REGION}" \
        --output json > /tmp/lambda-create.json
    
    echo -e "${GREEN}✅ Lambda関数作成完了${NC}"
fi

# API Gatewayの確認/作成
echo -e "${YELLOW}8. API Gatewayの確認...${NC}"

API_ID=$(aws apigatewayv2 get-apis --query "Items[?Name=='$API_NAME'].ApiId | [0]" --output text)

if [ "$API_ID" == "None" ] || [ -z "$API_ID" ]; then
    echo "新しいHTTP APIを作成します..."
    
    API_ID=$(aws apigatewayv2 create-api \
        --name "$API_NAME" \
        --protocol-type HTTP \
        --cors-configuration "AllowOrigins=*,AllowMethods=*,AllowHeaders=*" \
        --query ApiId \
        --output text)
    
    echo -e "${GREEN}✅ API Gateway作成完了 (ID: $API_ID)${NC}"
else
    echo -e "${GREEN}✅ 既存のAPI Gatewayを使用 (ID: $API_ID)${NC}"
fi

# Lambda統合の作成/更新
echo -e "${YELLOW}9. Lambda統合の設定...${NC}"

LAMBDA_ARN="arn:aws:lambda:$AWS_REGION:$ACCOUNT_ID:function:$FUNCTION_NAME"
INTEGRATION_URI="arn:aws:apigateway:$AWS_REGION:lambda:path/2015-03-31/functions/$LAMBDA_ARN/invocations"

# 既存の統合を確認
INTEGRATION_ID=$(aws apigatewayv2 get-integrations --api-id "$API_ID" --query "Items[?IntegrationUri=='$INTEGRATION_URI'].IntegrationId | [0]" --output text)

if [ "$INTEGRATION_ID" == "None" ] || [ -z "$INTEGRATION_ID" ]; then
    INTEGRATION_ID=$(aws apigatewayv2 create-integration \
        --api-id "$API_ID" \
        --integration-type AWS_PROXY \
        --integration-uri "$INTEGRATION_URI" \
        --payload-format-version "2.0" \
        --query IntegrationId \
        --output text)
    
    echo -e "${GREEN}✅ Lambda統合作成完了 (ID: $INTEGRATION_ID)${NC}"
else
    echo -e "${GREEN}✅ 既存のLambda統合を使用 (ID: $INTEGRATION_ID)${NC}"
fi

# ルートの作成/更新
echo -e "${YELLOW}10. ルートの設定...${NC}"

ROUTE_KEY='$default'
ROUTE_ID=$(aws apigatewayv2 get-routes --api-id "$API_ID" --query "Items[?RouteKey=='$ROUTE_KEY'].RouteId | [0]" --output text)

if [ "$ROUTE_ID" == "None" ] || [ -z "$ROUTE_ID" ]; then
    ROUTE_ID=$(aws apigatewayv2 create-route \
        --api-id "$API_ID" \
        --route-key "$ROUTE_KEY" \
        --target "integrations/$INTEGRATION_ID" \
        --query RouteId \
        --output text)
    
    echo -e "${GREEN}✅ ルート作成完了 (ID: $ROUTE_ID)${NC}"
else
    aws apigatewayv2 update-route \
        --api-id "$API_ID" \
        --route-id "$ROUTE_ID" \
        --target "integrations/$INTEGRATION_ID" \
        > /dev/null
    
    echo -e "${GREEN}✅ ルート更新完了 (ID: $ROUTE_ID)${NC}"
fi

# Lambda権限の設定（HTTP API用の正しいSourceArn形式）
echo -e "${YELLOW}11. Lambda権限の設定...${NC}"

STATEMENT_ID="apigateway-http-api-$ENVIRONMENT"
SOURCE_ARN="arn:aws:execute-api:$AWS_REGION:$ACCOUNT_ID:$API_ID/*/*"

# 既存の権限を削除（存在する場合）
aws lambda remove-permission \
    --function-name "$FUNCTION_NAME" \
    --statement-id "$STATEMENT_ID" \
    2>/dev/null || true

# 新しい権限を追加
aws lambda add-permission \
    --function-name "$FUNCTION_NAME" \
    --statement-id "$STATEMENT_ID" \
    --action lambda:InvokeFunction \
    --principal apigateway.amazonaws.com \
    --source-arn "$SOURCE_ARN" \
    > /dev/null

echo -e "${GREEN}✅ Lambda権限設定完了${NC}"

# CloudWatch Logsの設定
echo -e "${YELLOW}12. CloudWatch Logsの設定...${NC}"

LOG_GROUP_NAME="/aws/apigateway/$API_NAME"

# ロググループの作成
aws logs create-log-group --log-group-name "$LOG_GROUP_NAME" 2>/dev/null || echo "ロググループは既に存在します"

# API GatewayアクセスログIAMロールの確認/作成
API_GW_ROLE_NAME="apigateway-cloudwatch-logs"
if ! aws iam get-role --role-name "$API_GW_ROLE_NAME" &> /dev/null; then
    cat > /tmp/apigw-trust-policy.json <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Service": "apigateway.amazonaws.com"
      },
      "Action": "sts:AssumeRole"
    }
  ]
}
EOF
    
    aws iam create-role \
        --role-name "$API_GW_ROLE_NAME" \
        --assume-role-policy-document file:///tmp/apigw-trust-policy.json \
        > /dev/null
    
    aws iam attach-role-policy \
        --role-name "$API_GW_ROLE_NAME" \
        --policy-arn arn:aws:iam::aws:policy/service-role/AmazonAPIGatewayPushToCloudWatchLogs
fi

# アクセスログの有効化
LOG_ARN="arn:aws:logs:$AWS_REGION:$ACCOUNT_ID:log-group:$LOG_GROUP_NAME:*"
LOG_FORMAT='$context.requestId $context.error.message $context.error.messageString $context.integrationErrorMessage $context.integration.status $context.integration.error $context.status $context.requestTime $context.path'

aws apigatewayv2 update-stage \
    --api-id "$API_ID" \
    --stage-name '$default' \
    --access-log-settings "DestinationArn=$LOG_ARN,Format=$LOG_FORMAT" \
    > /dev/null

echo -e "${GREEN}✅ CloudWatch Logs設定完了${NC}"

# デプロイ完了
API_ENDPOINT="https://$API_ID.execute-api.$AWS_REGION.amazonaws.com"

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}デプロイ完了！${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo "Lambda関数名: $FUNCTION_NAME"
echo "API Gateway ID: $API_ID"
echo "API エンドポイント: $API_ENDPOINT"
echo ""
echo "動作確認コマンド:"
echo "  curl $API_ENDPOINT/api/messages/"
echo ""
echo "ログ確認コマンド:"
echo "  aws logs tail /aws/lambda/$FUNCTION_NAME --follow"
echo "  aws logs tail $LOG_GROUP_NAME --follow"
echo ""
