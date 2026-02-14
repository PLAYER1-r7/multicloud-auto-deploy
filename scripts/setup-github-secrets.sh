#!/bin/bash
# GitHub Secrets設定ガイド生成スクリプト

set -e

# カラー定義
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  GitHub Secrets Setup Guide${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""
echo "このスクリプトは GitHub Secrets の設定手順を表示します。"
echo ""

# 設定場所の説明
echo -e "${CYAN}📍 設定場所:${NC}"
echo "1. GitHubリポジトリのページを開く"
echo "2. Settings → Secrets and variables → Actions"
echo "3. 'New repository secret' をクリック"
echo ""

print_secret_section() {
    local cloud=$1
    echo -e "${BLUE}========================================${NC}"
    echo -e "${BLUE}  ${cloud}${NC}"
    echo -e "${BLUE}========================================${NC}"
    echo ""
}

print_secret() {
    local name=$1
    local description=$2
    local example=$3
    
    echo -e "${YELLOW}Secret Name:${NC} ${GREEN}${name}${NC}"
    echo -e "${CYAN}説明:${NC} $description"
    if [ -n "$example" ]; then
        echo -e "${CYAN}例:${NC} $example"
    fi
    echo ""
}

# AWS Secrets
print_secret_section "AWS Secrets"

print_secret \
    "AWS_ACCESS_KEY_ID" \
    "AWSアクセスキーID" \
    "AKIAIOSFODNN7EXAMPLE"

print_secret \
    "AWS_SECRET_ACCESS_KEY" \
    "AWSシークレットアクセスキー" \
    "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"

echo -e "${CYAN}取得方法:${NC}"
echo "aws iam create-access-key --user-name YOUR_USER"
echo ""
echo -e "${CYAN}必要な権限:${NC}"
echo "- AmazonAPIGatewayAdministrator"
echo "- AWSLambda_FullAccess"
echo "- AmazonS3FullAccess"
echo "- CloudFrontFullAccess"
echo "- AmazonDynamoDBFullAccess"
echo ""
echo "---"
echo ""

# Azure Secrets
print_secret_section "Azure Secrets"

print_secret \
    "ARM_CLIENT_ID" \
    "Service Principal のアプリケーションID" \
    "12345678-1234-1234-1234-123456789abc"

print_secret \
    "ARM_CLIENT_SECRET" \
    "Service Principal のクライアントシークレット" \
    "abcdefghijklmnopqrstuvwxyz123456789"

print_secret \
    "ARM_SUBSCRIPTION_ID" \
    "AzureサブスクリプションID" \
    "12345678-1234-1234-1234-123456789abc"

print_secret \
    "ARM_TENANT_ID" \
    "Azure AD テナントID" \
    "12345678-1234-1234-1234-123456789abc"

echo -e "${CYAN}取得方法:${NC}"
echo "# Service Principalの作成"
echo "az ad sp create-for-rbac --name github-actions-deploy --role Contributor --scopes /subscriptions/YOUR_SUBSCRIPTION_ID"
echo ""
echo "# 出力から以下を取得:"
echo "# - appId → ARM_CLIENT_ID"
echo "# - password → ARM_CLIENT_SECRET"
echo "# - tenant → ARM_TENANT_ID"
echo ""
echo -e "${CYAN}必要なロール:${NC}"
echo "- Contributor (リソースグループまたはサブスクリプションレベル)"
echo ""
echo "---"
echo ""

# GCP Secrets
print_secret_section "GCP Secrets"

print_secret \
    "GCP_PROJECT_ID" \
    "GCPプロジェクトID" \
    "my-project-123456"

print_secret \
    "GCP_CREDENTIALS" \
    "Service Accountのキー（JSON形式全体）" \
    '{"type":"service_account","project_id":"..."}'

echo -e "${CYAN}取得方法:${NC}"
echo "# Service Accountの作成"
echo "gcloud iam service-accounts create github-actions-deploy --display-name=\"GitHub Actions Deploy\""
echo ""
echo "# キーの作成"
echo "gcloud iam service-accounts keys create gcp-key.json --iam-account=github-actions-deploy@PROJECT_ID.iam.gserviceaccount.com"
echo ""
echo "# 権限の付与"
echo "gcloud projects add-iam-policy-binding PROJECT_ID --member=\"serviceAccount:github-actions-deploy@PROJECT_ID.iam.gserviceaccount.com\" --role=\"roles/editor\""
echo "gcloud projects add-iam-policy-binding PROJECT_ID --member=\"serviceAccount:github-actions-deploy@PROJECT_ID.iam.gserviceaccount.com\" --role=\"roles/datastore.owner\""
echo "gcloud projects add-iam-policy-binding PROJECT_ID --member=\"serviceAccount:github-actions-deploy@PROJECT_ID.iam.gserviceaccount.com\" --role=\"roles/run.admin\""
echo ""
echo "# GCS Bucket への権限"
echo "gcloud storage buckets add-iam-policy-binding gs://multicloud-auto-deploy-tfstate-gcp --member=\"serviceAccount:github-actions-deploy@PROJECT_ID.iam.gserviceaccount.com\" --role=\"roles/storage.objectAdmin\""
echo ""
echo -e "${CYAN}GitHub Secretsへの設定:${NC}"
echo "cat gcp-key.json | pbcopy  # macOS"
echo "cat gcp-key.json | xclip -selection clipboard  # Linux"
echo "# JSON全体をコピーしてGitHub SecretsのGCP_CREDENTIALSに貼り付け"
echo ""
echo "---"
echo ""

# デプロイテスト
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  設定後のテスト${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""
echo "すべてのSecretsを設定したら:"
echo ""
echo "1. GitHub リポジトリの Actions タブを開く"
echo "2. 各ワークフロー（deploy-aws.yml, deploy-azure.yml, deploy-gcp.yml）を選択"
echo "3. 'Run workflow' をクリックして手動実行"
echo "4. environment: staging を選択して実行"
echo ""
echo -e "${GREEN}✓ すべてのワークフローが成功すれば設定完了です！${NC}"
echo ""

# オプション: 現在の値を確認（ローカル）
if [ "$1" = "--check-local" ]; then
    echo -e "${BLUE}========================================${NC}"
    echo -e "${BLUE}  ローカル環境変数チェック${NC}"
    echo -e "${BLUE}========================================${NC}"
    echo ""
    
    check_env() {
        local var_name=$1
        if [ -n "${!var_name}" ]; then
            echo -e "${GREEN}✓${NC} $var_name: 設定済み"
        else
            echo -e "${RED}✗${NC} $var_name: 未設定"
        fi
    }
    
    echo "AWS:"
    check_env "AWS_ACCESS_KEY_ID"
    check_env "AWS_SECRET_ACCESS_KEY"
    echo ""
    
    echo "Azure:"
    check_env "ARM_CLIENT_ID"
    check_env "ARM_CLIENT_SECRET"
    check_env "ARM_SUBSCRIPTION_ID"
    check_env "ARM_TENANT_ID"
    echo ""
    
    echo "GCP:"
    check_env "GCP_PROJECT_ID"
    check_env "GOOGLE_APPLICATION_CREDENTIALS"
    echo ""
fi

echo -e "${CYAN}💡 Tip:${NC}"
echo "このスクリプトの出力を保存しておくと便利です："
echo "  ./scripts/setup-github-secrets.sh > SECRETS_GUIDE.txt"
echo ""
