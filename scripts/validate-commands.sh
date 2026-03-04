#!/bin/bash
# ========================================
# Script Name: validate-commands.sh
# Description: コマンド実行環境の検証スクリプト
# Author: PLAYER1-r7
# Created: 2026-03-04
# Version: 1.0.0
# ========================================
#
# Usage: ./scripts/validate-commands.sh [--fix] [--strict]
#
# Description:
#   よく使うコマンド・環境変数・ディレクトリ存在を検証
#   エラーが見つかった場合は詳細を表示＆ユーザーに対応方法を提案
#
# Options:
#   --fix      自動修正を試みる（python venv 作成など）
#   --strict   1つのエラーで終了（デフォルトは全チェック後に終了）
#
# Exit Codes:
#   0 - すべてのチェック成功
#   1 - 1つ以上のチェック失敗（--strict で即終了）
#
# ========================================

set -o pipefail

# 色定義
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# ログ変数
ERRORS=0
WARNINGS=0
FIXES_APPLIED=0
PROJECT_ROOT="${PROJECT_ROOT:-.}"

# オプション解析
AUTO_FIX=false
STRICT_MODE=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --fix)
            AUTO_FIX=true
            shift
            ;;
        --strict)
            STRICT_MODE=true
            shift
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

# ログ関数
log_error() {
    echo -e "${RED}❌ エラー: $1${NC}"
    ((ERRORS++))
    if [[ "$STRICT_MODE" == "true" ]]; then
        exit 1
    fi
}

log_warning() {
    echo -e "${YELLOW}⚠️  警告: $1${NC}"
    ((WARNINGS++))
}

log_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

log_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

log_fix() {
    echo -e "${GREEN}🔧 自動修正: $1${NC}"
    ((FIXES_APPLIED++))
}

# ========================================
# チェック関数
# ========================================

check_directory_structure() {
    echo ""
    echo "🔍 [1] ディレクトリ構造をチェック..."

    local required_dirs=(
        "services/api"
        "services/frontend_react"
        "infrastructure/pulumi/aws"
        "infrastructure/pulumi/azure"
        "infrastructure/pulumi/gcp"
        "scripts"
        "docs"
        "static-site"
    )

    for dir in "${required_dirs[@]}"; do
        if [[ ! -d "$PROJECT_ROOT/$dir" ]]; then
            log_error "ディレクトリ '$dir' が見つかりません"
            log_info "正しいパス: $PROJECT_ROOT/$dir"
        else
            log_success "ディレクトリ '$dir' が存在します"
        fi
    done
}

check_node_installation() {
    echo ""
    echo "🔍 [2] Node.js 環境をチェック..."

    if ! command -v node &> /dev/null; then
        log_error "Node.js がインストールされていません"
        log_info "インストール: https://nodejs.org/"
        return
    fi

    local node_version=$(node -v)
    log_success "Node.js $node_version がインストール済み"

    if ! command -v npm &> /dev/null; then
        log_error "npm がインストールされていません"
        return
    fi

    local npm_version=$(npm -v)
    log_success "npm $npm_version がインストール済み"
}

check_python_environment() {
    echo ""
    echo "🔍 [3] Python 環境をチェック..."

    if ! command -v python3 &> /dev/null; then
        log_error "Python 3 がインストールされていません"
        log_info "インストール: https://www.python.org/downloads/"
        return
    fi

    local python_version=$(python3 --version)
    log_success "Python $python_version がインストール済み"

    # Python の仮想環境を確認
    local api_venv="$PROJECT_ROOT/services/api/.venv"
    if [[ ! -d "$api_venv" ]]; then
        log_warning "API 仮想環境 ($api_venv) が見つかりません"

        if [[ "$AUTO_FIX" == "true" ]]; then
            log_fix "API 仮想環境を作成中..."
            cd "$PROJECT_ROOT/services/api"
            python3 -m venv .venv
            if [[ $? -eq 0 ]]; then
                log_success "API 仮想環境を作成しました"
                log_fix "次のコマンドを実行してください: source .venv/bin/activate"
            else
                log_error "API 仮想環境の作成に失敗しました"
            fi
            cd - > /dev/null
        else
            log_info "修正: make install または python3 -m venv services/api/.venv を実行してください"
        fi
    else
        log_success "API 仮想環境が存在します"
    fi
}

