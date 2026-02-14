# Simple SNS - Reflex Frontend

完全Python実装のフロントエンド（Reflex使用）

## 🎯 特徴

- **完全Python実装** - JavaScriptなし
- **リアクティブUI** - React風のコンポーネント
- **型安全** - Pydanticベース
- **CRUD完全対応** - 作成/読取/更新/削除
- **画像アップロード** - MinIO統合
- **ページネーション** - ページ切り替え機能

## 🚀 クイックスタート

### 開発環境

```bash
# 依存関係のインストール
pip install -r requirements.txt

# Reflexプロジェクトの初期化
reflex init

# 開発サーバー起動
export API_URL=http://localhost:8000
reflex run
```

### Docker環境

```bash
# docker-compose.ymlに以下を追加
docker-compose up frontend_reflex
```

## 📋 機能

- ✅ メッセージ作成（テキスト + 画像）
- ✅ メッセージ一覧表示
- ✅ メッセージ編集（インライン）
- ✅ メッセージ削除
- ✅ 画像アップロード・プレビュー
- ✅ ページネーション（前へ/次へ）

## 🔧 設定

`rxconfig.py` で設定可能：

```python
config = rx.Config(
    app_name="simple_sns",
    frontend_port=3000,
    backend_port=3001,
    api_url="http://localhost:8000",
)
```

## 📦 構造

```
frontend_reflex/
├── simple_sns.py      # メインアプリケーション
├── rxconfig.py        # Reflex設定
├── requirements.txt   # 依存関係
├── Dockerfile         # Docker設定
└── README.md          # このファイル
```

## 🌐 アクセス

- フロントエンド: http://localhost:3000
- Reflex管理: http://localhost:3001
