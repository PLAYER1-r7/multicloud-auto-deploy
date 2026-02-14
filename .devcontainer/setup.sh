#!/bin/bash
# Dev Container初期化スクリプト

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

# Terraformの初期化
for cloud in aws azure gcp; do
    tf_dir="infrastructure/terraform/$cloud"
    if [ -d "$tf_dir" ]; then
        echo -e "${BLUE}Initializing Terraform for $cloud...${NC}"
        (cd "$tf_dir" && terraform init -backend=false &>/dev/null) || true
        echo -e "${GREEN}✓ Terraform $cloud initialized${NC}"
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
echo "Terraform shortcuts:"
echo "  tf             - terraform コマンド"
echo "  deploy-aws     - AWS環境にデプロイ"
echo "  deploy-azure   - Azure環境にデプロイ"
echo "  deploy-gcp     - GCP環境にデプロイ"
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