check_npm_packages() {
    echo ""
    echo "🔍 [4] npm パッケージをチェック..."

    local frontend_dir="$PROJECT_ROOT/services/frontend_react"

    if [[ ! -d "$frontend_dir/node_modules" ]]; then
        log_warning "React フロントエンド ($frontend_dir) の node_modules がインストールされていません"

        if [[ "$AUTO_FIX" == "true" ]]; then
            log_fix "npm パッケージをインストール中..."
            cd "$frontend_dir"
            npm ci
            if [[ $? -eq 0 ]]; then
                log_success "npm パッケージをインストールしました"
            else
                log_error "npm パッケージのインストールに失敗しました"
            fi
            cd - > /dev/null
        else
            log_info "修正: cd services/frontend_react && npm ci を実行してください"
        fi
    else
        log_success "React npm パッケージがインストール済み"
    fi
}

check_pip_packages() {
    echo ""
    echo "🔍 [5] pip パッケージをチェック..."

    local api_dir="$PROJECT_ROOT/services/api"
    local venv_python="$api_dir/.venv/bin/python3"

    if [[ ! -f "$venv_python" ]]; then
        log_warning "API 仮想環境が有効な状態で pip パッケージをチェックできません"
        return
    fi

    # venv を有効化
    source "$api_dir/.venv/bin/activate"

    # 必須パッケージ確認
    local required_packages=("fastapi" "pydantic" "pytest")
    for pkg in "${required_packages[@]}"; do
        if "$venv_python" -c "import $pkg" 2>/dev/null; then
            log_success "パッケージ '$pkg' がインストール済み"
        else
            log_warning "パッケージ '$pkg' がインストールされていません"

            if [[ "$AUTO_FIX" == "true" ]]; then
                log_fix "pip パッケージをインストール中..."
                pip install -r "$api_dir/requirements.txt" > /dev/null 2>&1
                if [[ $? -eq 0 ]]; then
                    log_success "pip パッケージをインストールしました"
                else
                    log_error "pip パッケージのインストールに失敗しました"
                fi
            else
                log_info "修正: cd services/api && pip install -r requirements.txt を実行してください"
            fi
        fi
    done

    deactivate
}

check_aws_cli() {
    echo ""
    echo "🔍 [6] AWS CLI をチェック..."

    if ! command -v aws &> /dev/null; then
        log_warning "AWS CLI がインストールされていません（AWS デプロイに必須）"
        log_info "インストール: https://aws.amazon.com/cli/"
        return
    fi

    local aws_version=$(aws --version)
    log_success "AWS CLI $aws_version がインストール済み"

    # AWS 認証確認
    if ! aws sts get-caller-identity &> /dev/null; then
        log_warning "AWS CLI が認証されていません"
        log_info "実行: aws configure"
    else
        log_success "AWS CLI が認証済み"
    fi
}

check_azure_cli() {
    echo ""
    echo "🔍 [7] Azure CLI をチェック..."

    if ! command -v az &> /dev/null; then
        log_warning "Azure CLI がインストールされていません（Azure デプロイに必須）"
        log_info "インストール: https://learn.microsoft.com/cli/azure/install-azure-cli"
        return
    fi

    local az_version=$(az --version | head -1)
    log_success "Azure CLI $az_version がインストール済み"

    # Azure 認証確認
    if ! az account show &> /dev/null; then
        log_warning "Azure CLI が認証されていません"
        log_info "実行: az login"
    else
        log_success "Azure CLI が認証済み"
    fi
}

