# Simple SNS API (FastAPI)

完全Python実装のマルチクラウド対応Simple SNS バックエンドAPI

## 🎯 特徴

- **FastAPI** - 高速で型安全なPythonフレームワーク
- **マルチクラウド対応** - AWS / Azure / GCP / Local開発環境
- **Pydantic** - データバリデーションと設定管理
- **自動API文書** - OpenAPI (Swagger UI / ReDoc)

## 🚀 クイックスタート

### ローカル開発（MinIO使用）

```bash
# 依存関係のインストール
pip install -r requirements.txt

# MinIOを起動（Docker Compose）
docker-compose up -d minio

# 開発サーバー起動
uvicorn app.main:app --reload

# API文書
open http://localhost:8000/docs
```

### Docker使用

```bash
docker build -t simple-sns-api .
docker run -p 8000:8000 simple-sns-api
```

## 📁 プロジェクト構造

```
services/api/
├── app/
│   ├── __init__.py
│   ├── main.py          # FastAPIアプリケーション
│   ├── config.py        # 設定管理（Pydantic Settings）
│   ├── models.py        # データモデル（Pydantic）
│   ├── backends/        # クラウドプロバイダー別実装
│   │   ├── aws.py
│   │   ├── azure.py
│   │   ├── gcp.py
│   │   └── local.py
│   └── routes/          # APIルート
│       ├── messages.py
│       └── uploads.py
├── tests/               # テスト
├── requirements.txt
├── Dockerfile
└── .env.example
```

## 🔧 環境変数

`.env.example`を`.env`としてコピーして設定：

```bash
# クラウドプロバイダー選択
CLOUD_PROVIDER=aws  # aws, azure, gcp, local

# AWS設定
AWS_REGION=ap-northeast-1
DYNAMODB_TABLE_NAME=simple-sns-messages
S3_BUCKET_NAME=your-bucket
```

## 🧪 テスト

```bash
# テスト実行
pytest

# カバレッジ付き
pytest --cov=app tests/
```

## 📦 デプロイ

### AWS Lambda

```bash
# Lambda用にパッケージング
cd services/api
pip install -r requirements.txt -t package/
cp -r app/ package/
cd package && zip -r ../lambda.zip . && cd ..
```

### Azure Container Apps

```bash
az containerapp up \
  --name simple-sns-api \
  --source . \
  --ingress external \
  --target-port 8000
```

### GCP Cloud Run

```bash
gcloud run deploy simple-sns-api \
  --source . \
  --platform managed \
  --region asia-northeast1 \
  --allow-unauthenticated
```

## 🌐 エンドポイント

| メソッド | パス | 説明 |
|---------|------|------|
| GET | `/` | ヘルスチェック |
| GET | `/health` | ヘルスチェック |
| GET | `/docs` | API文書（Swagger UI） |
| GET | `/redoc` | API文書（ReDoc） |

## 🔗 関連リンク

- [FastAPI](https://fastapi.tiangolo.com/)
- [Pydantic](https://docs.pydantic.dev/)
- [Uvicorn](https://www.uvicorn.org/)
