#!/bin/bash
# E2E テストセットアップ: frontend_exam + ローカル API サーバー

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

echo ""
echo "╔════════════════════════════════════════════════════════════════╗"
echo "║                  E2E テスト環境セットアップ                    ║"
echo "║         frontend_exam + ローカル API サーバー                  ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo ""

# ポート確認
check_port() {
    local port=$1
    if lsof -i :$port > /dev/null 2>&1; then
        echo "⚠️  ポート $port は既に使用中です"
        return 1
    fi
    return 0
}

# Step 1: API サーバー起動
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "STEP 1️⃣  API サーバーの起動（ポート 7072）"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

if ! check_port 7072; then
    echo "❌ ポート 7072 を開放してください"
    exit 1
fi

cd "$PROJECT_ROOT/services/api"
echo "📁 作業ディレクトリ: $PWD"
echo "🚀 API サーバー起動中..."
python3 -m uvicorn app.main:app --host 0.0.0.0 --port 7072 --reload > /tmp/api_server.log 2>&1 &
API_PID=$!
echo "   PID: $API_PID"

# サーバー起動待機
sleep 3
if kill -0 $API_PID 2>/dev/null; then
    echo "✅ API サーバーが起動しました (PID: $API_PID)"
else
    echo "❌ API サーバーの起動に失敗しました"
    cat /tmp/api_server.log
    exit 1
fi

# Step 2: Frontend Exam 提供
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "STEP 2️⃣  Frontend Exam の提供（ポート 5174）"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

if ! check_port 5174; then
    echo "❌ ポート 5174 を開放してください"
    kill $API_PID
    exit 1
fi

cd "$PROJECT_ROOT/services/frontend_exam"

# dist フォルダの確認
if [ ! -d "dist" ]; then
    echo "❌ dist フォルダが見つかりません"
    echo "   実行: cd $PROJECT_ROOT/services/frontend_exam && npm run build"
    kill $API_PID
    exit 1
fi

echo "📁 作業ディレクトリ: $PWD"
echo "🚀 Frontend Exam を提供中（ポート 5174）..."

# Python HTTP サーバー + CORS プロキシ
python3 << 'EOF' > /tmp/frontend_proxy.log 2>&1 &
import http.server
import socketserver
import urllib.request
import json
import os
from pathlib import Path

class ProxyHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        # 静的ファイルの提供
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()

        if self.path == '/' or self.path.endswith('.html'):
            file_path = Path('dist') / self.path.lstrip('/')
            if file_path.is_file():
                with open(file_path, 'rb') as f:
                    self.wfile.write(f.read())
            else:
                with open('dist/index.html', 'rb') as f:
                    self.wfile.write(f.read())
        else:
            file_path = Path('dist') / self.path.lstrip('/')
            if file_path.is_file():
                with open(file_path, 'rb') as f:
                    self.wfile.write(f.read())

    def do_POST(self):
        # API プロキシ: localhost:5174/v1/* → localhost:7072/v1/*
        if self.path.startswith('/v1/'):
            content_length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(content_length)

            # API バックエンドへフォワード
            backend_url = f'http://localhost:7072{self.path}'
            try:
                req = urllib.request.Request(
                    backend_url,
                    data=body,
                    headers={'Content-Type': 'application/json'}
                )
                with urllib.request.urlopen(req, timeout=120) as response:
                    api_response = response.read()

                # CORS レスポンス
                self.send_response(response.status)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.send_header('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS')
                self.send_header('Access-Control-Allow-Headers', 'Content-Type')
                self.end_headers()
                self.wfile.write(api_response)
            except Exception as e:
                self.send_response(502)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(json.dumps({'error': str(e)}).encode())
        else:
            self.send_response(404)
            self.end_headers()

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

os.chdir('dist')
with socketserver.TCPServer(('0.0.0.0', 5174), ProxyHandler) as httpd:
    print('Frontend Proxy running on port 5174')
    httpd.serve_forever()
EOF

PROXY_PID=$!
echo "   PID: $PROXY_PID"

sleep 2
if kill -0 $PROXY_PID 2>/dev/null; then
    echo "✅ Frontend Exam が http://localhost:5174 で提供中"
else
    echo "❌ Frontend Exam の起動に失敗しました"
    cat /tmp/frontend_proxy.log
    kill $API_PID
    exit 1
fi

# Step 3: テスト情報表示
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
echo "  2. 数学問題画像をアップロード（または URL 指定）"
echo "  3. 「AI解答を実行」ボタンをクリック"
echo "  4. フロントエンド → API → Azure OCR/LLM という流れで処理"
echo ""
echo "📊 ログ確認:"
echo "  • API:      tail -f /tmp/api_server.log"
echo "  • Frontend: tail -f /tmp/frontend_proxy.log"
echo ""
echo "🛑 終了するには Ctrl+C を押してください"
echo ""

# Cleanup on exit
cleanup() {
    echo ""
    echo "🛑 クリーンアップ中..."
    kill $API_PID 2>/dev/null || true
    kill $PROXY_PID 2>/dev/null || true
    echo "✅ サービスを停止しました"
}

trap cleanup EXIT INT TERM

# サービス継続
wait $API_PID $PROXY_PID
