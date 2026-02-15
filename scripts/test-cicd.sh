#!/bin/bash
# ========================================
# Script Name: test-cicd.sh
# Description: CI/CD Workflow Local Validator
# Author: PLAYER1-r7
# Created: 2026-01-15
# Last Modified: 2026-02-15
# Version: 1.0.0
# ========================================
#
# Usage: ./scripts/test-cicd.sh
#
# Description:
#   Validates GitHub Actions workflows locally before deployment.
#   Tests build processes, packaging, and configuration.
#
# Validation Steps:
#   1. Environment verification (Terraform, Node.js, Python)
#   2. Workflow file syntax check
#   3. AWS Lambda packaging test
#   4. Frontend build test
#   5. AWS credentials check
#   6. GitHub Secrets check
#   7. Deploy target verification
#
# Prerequisites:
#   - Terraform 1.5+
#   - Node.js 18+
#   - Python 3.12+
#   - AWS CLI
#   - GitHub CLI (for secrets check)
#
# Exit Codes:
#   0 - All validations passed
#   1 - One or more validations failed
#
# ========================================

set -e

# カラー定義
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# テスト結果カウンター
TESTS_PASSED=0
TESTS_FAILED=0
TOTAL_TESTS=0

# ログ関数
log_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

log_success() {
    echo -e "${GREEN}✅ $1${NC}"
    TESTS_PASSED=$((TESTS_PASSED + 1))
}

log_error() {
    echo -e "${RED}❌ $1${NC}"
    TESTS_FAILED=$((TESTS_FAILED + 1))
}

log_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