check_gcloud_cli() {
    echo ""
    echo "🔍 [8] Google Cloud CLI をチェック..."

    if ! command -v gcloud &> /dev/null; then
        log_warning "Google Cloud CLI がインストールされていません（GCP デプロイに必須）"
        log_info "インストール: https://cloud.google.com/sdk/docs/install"
        return
    fi

    local gcloud_version=$(gcloud --version | head -1)
    log_success "Google Cloud CLI $gcloud_version がインストール済み"

    # GCP 認証確認
    if ! gcloud auth list &> /dev/null; then
        log_warning "Google Cloud CLI が認証されていません"
        log_info "実行: gcloud auth login"
    else
        log_success "Google Cloud CLI が認証済み"
    fi
}

check_docker() {
    echo ""
    echo "🔍 [9] Docker をチェック..."

    if ! command -v docker &> /dev/null; then
        log_warning "Docker がインストールされていません（ローカル開発に推奨）"
        log_info "インストール: https://www.docker.com/products/docker-desktop"
        return
    fi

    local docker_version=$(docker --version)
    log_success "Docker $docker_version がインストール済み"

    # Docker daemon 確認
    if ! docker ps &> /dev/null; then
        log_error "Docker daemon が起動していません"
        log_info "実行: docker daemon または Docker Desktop を起動してください"
    else
        log_success "Docker daemon が実行中"
    fi
}

check_git_config() {
    echo ""
    echo "🔍 [10] Git 設定をチェック..."

    if ! command -v git &> /dev/null; then
        log_error "Git がインストールされていません"
        return
    fi

    local git_version=$(git --version)
    log_success "Git $git_version がインストール済み"

    # git hooks 確認
    local hooks_path=$(git config core.hooksPath)
    if [[ "$hooks_path" != ".githooks" ]]; then
        log_warning "git hooks が設定されていません"
        log_info "実行: make hooks-install"
    else
        log_success "git hooks が設定済み"
    fi
}

# ========================================
# メイン処理
# ========================================

main() {
    echo "========================================"
    echo "🔧 コマンド実行環境検証ツール"
    echo "========================================"
    echo ""
    echo "プロジェクトルート: $PROJECT_ROOT"
    echo ""

    # ディレクトリ確認
    if [[ ! -d "$PROJECT_ROOT" ]]; then
        log_error "プロジェクトルート '$PROJECT_ROOT' が見つかりません"
        exit 1
    fi

    # チェック実行
    check_directory_structure
    check_node_installation
    check_python_environment
    check_npm_packages
    check_pip_packages
    check_aws_cli
    check_azure_cli
    check_gcloud_cli
    check_docker
    check_git_config

    # 結果表示
    echo ""
    echo "========================================"
    echo "📊 チェック結果"
    echo "========================================"
    echo -e "${GREEN}成功: ✅${NC}"
    echo -e "${YELLOW}警告: $WARNINGS${NC}"
    echo -e "${RED}エラー: $ERRORS${NC}"
    echo -e "${GREEN}自動修正適用: $FIXES_APPLIED${NC}"
    echo ""

    if [[ $ERRORS -gt 0 ]]; then
        echo -e "${RED}⚠️  $ERRORS 個のエラーが見つかりました${NC}"
        echo "詳細は上記のログを確認してください"
        echo ""
        echo "📚 ドキュメント参照："
        echo "  - コマンド使用法: docs/AI_AGENT_14_COMMAND_USAGE_AND_DIRECTORY_JA.md"
        echo "  - エラー報告: docs/AI_AGENT_ERROR_DOCUMENTATION_RULE.md"
        echo "  - トラブルシューティング: TROUBLESHOOTING.md"
        echo ""
        exit 1
    else
        echo -e "${GREEN}✅ すべてのチェックが成功しました！${NC}"
        exit 0
    fi
}

# スクリプト実行
main "$@"
