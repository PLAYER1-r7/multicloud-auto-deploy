# Simple SNS Web (Reflex)

完全Python実装のフロントエンド - Reflexフレームワーク使用

## 🎯 特徴

- **完全Python実装** - JavaScriptなしでモダンなWebUIを構築
- **リアクティブ** - React風のコンポーネントと状態管理
- **型安全** - Pydanticベースの型システム
- **高速開発** - Pythonのみで完結

## 🚀 クイックスタート

### 初回セットアップ

```bash
# 依存関係のインストール
pip install -r requirements.txt

# Reflexプロジェクトの初期化
reflex init
```

### 開発サーバー起動

```bash
# APIエンドポイントを環境変数で指定
export API_URL=http://localhost:8000

# 開発サーバー起動（ホットリロード有効）
reflex run
```

ブラウザで http://localhost:3000 を開く

### 本番ビルド

```bash
# 本番用ビルド
reflex export

# ビルド成果物は frontend/ に生成される
```

## 📁 プロジェクト構造

```
services/web/
├── simple_sns_web.py    # メインアプリケーション
├── requirements.txt
├── rxconfig.py          # Reflex設定（自動生成）
├── assets/              # 静的ファイル
└── .web/                # ビルド成果物（自動生成）
```

## 🎨 Reflexコンポーネント

### 状態管理

```python
class State(rx.State):
    messages: List[Message] = []
    
    async def load_messages(self):
        # 非同期でAPIからデータ取得
        self.messages = await fetch_messages()
```

### コンポーネント

```python
def message_card(message: Message) -> rx.Component:
    return rx.box(
        rx.heading(message.author),
        rx.text(message.content),
        # ... スタイリング
    )
```

## 🌐 API連携

環境変数 `API_URL` でバックエンドAPIを指定：

```bash
# ローカル開発
export API_URL=http://localhost:8000

# AWS
export API_URL=https://xxx.execute-api.ap-northeast-1.amazonaws.com

# Azure
export API_URL=https://xxx.azurecontainerapps.io

# GCP
export API_URL=https://xxx.a.run.app
```

## 🚢 デプロイ

### 静的ファイルとして

```bash
# エクスポート
reflex export

# frontend/ディレクトリをホスティングサービスにデプロイ
# - S3 + CloudFront
# - Azure Static Web Apps
# - Cloud Storage + Cloud CDN
```

### サーバーとして

Reflexアプリはバックエンドを含むため、コンテナとしてデプロイ可能：

```bash
# Docker
docker build -t simple-sns-web .
docker run -p 3000:3000 -p 8000:8000 simple-sns-web

# Cloud Run / Container Apps
gcloud run deploy simple-sns-web --source .
az containerapp up --name simple-sns-web --source .
```

## 🔗 参考リンク

- [Reflex Documentation](https://reflex.dev/docs/getting-started/introduction/)
- [Reflex Examples](https://github.com/reflex-dev/reflex-examples)
