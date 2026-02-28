#!/bin/bash

# ========================================
# Script Name: generate-source-code-pdf.sh
# Description: Generate comprehensive PDF with documentation AND full source code
# Author: PLAYER1-r7
# Created: 2026-02-28
# Version: 1.0.0
# ========================================
#
# Usage: ./scripts/generate-source-code-pdf.sh [output_filename]
#
# Parameters:
#   output_filename (optional) : Name of the output PDF file (default: multicloud-complete-source-code.pdf)
#
# Examples:
#   ./scripts/generate-source-code-pdf.sh
#   ./scripts/generate-source-code-pdf.sh complete-guide.pdf
#
# Prerequisites:
#   - pandoc (for Markdown to PDF conversion)
#   - texlive-xetex (LaTeX engine for PDF generation)
#   - texlive-lang-cjk (CJK fonts for Japanese)
#   - fonts-noto-cjk (Noto CJK fonts)
#
# Exit Codes:
#   0 : Success
#   1 : pandoc not found
#   2 : Source files not found
#   3 : PDF generation failed
# ========================================

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OUTPUT_FILE="${1:-multicloud-complete-source-code.pdf}"
TEMP_DIR=$(mktemp -d)
MERGED_MD="$TEMP_DIR/merged-complete.md"

# Check if pandoc is installed
if ! command -v pandoc &> /dev/null; then
    echo -e "${RED}✗ Error: pandoc is not installed${NC}"
    echo "Install with: sudo apt-get install pandoc texlive-xetex texlive-lang-cjk fonts-noto-cjk"
    exit 1
