#!/bin/bash

# Lambda Layer ビルドスクリプト
# 依存関係をLayerに分離してLambda関数のサイズを削減

set -e

# カラー定義
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 設定
PROJECT_NAME="${PROJECT_NAME:-multicloud-auto-deploy}"
ENVIRONMENT="${ENVIRONMENT:-staging}"
LAYER_NAME="${LAYER_NAME:-${PROJECT_NAME}-${ENVIRONMENT}-dependencies}"

# ディレクトリ設定
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
API_DIR="$PROJECT_ROOT/services/api"
BUILD_DIR="$API_DIR/.build-layer"

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Lambda Layer ビルドスクリプト${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo "レイヤー名: $LAYER_NAME"
echo ""

# 前提条件チェック
echo -e "${YELLOW}1. 前提条件のチェック...${NC}"

if ! command -v python3 &> /dev/null; then
    echo -e "${RED}❌ Python3がインストールされていません${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Python3確認完了${NC}"

# ビルドディレクトリのクリーンアップ
echo -e "${YELLOW}2. ビルドディレクトリのクリーンアップ...${NC}"
rm -rf "$BUILD_DIR"
mkdir -p "$BUILD_DIR/python"
echo -e "${GREEN}✅ クリーンアップ完了${NC}"

# AWS用の最小限の依存関係をインストール
echo -e "${YELLOW}3. 依存関係のインストール...${NC}"

# requirements-layer.txt を使用（API dirから）
if [ -f "$API_DIR/requirements-layer.txt" ]; then
    echo "既存の requirements-layer.txt を使用します"
    cp "$API_DIR/requirements-layer.txt" "$BUILD_DIR/requirements-layer.txt"
else
    echo "requirements-layer.txt が見つかりません。デフォルト設定を使用します"
    # Lambda Layer requirements (AWS専用、boto3/botocore除外)
    cat > "$BUILD_DIR/requirements-layer.txt" <<EOF
# Type checking (Python 3.12 compatibility)
typing_extensions==4.12.2

# FastAPI Core
fastapi==0.115.0
pydantic==2.9.0
pydantic-settings==2.5.2

# Lambda adapter
mangum==0.17.0

# Auth
python-jose[cryptography]==3.3.0
pyjwt==2.9.0

# HTTP client
requests==2.32.3

# Note: boto3とbotocoreはLambdaランタイムに含まれているため除外
EOF
fi

echo "インストール対象の依存関係:"
cat "$BUILD_DIR/requirements-layer.txt"
echo ""

# Lambda Layerの構造に従ってインストール (python/ ディレクトリに配置)
pip3 install -r "$BUILD_DIR/requirements-layer.txt" \
    -t "$BUILD_DIR/python/" \
    --upgrade \
    --platform manylinux2014_x86_64 \
    --python-version 3.12 \
    --only-binary=:all: 2>&1 | tee /tmp/pip-install.log

# 不要なファイルを削除してサイズを削減
echo -e "${YELLOW}4. 不要なファイルの削除...${NC}"
cd "$BUILD_DIR/python"

# テストファイルとドキュメントを削除
find . -type d -name "tests" -o -name "test" -exec rm -rf {} + 2>/dev/null || true
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
find . -type f -name "*.pyc" -delete 2>/dev/null || true
find . -type f -name "*.pyo" -delete 2>/dev/null || true
find . -type f -name "*.dist-info" -exec rm -rf {} + 2>/dev/null || true

# .so ファイル以外の開発用ファイルを削除
find . -type f -name "*.c" -delete 2>/dev/null || true
find . -type f -name "*.h" -delete 2>/dev/null || true
find . -type f -name "*.txt" -delete 2>/dev/null || true
find . -type f -name "*.md" -delete 2>/dev/null || true
find . -type f -name "*.rst" -delete 2>/dev/null || true

echo -e "${GREEN}✅ クリーンアップ完了${NC}"

# ZIPパッケージの作成
echo -e "${YELLOW}5. ZIPパッケージの作成...${NC}"
cd "$BUILD_DIR"
zip -r9 ../lambda-layer.zip python/ > /dev/null
cd "$API_DIR"
LAYER_SIZE=$(du -h "$BUILD_DIR/../lambda-layer.zip" | cut -f1)
echo -e "${GREEN}✅ Layerパッケージ作成完了 (サイズ: $LAYER_SIZE)${NC}"

# サイズ確認
LAYER_SIZE_BYTES=$(stat -f%z "$BUILD_DIR/../lambda-layer.zip" 2>/dev/null || stat -c%s "$BUILD_DIR/../lambda-layer.zip")
LAYER_SIZE_MB=$((LAYER_SIZE_BYTES / 1024 / 1024))

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Layer ビルド完了${NC}"
echo -e "${GREEN}========================================${NC}"
echo "Layer ZIPパス: $BUILD_DIR/../lambda-layer.zip"
echo "Layer サイズ: ${LAYER_SIZE} (${LAYER_SIZE_MB}MB)"
echo ""

if [ $LAYER_SIZE_MB -gt 50 ]; then
    echo -e "${YELLOW}⚠️  警告: Layer サイズが50MBを超えています${NC}"
    echo "   Lambda Layerの最大サイズは250MB（解凍後）です"
else
    echo -e "${GREEN}✅ Layer サイズOK (50MB以下)${NC}"
fi

echo ""
echo "次のコマンドでLayerをデプロイできます:"
echo "  aws lambda publish-layer-version --layer-name $LAYER_NAME --zip-file fileb://$BUILD_DIR/../lambda-layer.zip --compatible-runtimes python3.12"
