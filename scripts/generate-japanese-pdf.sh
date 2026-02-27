#!/bin/bash

# ========================================
# Script Name: generate-japanese-pdf.sh
# Description: Generate Japanese documentation PDF from selected Markdown files
# Author: PLAYER1-r7
# Created: 2026-02-27
# Version: 1.0.0
# ========================================
#
# Usage: ./scripts/generate-japanese-pdf.sh [output_filename]
#
# Parameters:
#   output_filename (optional) : Name of the output PDF file (default: multicloud-auto-deploy-japanese.pdf)
#
# Examples:
#   ./scripts/generate-japanese-pdf.sh
#   ./scripts/generate-japanese-pdf.sh japanese-guide.pdf
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
OUTPUT_FILE="${1:-multicloud-auto-deploy-japanese.pdf}"
TEMP_DIR=$(mktemp -d)
MERGED_MD="$TEMP_DIR/merged-japanese.md"

# Check if pandoc is installed
if ! command -v pandoc &> /dev/null; then
    echo -e "${RED}✗ Error: pandoc is not installed${NC}"
    echo "Install with: sudo apt-get install pandoc texlive-xetex texlive-lang-cjk fonts-noto-cjk"
    exit 1
fi

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  日本語PDF生成中${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Create temporary merged Markdown file with Japanese metadata
cat > "$MERGED_MD" << 'HEADER'
---
title: "マルチクラウド自動デプロイプラットフォーム"
subtitle: "日本語解説書"
author: "PLAYER1-r7"
date: "2026年2月27日"
geometry: margin=2.5cm
fontsize: 11pt
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

echo -e "${YELLOW}📝 日本語ドキュメントをマージ中...${NC}"

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

# Add Japanese documentation files
echo -e "\n${BLUE}概要とセットアップ${NC}"
add_chapter "$PROJECT_ROOT/README.md" "プロジェクト概要"

echo -e "\n${BLUE}実装ガイド${NC}"
add_chapter "$PROJECT_ROOT/docs/IMPLEMENTATION_GUIDE.md" "ソース実装解説書"
add_chapter "$PROJECT_ROOT/docs/SOURCE_CODE_GUIDE.md" "インフラ・CI/CD解説書"

echo -e "\n${BLUE}セットアップとデプロイ${NC}"
add_chapter "$PROJECT_ROOT/docs/CUSTOM_DOMAIN_SETUP.md" "カスタムドメイン設定"
add_chapter "$PROJECT_ROOT/docs/STAGING_TEST_GUIDE.md" "ステージング環境テスト"
add_chapter "$PROJECT_ROOT/docs/INTEGRATION_TESTS_GUIDE.md" "統合テストガイド"

echo -e "\n${BLUE}最適化とセキュリティ${NC}"
add_chapter "$PROJECT_ROOT/docs/LAMBDA_LAYER_OPTIMIZATION.md" "Lambda Layer最適化"
add_chapter "$PROJECT_ROOT/docs/CLOUD_ARCHITECTURE_MAPPER.md" "アーキテクチャマッパー"

echo ""
echo -e "${YELLOW}🔧 PDF生成中...${NC}"
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
    --variable fontsize=11pt \
    --variable papersize=a4 \
    --variable geometry:margin=2.5cm \
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
