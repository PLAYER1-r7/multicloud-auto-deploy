#!/bin/bash
# Simple-SNS Quick Start Script

set -e

echo "🚀 Simple-SNS AWS デプロイメント"
echo "=================================="
echo ""

# カレントディレクトリを確認
if [ ! -f "package.json" ]; then
    echo "❌ エラー: このスクリプトは aws/simple-sns ディレクトリから実行してください"
    exit 1
fi

# 依存関係のインストール
echo "📦 Step 1: 依存関係のインストール"
npm install
echo "✅ 完了"
echo ""

# Lambda関数のビルド
echo "🔨 Step 2: Lambda関数のビルド"
npm run build
echo "✅ 完了"
echo ""

# Terraform初期化
echo "⚙️  Step 3: Terraform初期化"
cd ../../terraform/aws/envs/simple-sns
if [ ! -d ".terraform" ]; then
    tofu init
else
    echo "⏭️  既に初期化済み"
fi
echo "✅ 完了"
echo ""

# Terraformプラン確認
echo "📋 Step 4: デプロイプランの確認"
tofu plan
echo ""

# デプロイ確認
read -p "このプランでデプロイしますか？ (y/N): " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "❌ デプロイをキャンセルしました"
    exit 0
fi

# Terraformデプロイ
echo ""
echo "🚀 Step 5: インフラストラクチャのデプロイ"
tofu apply -auto-approve
echo "✅ 完了"
echo ""

# 出力値の表示
echo "📝 デプロイ情報:"
echo "=================================="
tofu output
echo ""

# .env.localの作成を促す
echo "⚠️  次のステップ:"
echo "1. terraform/aws/envs/simple-sns/terraform.tfstate.backup から出力値を確認"
echo "2. .env.local を作成して以下の値を設定:"
echo "   - VITE_API_URL=<api_url>"
echo "   - VITE_USER_POOL_ID=<cognito_user_pool_id>"
echo "   - VITE_COGNITO_CLIENT_ID=<cognito_client_id>"
echo "   - VITE_COGNITO_DOMAIN=<cognito_domain>"
echo "   - VITE_REDIRECT_URI=<redirect_uri>"
echo "3. フロントエンドをビルド: npm run build:frontend"
echo "4. フロントエンドをデプロイ: npm run deploy"
echo ""
echo "✅ インフラストラクチャのデプロイが完了しました！"
