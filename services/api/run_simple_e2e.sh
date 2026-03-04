#!/bin/bash
# シンプルな E2E テスト: frontend_exam + ローカル API サーバー
# プロキシなしで、フロントエンドから直接 API にアクセス

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

echo ""
echo "╔════════════════════════════════════════════════════════════════╗"
echo "║         シンプル E2E テスト環境セットアップ                    ║"
echo "║    frontend_exam + ローカル API（プロキシなし）               ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo ""

# Step 1: API サーバー起動
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "STEP 1️⃣  API サーバーの起動（ポート 7072）"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

if lsof -i :7072 > /dev/null 2>&1; then
    echo "⚠️  ポート 7072 は既に使用中です"
    echo "実行: pkill -f uvicorn"
    exit 1
fi

cd "$PROJECT_ROOT/services/api"
echo "📁 作業ディレクトリ: $PWD"
echo "🚀 API サーバー起動中..."
python3 -m uvicorn app.main:app --host 0.0.0.0 --port 7072 --reload > /tmp/api_server.log 2>&1 &
API_PID=$!
echo "   PID: $API_PID"

sleep 3
if kill -0 $API_PID 2>/dev/null; then
    echo "✅ API サーバーが起動しました (PID: $API_PID)"
else
    echo "❌ API サーバーの起動に失敗しました"
    cat /tmp/api_server.log
    exit 1
fi

# Step 2: Frontend Exam を HTTP で提供
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "STEP 2️⃣  Frontend Exam の提供（ポート 5174）"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

if lsof -i :5174 > /dev/null 2>&1; then
    echo "⚠️  ポート 5174 は既に使用中です"
    exit 1
fi

cd "$PROJECT_ROOT/services/frontend_exam/dist"
echo "📁 作業ディレクトリ: $PWD"
echo "🚀 Frontend Exam を提供中（ポート 5174）..."

# シンプルな HTTP サーバー（プロキシなし）
python3 << 'EOF' > /tmp/frontend_server.log 2>&1 &
import http.server
import socketserver
import os

class SimpleHandler(http.server.SimpleHTTPRequestHandler):
    def end_headers(self):
        # CORS ヘッダー追加
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        super().end_headers()

    def do_OPTIONS(self):
        self.send_response(200)
        self.end_headers()

    def log_message(self, format, *args):
        # ログ出力
        with open('/tmp/frontend_server.log', 'a') as f:
            f.write(f'{self.address_string()} - {format % args}\n')

with socketserver.TCPServer(('0.0.0.0', 5174), SimpleHandler) as httpd:
    print('Frontend HTTP Server running on http://0.0.0.0:5174')
    httpd.serve_forever()
EOF

FRONTEND_PID=$!
echo "   PID: $FRONTEND_PID"

sleep 2
if kill -0 $FRONTEND_PID 2>/dev/null; then
    echo "✅ Frontend Exam が http://localhost:5174 で提供中"
else
    echo "⚠️  Frontend サーバーの起動に問題"
fi

# Step 3: テスト情報
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ E2E テスト環境準備完了"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "📋 稼働中のサービス:"
echo "  • Frontend:  http://localhost:5174"
echo "  • API:       http://localhost:7072"
echo ""
echo "🧪 テスト手順:"
echo "  1. ブラウザで http://localhost:5174 にアクセス"
echo "  2. フロントエンド下部の window.API_BASE_URL 値を確認"
echo "  3. 「AI解答を実行」ボタンをクリック"
echo ""
echo "📊 API テスト (curl):"
echo "  curl -X POST http://localhost:7072/v1/solve \\"
echo "    -H 'Content-Type: application/json' \\"
echo "    -d '{\"input\":{\"imageUrl\":\"https://example.com/test.jpg\"},\"exam\":{\"university\":\"tokyo\"},\"options\":{}}'  "
echo ""
echo "📋 ログ確認:"
echo "  • API:       tail -f /tmp/api_server.log"
echo "  • Frontend:  tail -f /tmp/frontend_server.log"
echo ""
echo "🛑 終了するには Ctrl+C を押してください"
echo ""

# Cleanup on exit
cleanup() {
    echo ""
    echo "🛑 クリーンアップ中..."
    kill $API_PID 2>/dev/null || true
    kill $FRONTEND_PID 2>/dev/null || true
    echo "✅ サービスを停止しました"
}

trap cleanup EXIT INT TERM

# サービス継続
wait $API_PID $FRONTEND_PID 2>/dev/null || true
