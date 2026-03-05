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

# 現在のディレクトリを API ディレクトリとして使用（ワークフローから呼び出される想定）
# ワークフローでは cd services/{service-name} してから呼び出される
if [ -f "requirements.txt" ] || [ -f "requirements-layer.txt" ]; then
    API_DIR="$(pwd)"
else
    # フォールバック: services/sns-api を使用
    API_DIR="$PROJECT_ROOT/services/sns-api"
fi

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
# Type checking (Python 3.13 compatibility)
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
# Suppress non-critical warnings for cleaner CI/CD logs
pip3 install -r "$BUILD_DIR/requirements-layer.txt" \
    -t "$BUILD_DIR/python/" \
    --upgrade \
    --platform manylinux2014_x86_64 \
    --python-version 3.13 \
    --only-binary=:all: \
    --disable-pip-version-check \
    --quiet 2>&1 | tee /tmp/pip-install.log || { \
      echo -e "${RED}❌ pip install failed${NC}"; \
      cat /tmp/pip-install.log; \
      exit 1; \
    }

# 不要なファイルを削除してサイズを削減
echo -e "${YELLOW}4. 不要なファイルの削除...${NC}"
cd "$BUILD_DIR/python"

# テストファイルとドキュメントを削除
find . -type d \( -name "tests" -o -name "test" \) -exec rm -rf {} + 2>/dev/null || true
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
find . -type f -name "*.pyc" -delete 2>/dev/null || true
find . -type f -name "*.pyo" -delete 2>/dev/null || true

# .dist-info ディレクトリを削除 (metadata, RECORD, WHEEL, etc.)
find . -type d -name "*dist-info" -exec rm -rf {} + 2>/dev/null || true

# .data ディレクトリを削除
find . -type d -name "*.data" -exec rm -rf {} + 2>/dev/null || true

# 開発用ファイルを削除 (.so ファイル以外)
find . -type f -name "*.c" -delete 2>/dev/null || true
find . -type f -name "*.h" -delete 2>/dev/null || true
find . -type f -name "*.so.py" -delete 2>/dev/null || true
find . -type f -name "*.pyd" -delete 2>/dev/null || true

# ドキュメントを削除
find . -type f -name "*.txt" -delete 2>/dev/null || true
find . -type f -name "*.md" -delete 2>/dev/null || true
find . -type f -name "*.rst" -delete 2>/dev/null || true
find . -type f -name "LICENSE*" -delete 2>/dev/null || true
find . -type f -name "COPYING*" -delete 2>/dev/null || true

# top_level.txt などのメタデータファイルを削除
find . -type f \( -name "top_level.txt" -o -name "RECORD" -o -name "WHEEL" -o -name "METADATA" -o -name "entry_points.txt" \) -delete 2>/dev/null || true

echo -e "${GREEN}✅ クリーンアップ完了${NC}"

# ZIPパッケージの作成
echo -e "${YELLOW}5. ZIPパッケージの作成...${NC}"
cd "$BUILD_DIR"
zip -r9q ../lambda-layer.zip python/ || { \
  echo -e "${RED}❌ Failed to create ZIP file${NC}"; \
  exit 1; \
}
cd "$API_DIR"
LAYER_ZIP="$BUILD_DIR/../lambda-layer.zip"
if [ ! -f "$LAYER_ZIP" ]; then
  echo -e "${RED}❌ ZIP file not created: $LAYER_ZIP${NC}"
  exit 1
fi

LAYER_SIZE=$(du -h "$LAYER_ZIP" | cut -f1)
echo -e "${GREEN}✅ Layerパッケージ作成完了 (サイズ: $LAYER_SIZE)${NC}"

# サイズ確認 (Linux/macOS互換)
LAYER_SIZE_BYTES=$(stat -c%s "$LAYER_ZIP" 2>/dev/null || stat -f%z "$LAYER_ZIP" 2>/dev/null || du -b "$LAYER_ZIP" | cut -f1)
LAYER_SIZE_MB=$((LAYER_SIZE_BYTES / 1024 / 1024))

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Layer ビルド完了${NC}"
echo -e "${GREEN}========================================${NC}"
echo "Layer ZIPパス: $BUILD_DIR/../lambda-layer.zip"
echo "Layer サイズ: ${LAYER_SIZE} (${LAYER_SIZE_MB}MB)"
echo ""

if [ $LAYER_SIZE_MB -gt 50 ]; then
    echo -e "${YELLOW}⚠️  警告: Layer サイズが50MBを超えています（${LAYER_SIZE_MB}MB）${NC}"
    echo "   Lambda Layerの最大サイズは250MB（解凍後）です"
    echo -e "${YELLOW}   ⚠️  S3アップロードが必要になり、デプロイが遅くなります${NC}"
else
    echo -e "${GREEN}✅ Layer サイズOK (${LAYER_SIZE_MB}MB - 50MB以下)${NC}"
fi

# GitHub Actions環境での出力設定
if [ -n "$GITHUB_OUTPUT" ]; then
    echo "layer_size_mb=$LAYER_SIZE_MB" >> "$GITHUB_OUTPUT"
    echo "layer_zip_path=$LAYER_ZIP" >> "$GITHUB_OUTPUT"
fi

echo ""
echo "✨ Lambda Layer ビルド完了！"