fi

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  完全版PDF生成中（解説書 + ソースコード）${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Create temporary merged Markdown file with Japanese metadata
cat > "$MERGED_MD" << 'HEADER'
---
title: "マルチクラウド自動デプロイプラットフォーム"
subtitle: "完全版ソースコード解説書（ソースコード全文付き）"
author: "PLAYER1-r7"
date: "2026年2月28日"
geometry: margin=2cm
fontsize: 10pt
documentclass: report
toc: true
toc-depth: 3
numbersections: true
colorlinks: true
linkcolor: blue
urlcolor: blue
---

\newpage

HEADER

echo -e "${YELLOW}📝 ドキュメントをマージ中...${NC}"

# Function to add chapter to merged file
add_chapter() {
    local file=$1
    local title=$2

    if [ -f "$file" ]; then
        echo -e "${GREEN}  ✓ 追加: $title${NC}"
        echo "" >> "$MERGED_MD"
        echo "# $title" >> "$MERGED_MD"
        echo "" >> "$MERGED_MD"

        # Remove first heading and add content
        tail -n +2 "$file" | sed '/^#/,1d' >> "$MERGED_MD"
        echo "" >> "$MERGED_MD"
        echo '\newpage' >> "$MERGED_MD"
        echo "" >> "$MERGED_MD"
    else
        echo -e "${YELLOW}  ⚠ 警告: $file が見つかりません${NC}"
    fi
}

# Function to add source code file
add_source_file() {
    local file=$1
    local title=$2
    local lang=${3:-python}

    if [ -f "$file" ]; then
        echo -e "${GREEN}  ✓ 追加: $title${NC}"
        echo "" >> "$MERGED_MD"
        echo "## $title" >> "$MERGED_MD"
        echo "" >> "$MERGED_MD"
        echo "\`\`\`$lang" >> "$MERGED_MD"
        cat "$file" >> "$MERGED_MD"
        echo "" >> "$MERGED_MD"
        echo "\`\`\`" >> "$MERGED_MD"
        echo "" >> "$MERGED_MD"
    else
        echo -e "${YELLOW}  ⚠ 警告: $file が見つかりません${NC}"
    fi
}

# ============================================================
# Part 1: 解説ドキュメント
# ============================================================
echo -e "\n${BLUE}Part 1: プロジェクト概要と解説書${NC}"
add_chapter "$PROJECT_ROOT/README.md" "プロジェクト概要"
add_chapter "$PROJECT_ROOT/docs/IMPLEMENTATION_GUIDE.md" "ソース実装解説書"
add_chapter "$PROJECT_ROOT/docs/SOURCE_CODE_GUIDE.md" "インフラ・CI/CD解説書"

# ============================================================
# Part 2: バックエンドAPI ソースコード
# ============================================================
echo -e "\n${BLUE}Part 2: バックエンドAPI ソースコード${NC}"

cat >> "$MERGED_MD" << 'SECTION'

# バックエンドAPI ソースコード

このセクションでは、FastAPIベースのバックエンドAPIのソースコード全文を掲載します。

SECTION

echo -e "\n${BLUE}  2.1 コアファイル${NC}"
add_source_file "$PROJECT_ROOT/services/api/app/main.py" "main.py - FastAPIアプリケーション" "python"
add_source_file "$PROJECT_ROOT/services/api/app/config.py" "config.py - 環境設定" "python"
add_source_file "$PROJECT_ROOT/services/api/app/models.py" "models.py - データモデル" "python"
add_source_file "$PROJECT_ROOT/services/api/app/auth.py" "auth.py - 認証ミドルウェア" "python"
add_source_file "$PROJECT_ROOT/services/api/app/jwt_verifier.py" "jwt_verifier.py - JWT検証" "python"

echo -e "\n${BLUE}  2.2 バックエンド実装${NC}"
add_source_file "$PROJECT_ROOT/services/api/app/backends/base.py" "backends/base.py - 抽象基底クラス" "python"
add_source_file "$PROJECT_ROOT/services/api/app/backends/aws_backend.py" "backends/aws_backend.py - AWS実装" "python"
add_source_file "$PROJECT_ROOT/services/api/app/backends/azure_backend.py" "backends/azure_backend.py - Azure実装" "python"
add_source_file "$PROJECT_ROOT/services/api/app/backends/gcp_backend.py" "backends/gcp_backend.py - GCP実装" "python"
add_source_file "$PROJECT_ROOT/services/api/app/backends/local_backend.py" "backends/local_backend.py - ローカル実装" "python"

echo -e "\n${BLUE}  2.3 APIルート${NC}"
add_source_file "$PROJECT_ROOT/services/api/app/routes/posts.py" "routes/posts.py - 投稿API" "python"
add_source_file "$PROJECT_ROOT/services/api/app/routes/profile.py" "routes/profile.py - プロフィールAPI" "python"
add_source_file "$PROJECT_ROOT/services/api/app/routes/uploads.py" "routes/uploads.py - アップロードAPI" "python"

echo -e "\n${BLUE}  2.4 クラウド別エントリーポイント${NC}"
add_source_file "$PROJECT_ROOT/services/api/index.py" "index.py - AWS Lambda ハンドラー" "python"
add_source_file "$PROJECT_ROOT/services/api/function_app.py" "function_app.py - Azure Functions ハンドラー" "python"
add_source_file "$PROJECT_ROOT/services/api/function.py" "function.py - GCP Cloud Run ハンドラー" "python"

# ============================================================
# Part 3: インフラストラクチャコード (Pulumi)
# ============================================================
echo -e "\n${BLUE}Part 3: インフラストラクチャコード (Pulumi)${NC}"

cat >> "$MERGED_MD" << 'SECTION'

# インフラストラクチャコード (Pulumi)

このセクションでは、Pulumi Pythonを使用したIaCコードを掲載します。

SECTION

echo -e "\n${BLUE}  3.1 AWS インフラ${NC}"
add_source_file "$PROJECT_ROOT/infrastructure/pulumi/aws/__main__.py" "AWS Pulumi __main__.py" "python"
add_source_file "$PROJECT_ROOT/infrastructure/pulumi/aws/Pulumi.staging.yaml" "AWS Pulumi.staging.yaml" "yaml"

echo -e "\n${BLUE}  3.2 Azure インフラ${NC}"
add_source_file "$PROJECT_ROOT/infrastructure/pulumi/azure/__main__.py" "Azure Pulumi __main__.py" "python"
add_source_file "$PROJECT_ROOT/infrastructure/pulumi/azure/Pulumi.staging.yaml" "Azure Pulumi.staging.yaml" "yaml"

echo -e "\n${BLUE}  3.3 GCP インフラ${NC}"
add_source_file "$PROJECT_ROOT/infrastructure/pulumi/gcp/__main__.py" "GCP Pulumi __main__.py" "python"
add_source_file "$PROJECT_ROOT/infrastructure/pulumi/gcp/Pulumi.staging.yaml" "GCP Pulumi.staging.yaml" "yaml"

# ============================================================
# Part 4: CI/CDワークフロー
# ============================================================
echo -e "\n${BLUE}Part 4: CI/CDワークフロー (GitHub Actions)${NC}"

cat >> "$MERGED_MD" << 'SECTION'

# CI/CDワークフロー (GitHub Actions)

このセクションでは、GitHub Actionsワークフローファイルを掲載します。

SECTION

add_source_file "$PROJECT_ROOT/.github/workflows/deploy-aws.yml" "deploy-aws.yml - AWS デプロイ" "yaml"
add_source_file "$PROJECT_ROOT/.github/workflows/deploy-azure.yml" "deploy-azure.yml - Azure デプロイ" "yaml"
add_source_file "$PROJECT_ROOT/.github/workflows/deploy-gcp.yml" "deploy-gcp.yml - GCP デプロイ" "yaml"
add_source_file "$PROJECT_ROOT/.github/workflows/deploy-react-spa.yml" "deploy-react-spa.yml - React SPA デプロイ" "yaml"
add_source_file "$PROJECT_ROOT/.github/workflows/test.yml" "test.yml - テストワークフロー" "yaml"

# ============================================================
# Part 5: フロントエンド (React) 主要コード
# ============================================================
echo -e "\n${BLUE}Part 5: フロントエンド (React) 主要コード${NC}"

cat >> "$MERGED_MD" << 'SECTION'

# フロントエンド (React) 主要コード

このセクションでは、React + TypeScript + Viteベースのフロントエンドの主要ファイルを掲載します。

SECTION

echo -e "\n${BLUE}  5.1 コアファイル${NC}"
add_source_file "$PROJECT_ROOT/services/frontend_react/src/App.tsx" "App.tsx - メインアプリケーション" "typescript"
add_source_file "$PROJECT_ROOT/services/frontend_react/src/main.tsx" "main.tsx - エントリーポイント" "typescript"
add_source_file "$PROJECT_ROOT/services/frontend_react/src/contexts/AuthContext.tsx" "AuthContext.tsx - 認証コンテキスト" "typescript"

echo -e "\n${BLUE}  5.2 API クライアント${NC}"
add_source_file "$PROJECT_ROOT/services/frontend_react/src/api/client.ts" "api/client.ts - APIクライアント" "typescript"
add_source_file "$PROJECT_ROOT/services/frontend_react/src/api/posts.ts" "api/posts.ts - 投稿API" "typescript"

echo -e "\n${BLUE}  5.3 主要ページコンポーネント${NC}"
add_source_file "$PROJECT_ROOT/services/frontend_react/src/pages/Home.tsx" "pages/Home.tsx - ホームページ" "typescript"
add_source_file "$PROJECT_ROOT/services/frontend_react/src/pages/Feed.tsx" "pages/Feed.tsx - フィードページ" "typescript"
add_source_file "$PROJECT_ROOT/services/frontend_react/src/pages/Profile.tsx" "pages/Profile.tsx - プロフィールページ" "typescript"

echo -e "\n${BLUE}  5.4 設定ファイル${NC}"
add_source_file "$PROJECT_ROOT/services/frontend_react/vite.config.ts" "vite.config.ts - Vite設定" "typescript"
add_source_file "$PROJECT_ROOT/services/frontend_react/tsconfig.json" "tsconfig.json - TypeScript設定" "json"
add_source_file "$PROJECT_ROOT/services/frontend_react/package.json" "package.json - パッケージ設定" "json"

# ============================================================
# Part 6: スクリプト
# ============================================================
echo -e "\n${BLUE}Part 6: スクリプト${NC}"

cat >> "$MERGED_MD" << 'SECTION'

# スクリプト

このセクションでは、デプロイやテストに使用される主要なスクリプトを掲載します。

SECTION

add_source_file "$PROJECT_ROOT/scripts/build-lambda-layer.sh" "build-lambda-layer.sh - Lambda Layer ビルド" "bash"
add_source_file "$PROJECT_ROOT/scripts/deploy-aws.sh" "deploy-aws.sh - AWS デプロイスクリプト" "bash"
add_source_file "$PROJECT_ROOT/scripts/deploy-azure.sh" "deploy-azure.sh - Azure デプロイスクリプト" "bash"
add_source_file "$PROJECT_ROOT/scripts/deploy-gcp.sh" "deploy-gcp.sh - GCP デプロイスクリプト" "bash"
add_source_file "$PROJECT_ROOT/scripts/test-e2e.sh" "test-e2e.sh - E2Eテスト" "bash"
add_source_file "$PROJECT_ROOT/scripts/cloud_architecture_mapper.py" "cloud_architecture_mapper.py - アーキテクチャマッパー" "python"

# ============================================================
# Part 7: 設定ファイル
# ============================================================
echo -e "\n${BLUE}Part 7: 設定ファイル${NC}"

cat >> "$MERGED_MD" << 'SECTION'

# 設定ファイル

このセクションでは、プロジェクト全体の主要な設定ファイルを掲載します。

SECTION

add_source_file "$PROJECT_ROOT/docker-compose.yml" "docker-compose.yml - ローカル開発環境" "yaml"
add_source_file "$PROJECT_ROOT/Makefile" "Makefile - ビルドタスク" "makefile"
add_source_file "$PROJECT_ROOT/.gitignore" ".gitignore - Git除外設定" "text"

echo ""
echo -e "${YELLOW}🔧 PDF生成中（これには数分かかる場合があります）...${NC}"
echo ""

# Check if LaTeX header exists
LATEX_HEADER="$PROJECT_ROOT/scripts/latex-header.tex"
if [ ! -f "$LATEX_HEADER" ]; then
    echo -e "${RED}✗ Error: LaTeX header not found at $LATEX_HEADER${NC}"
    exit 3
fi

# Generate PDF using Pandoc
LUA_FILTER="$PROJECT_ROOT/scripts/table-columns.lua"
cd "$PROJECT_ROOT"

if pandoc "$MERGED_MD" \
    -o "$OUTPUT_FILE" \
    --pdf-engine=xelatex \
    --template="$PROJECT_ROOT/scripts/custom-latex-template.tex" \
    --lua-filter="$LUA_FILTER" \
    --toc \
    --toc-depth=3 \
    --number-sections \
    --include-in-header="$LATEX_HEADER" \
    --highlight-style=tango \
    --listings \
    --variable documentclass=report \
    --variable fontsize=10pt \
    --variable papersize=a4 \
    --variable geometry:margin=2cm \
    --variable tables=true \
    --variable graphics=true \
    --variable lmodern=false \
    2>&1; then

    echo ""
    echo -e "${GREEN}========================================${NC}"
    echo -e "${GREEN}  ✓ PDF生成完了！${NC}"
    echo -e "${GREEN}========================================${NC}"
    echo ""
    echo "出力ファイル: $OUTPUT_FILE"
    echo "ファイルサイズ: $(du -h "$OUTPUT_FILE" | cut -f1)"
    echo "保存場所: $(realpath "$OUTPUT_FILE")"
    echo ""
    echo -e "${BLUE}内容:${NC}"
    echo "  • 解説ドキュメント（概要、実装ガイド、インフラガイド）"
    echo "  • バックエンドAPIソースコード全文（FastAPI、backends、routes）"
    echo "  • インフラコード全文（Pulumi AWS/Azure/GCP）"
    echo "  • CI/CDワークフロー（GitHub Actions）"
    echo "  • フロントエンドソースコード（React主要ファイル）"
    echo "  • スクリプト（デプロイ、テスト、ビルド）"
    echo "  • 設定ファイル（docker-compose、Makefile等）"
    echo ""

    # Cleanup
    rm -rf "$TEMP_DIR"

    exit 0
else
    echo ""
    echo -e "${RED}✗ Error: PDF生成に失敗しました${NC}"
    echo -e "${YELLOW}マージ済みMarkdownファイル: $MERGED_MD${NC}"
    echo -e "${YELLOW}このファイルを確認するか、手動でPDF生成を試してください。${NC}"
    exit 3
fi
