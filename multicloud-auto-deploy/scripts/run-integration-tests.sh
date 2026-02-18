#!/bin/bash
# ========================================
# Script Name: run-integration-tests.sh
# Description: Execute Python integration tests
# Author: GitHub Copilot
# Created: 2026-02-18
# Version: 1.0.0
# ========================================
#
# Usage: ./scripts/run-integration-tests.sh [OPTIONS]
#
# Description:
#   Executes Python pytest integration tests for all backend implementations.
#   Tests AWS, GCP, and Azure backends with mocked resources.
#
# Options:
#   -v, --verbose         Verbose output
#   -m, --markers MARKER  Run tests with specific marker (aws, gcp, azure, integration)
#   --coverage            Generate coverage report
#   -k EXPRESSION         Run tests matching expression
#   --endpoints           Test actual API endpoints (requires network)
#   -h, --help            Show this help message
#
# Examples:
#   ./scripts/run-integration-tests.sh
#   ./scripts/run-integration-tests.sh -v
#   ./scripts/run-integration-tests.sh -m aws
#   ./scripts/run-integration-tests.sh --endpoints
#   ./scripts/run-integration-tests.sh -k "test_create_post"
#
# Prerequisites:
#   - Python 3.12+
#   - pytest installed
#   - pytest-mock installed (for mocking)
#   - requests installed (for endpoint tests)
#
# ========================================

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Default options
VERBOSE=""
MARKERS=""
COVERAGE=""
EXPRESSION=""
TEST_ENDPOINTS=false
PYTEST_ARGS=""

# Show help
show_help() {
    cat << EOF
使用方法: $0 [OPTIONS]

Python統合テストを実行します。

オプション:
    -v, --verbose          詳細な出力を表示
    -m, --markers MARKER   特定のマーカーでテストを実行 (aws, gcp, azure, integration)
    --coverage             カバレッジレポートを生成
    -k EXPRESSION          特定の<br/>のテストを実行
    --endpoints            実際のAPIエンドポイントをテスト（ネットワーク必須）
    -h, --help             このヘルプメッセージを表示

例:
    $0                              # 全てのユニット/統合テストを実行
    $0 -v                           # 詳細出力で実行
    $0 -m aws                       # AWSバックエンドのみテスト
    $0 --endpoints                  # 実際のAPIエンドポイントをテスト
    $0 -k "test_create_post"        # 特定のテストのみ実行
    $0 --coverage                   # カバレッジ付きで実行

マーカー:
    aws                    AWS backend tests
    gcp                    GCP backend tests
    azure                  Azure backend tests
    integration            Integration tests
    unit                   Unit tests
    slow                   Slow-running tests
    requires_network       Network-dependent tests
    requires_credentials   Credential-dependent tests

EOF
}

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -v|--verbose)
            VERBOSE="-vv"
            shift
            ;;
        -m|--markers)
            MARKERS="-m $2"
            shift 2
            ;;
        --coverage)
            COVERAGE="--cov=app --cov-report=html --cov-report=term"
            shift
            ;;
        -k)
            EXPRESSION="-k $2"
            shift 2
            ;;
        --endpoints)
            TEST_ENDPOINTS=true
            shift
            ;;
        -h|--help)
            show_help
            exit 0
            ;;
        *)
            echo -e "${RED}エラー: 不明なオプション: $1${NC}"
            show_help
            exit 1
            ;;
    esac
done

# Navigate to API directory
cd "$(dirname "$0")/../services/api" || exit 1

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Python統合テスト実行${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Check if pytest is installed
if ! command -v pytest &> /dev/null; then
    echo -e "${RED}エラー: pytest がインストールされていません${NC}"
    echo "インストールコマンド: pip install pytest pytest-mock pytest-asyncio"
    exit 1
fi

# Check Python version
PYTHON_VERSION=$(python --version 2>&1 | awk '{print $2}')
echo "Python: $PYTHON_VERSION"
echo "pytest: $(pytest --version 2>&1 | head -n 1)"
echo ""

# Build pytest command
PYTEST_CMD="pytest tests/"

if [ -n "$VERBOSE" ]; then
    PYTEST_CMD="$PYTEST_CMD $VERBOSE"
fi

if [ -n "$MARKERS" ]; then
    PYTEST_CMD="$PYTEST_CMD $MARKERS"
    echo -e "${YELLOW}マーカー: $MARKERS${NC}"
fi

if [ -n "$COVERAGE" ]; then
    PYTEST_CMD="$PYTEST_CMD $COVERAGE"
    echo -e "${YELLOW}カバレッジ: 有効${NC}"
fi

if [ -n "$EXPRESSION" ]; then
    PYTEST_CMD="$PYTEST_CMD $EXPRESSION"
    echo -e "${YELLOW}フィルター: $EXPRESSION${NC}"
fi

if [ "$TEST_ENDPOINTS" = true ]; then
    PYTEST_CMD="$PYTEST_CMD -m requires_network"
    echo -e "${YELLOW}エンドポイントテスト: 有効${NC}"
    echo ""
    echo -e "${YELLOW}環境変数:${NC}"
    echo "  AWS_API_ENDPOINT=${AWS_API_ENDPOINT:-未設定}"
    echo "  GCP_API_ENDPOINT=${GCP_API_ENDPOINT:-未設定}"
    echo "  AZURE_API_ENDPOINT=${AZURE_API_ENDPOINT:-未設定}"
else
    # Exclude network tests by default
    if [ -z "$MARKERS" ]; then
        PYTEST_CMD="$PYTEST_CMD -m 'not requires_network and not requires_credentials'"
    fi
fi

echo ""
echo -e "${BLUE}実行コマンド:${NC}"
echo "$PYTEST_CMD"
echo ""

# Execute tests
if eval "$PYTEST_CMD"; then
    echo ""
    echo -e "${GREEN}========================================${NC}"
    echo -e "${GREEN}✅ 全てのテストが成功しました！${NC}"
    echo -e "${GREEN}========================================${NC}"
    
    # Show coverage report location if generated
    if [ -n "$COVERAGE" ]; then
        echo ""
        echo -e "${BLUE}カバレッジレポート: htmlcov/index.html${NC}"
    fi
    
    exit 0
else
    echo ""
    echo -e "${RED}========================================${NC}"
    echo -e "${RED}❌ 一部のテストが失敗しました${NC}"
    echo -e "${RED}========================================${NC}"
    exit 1
fi