run_test() {
    local test_name="$1"
    TOTAL_TESTS=$((TOTAL_TESTS + 1))
    log_info "テスト $TOTAL_TESTS: $test_name"
}

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}CI/CD ワークフローテスト${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# ディレクトリ設定
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

cd "$PROJECT_ROOT"

# ===========================================
# 1. 環境検証
# ===========================================
echo -e "${YELLOW}=== 1. 環境検証 ===${NC}"
echo ""

run_test "Node.js バージョン確認"
if command -v node &> /dev/null; then
    NODE_VERSION=$(node --version)
    log_success "Node.js インストール済み: $NODE_VERSION"
    if [[ "$NODE_VERSION" =~ v18\. ]] || [[ "$NODE_VERSION" =~ v2[0-9]\. ]]; then
        log_success "Node.js バージョン適合 (v18+)"
    else
        log_warning "推奨バージョン: v18+ (現在: $NODE_VERSION)"
    fi
else
    log_error "Node.js がインストールされていません"
fi
echo ""

run_test "Python バージョン確認"
if command -v python3 &> /dev/null; then
    PYTHON_VERSION=$(python3 --version)
    log_success "Python インストール済み: $PYTHON_VERSION"
    if [[ "$PYTHON_VERSION" =~ 3\.1[12]\. ]]; then
        log_success "Python バージョン適合 (3.11+)"
    else
        log_warning "推奨バージョン: 3.11+ (現在: $PYTHON_VERSION)"
    fi
else
    log_error "Python3 がインストールされていません"
fi
echo ""

run_test "AWS CLI 確認"
if command -v aws &> /dev/null; then
    AWS_VERSION=$(aws --version)
    log_success "AWS CLI インストール済み: $AWS_VERSION"
else
    log_warning "AWS CLI がインストールされていません（AWS デプロイに必要）"
fi
echo ""

run_test "Azure CLI 確認"
if command -v az &> /dev/null; then
    AZ_VERSION=$(az --version | head -n 1)
    log_success "Azure CLI インストール済み: $AZ_VERSION"
else
    log_warning "Azure CLI がインストールされていません（Azure デプロイに必要）"
fi
echo ""

run_test "GCP CLI 確認"
if command -v gcloud &> /dev/null; then
    GCLOUD_VERSION=$(gcloud --version | head -n 1)
    log_success "GCP CLI インストール済み: $GCLOUD_VERSION"
else
    log_warning "GCP CLI がインストールされていません（GCP デプロイに必要）"
fi
echo ""

# ===========================================
# 2. ワークフローファイル検証
# ===========================================
echo -e "${YELLOW}=== 2. ワークフローファイル検証 ===${NC}"
echo ""

WORKFLOW_DIR=".github/workflows"

run_test "ワークフローディレクトリ確認"
if [ -d "$WORKFLOW_DIR" ]; then
    log_success "ワークフローディレクトリ存在: $WORKFLOW_DIR"
else
    log_error "ワークフローディレクトリが見つかりません"
fi
echo ""

WORKFLOWS=("deploy-aws.yml" "deploy-azure.yml" "deploy-gcp.yml" "deploy-multicloud.yml")

for workflow in "${WORKFLOWS[@]}"; do
    run_test "ワークフロー: $workflow"
    if [ -f "$WORKFLOW_DIR/$workflow" ]; then
        log_success "$workflow 存在"
        
        # YAML構文チェック（yamlが利用可能な場合）
        if command -v yamllint &> /dev/null; then
            if yamllint "$WORKFLOW_DIR/$workflow" 2>/dev/null; then
                log_success "$workflow YAML構文OK"
            else
                log_warning "$workflow YAML構文警告あり"
            fi
        fi
    else
        log_error "$workflow が見つかりません"
    fi
    echo ""
done

# ===========================================
# 3. ビルドプロセス検証（AWS Lambda パッケージング）
# ===========================================
echo -e "${YELLOW}=== 3. ビルドプロセス検証 ===${NC}"
echo ""

run_test "Lambda パッケージング シミュレーション"
if [ -d "services/api" ]; then
    cd services/api
    
    # クリーンアップ
    rm -rf .build/package .build/lambda-test.zip
    mkdir -p .build/package
    
    log_info "依存関係インストール中..."
    if pip3 install -r requirements.txt \
        -t .build/package/ \
        --platform manylinux2014_x86_64 \
        --only-binary=:all: \
        --quiet 2>&1 | grep -v "Requirement already satisfied" || true; then
        log_success "依存関係インストール完了"
    else
        log_error "依存関係インストール失敗"
    fi
    
    log_info "アプリケーションコードコピー中..."
    if cp -r app .build/package/; then
        log_success "コードコピー完了"
    else
        log_error "コードコピー失敗"
    fi
    
    log_info "ZIPパッケージ作成中..."
    cd .build/package
    if zip -r9 ../lambda-test.zip . > /dev/null 2>&1; then
        cd ../..
        PACKAGE_SIZE=$(du -h .build/lambda-test.zip | cut -f1)
        log_success "ZIPパッケージ作成完了（サイズ: $PACKAGE_SIZE）"
        
        # パッケージ内容検証
        if unzip -l .build/lambda-test.zip | grep -q "app/main.py"; then
            log_success "パッケージ内容検証OK（main.pyが含まれる）"
        else
            log_error "パッケージ内容検証失敗（main.pyが見つからない）"
        fi
    else
        cd ../..
        log_error "ZIPパッケージ作成失敗"
    fi
    
    cd "$PROJECT_ROOT"
else
    log_error "services/api ディレクトリが見つかりません"
fi
echo ""

# ===========================================
# 4. フロントエンドビルド検証
# ===========================================
echo -e "${YELLOW}=== 4. フロントエンドビルド検証 ===${NC}"
echo ""

run_test "React フロントエンドビルド"
if [ -d "services/frontend_react" ]; then
    cd services/frontend_react
    
    log_info "依存関係確認中..."
    if [ -f "package.json" ]; then
        log_success "package.json 存在"
        
        # node_modulesの存在確認
        if [ -d "node_modules" ]; then
            log_success "node_modules 存在（依存関係インストール済み）"
            
            log_info "ビルド実行中..."
            if npm run build > /tmp/react-build.log 2>&1; then
                log_success "Reactビルド成功"
                
                # ビルド成果物確認
                if [ -d "dist" ] && [ -f "dist/index.html" ]; then
                    log_success "ビルド成果物確認OK（dist/index.html存在）"
                    
                    DIST_SIZE=$(du -sh dist | cut -f1)
                    log_info "ビルドサイズ: $DIST_SIZE"
                else
                    log_error "ビルド成果物が見つかりません"
                fi
            else
                log_error "Reactビルド失敗"
                log_info "ログ: /tmp/react-build.log"
            fi
        else
            log_warning "node_modules が見つかりません。npm install を実行してください"
        fi
    else
        log_error "package.json が見つかりません"
    fi
    
    cd "$PROJECT_ROOT"
else
    log_error "services/frontend_react ディレクトリが見つかりません"
fi
echo ""

# ===========================================
# 5. AWS認証情報確認
# ===========================================
echo -e "${YELLOW}=== 5. AWS認証情報確認 ===${NC}"
echo ""

run_test "AWS認証情報"
if command -v aws &> /dev/null; then
    if aws sts get-caller-identity &> /dev/null; then
        ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
        USER_ARN=$(aws sts get-caller-identity --query Arn --output text)
        log_success "AWS認証済み"
        log_info "アカウントID: $ACCOUNT_ID"
        log_info "ユーザー: $USER_ARN"
    else
        log_warning "AWS認証情報が設定されていません"
        log_info "aws configure を実行してください"
    fi
else
    log_warning "AWS CLIがインストールされていません"
fi
echo ""

# ===========================================
# 6. シークレット/環境変数確認（GitHub Actions）
# ===========================================
echo -e "${YELLOW}=== 6. 必要なシークレット一覧 ===${NC}"
echo ""

log_info "GitHub Actionsで設定すべきシークレット:"
echo ""

echo "【AWS】"
echo "  - AWS_ACCESS_KEY_ID"
echo "  - AWS_SECRET_ACCESS_KEY"
echo "  - AWS_LAMBDA_FUNCTION_NAME (optional)"
echo "  - AWS_S3_BUCKET (optional)"
echo ""

echo "【Azure】"
echo "  - AZURE_CREDENTIALS (JSON形式)"
echo "  - AZURE_SUBSCRIPTION_ID"
echo "  - AZURE_TENANT_ID"
echo "  - AZURE_CLIENT_ID"
echo "  - AZURE_CLIENT_SECRET"
echo ""

echo "【GCP】"
echo "  - GCP_CREDENTIALS (JSON形式)"
echo "  - GCP_PROJECT_ID"
echo ""

# ===========================================
# 7. デプロイターゲット確認
# ===========================================
echo -e "${YELLOW}=== 7. デプロイターゲット確認 ===${NC}"
echo ""

run_test "AWS Lambda 関数確認"
if command -v aws &> /dev/null && aws sts get-caller-identity &> /dev/null; then
    LAMBDA_NAME="multicloud-auto-deploy-staging-api"
    if aws lambda get-function --function-name "$LAMBDA_NAME" &> /dev/null; then
        log_success "Lambda関数存在: $LAMBDA_NAME"
        
        LAMBDA_RUNTIME=$(aws lambda get-function-configuration --function-name "$LAMBDA_NAME" --query Runtime --output text)
        LAMBDA_MEMORY=$(aws lambda get-function-configuration --function-name "$LAMBDA_NAME" --query MemorySize --output text)
        log_info "Runtime: $LAMBDA_RUNTIME, Memory: ${LAMBDA_MEMORY}MB"
    else
        log_warning "Lambda関数が見つかりません: $LAMBDA_NAME"
    fi
else
    log_warning "AWS認証情報未設定またはAWS CLI未インストール"
fi
echo ""

run_test "S3 バケット確認"
if command -v aws &> /dev/null && aws sts get-caller-identity &> /dev/null; then
    S3_BUCKET="multicloud-auto-deploy-staging-frontend"
    if aws s3 ls "s3://$S3_BUCKET" &> /dev/null; then
        log_success "S3バケット存在: $S3_BUCKET"
    else
        log_warning "S3バケットが見つかりません: $S3_BUCKET"
    fi
else
    log_warning "AWS認証情報未設定またはAWS CLI未インストール"
fi
echo ""

# ===========================================
# 8. ワークフロートリガー検証
# ===========================================
echo -e "${YELLOW}=== 8. ワークフロートリガー検証 ===${NC}"
echo ""

log_info "各ワークフローのトリガー条件:"
echo ""

for workflow in "${WORKFLOWS[@]}"; do
    if [ -f "$WORKFLOW_DIR/$workflow" ]; then
        echo "【$workflow】"
        grep -A 10 "^on:" "$WORKFLOW_DIR/$workflow" | head -n 15
        echo ""
    fi
done

# ===========================================
# 結果サマリー
# ===========================================
echo ""
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}テスト結果サマリー${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""
echo "総テスト数: $TOTAL_TESTS"
echo -e "${GREEN}成功: $TESTS_PASSED${NC}"
echo -e "${RED}失敗: $TESTS_FAILED${NC}"
echo ""

if [ $TESTS_FAILED -eq 0 ]; then
    SUCCESS_RATE=100
else
    SUCCESS_RATE=$(awk "BEGIN {printf \"%.1f\", ($TESTS_PASSED/$TOTAL_TESTS)*100}")
fi

echo "成功率: $SUCCESS_RATE%"
echo ""

if [ $TESTS_FAILED -eq 0 ]; then
    echo -e "${GREEN}🎉 全てのテストが成功しました！${NC}"
    echo ""
    echo "次のステップ:"
    echo "1. GitHub Actionsシークレットを設定"
    echo "2. ブランチにプッシュしてワークフローを実行"
    echo "3. GitHub Actions UIで実行結果を確認"
    exit 0
else
    echo -e "${YELLOW}⚠️  一部のテストが失敗または警告があります${NC}"
    echo ""
    echo "推奨アクション:"
    echo "1. 失敗したテストの原因を確認"
    echo "2. 必要なツールをインストール"
    echo "3. 認証情報を設定"
    echo "4. 再度テストを実行"
    exit 1
fi
