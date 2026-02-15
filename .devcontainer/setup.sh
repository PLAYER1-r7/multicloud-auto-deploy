#!/bin/bash
# Dev Container初期化スクリプト
#
# Note: Core tools (AWS CLI, Azure CLI, GitHub CLI, Pulumi, Node.js, Python, Git, Docker)
#       are provided by devcontainer features and Dockerfile. This script handles:
#       - Node.js/Python project dependencies installation
#       - Pulumi Python dependencies (requirements.txt)
#       - Script permissions and project-specific setup

set -e

echo "========================================="
echo "  Multi-Cloud Auto Deploy - Setup"
echo "========================================="
echo ""

# カラー定義
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Node.js依存関係のインストール
if [ -d "services/frontend" ]; then
    echo -e "${BLUE}Installing frontend dependencies...${NC}"
    cd services/frontend
    npm install --quiet
    cd ../..
    echo -e "${GREEN}✓ Frontend dependencies installed${NC}"
fi

if [ -d "services/backend" ]; then
    echo -e "${BLUE}Installing backend dependencies...${NC}"
    cd services/backend
    npm install --quiet || true
    cd ../..
    echo -e "${GREEN}✓ Backend dependencies installed${NC}"
fi

# Python依存関係のインストール
if [ -f "services/backend/requirements.txt" ]; then
    echo -e "${BLUE}Installing Python dependencies...${NC}"
    pip install -q -r services/backend/requirements.txt
    echo -e "${GREEN}✓ Python dependencies installed${NC}"
fi

# Pulumi環境のセットアップ（requirements.txtのインストールのみ）
for cloud in aws azure gcp; do
    pulumi_dir="infrastructure/pulumi/$cloud"
    if [ -d "$pulumi_dir" ]; then
        echo -e "${BLUE}Setting up Pulumi dependencies for $cloud...${NC}"
        (cd "$pulumi_dir" && [ -f requirements.txt ] && pip install -q -r requirements.txt) || true
        echo -e "${GREEN}✓ Pulumi $cloud dependencies installed${NC}"
    fi
done

# スクリプトの実行権限確認
echo -e "${BLUE}Setting script permissions...${NC}"
chmod +x scripts/*.sh
echo -e "${GREEN}✓ Script permissions set${NC}"

# 便利なエイリアス表示
echo ""
echo -e "${YELLOW}=========================================${NC}"
echo -e "${YELLOW}  Available Commands${NC}"
echo -e "${YELLOW}=========================================${NC}"
echo ""
echo "Pulumi shortcuts:"
echo "  pulumi preview - 変更内容プレビュー"
echo "  pulumi up      - インフラストラクチャをデプロイ"
echo "  pulumi stack   - スタック管理"
echo ""
echo "Testing:"
echo "  test-all                   - 全エンドポイントテスト"
echo "  ./scripts/test-endpoints.sh - カスタムテスト"
echo ""
echo "Git shortcuts:"
echo "  gs   - git status"
echo "  gp   - git pull"
echo "  ll   - ls -lah"
echo ""
echo -e "${GREEN}✓ Setup complete!${NC}"
echo ""
