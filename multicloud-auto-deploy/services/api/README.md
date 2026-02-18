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

### AWS Lambda（推奨方法）

**最適化されたデプロイ**: カスタムLambdaレイヤーを使用してサイズを削減

```bash
# 1. Lambda Layerをビルド（依存関係のみ）
cd /workspaces/ashnova/multicloud-auto-deploy
./scripts/build-lambda-layer.sh

# 2. Layerをデプロイ
aws lambda publish-layer-version \
  --layer-name multicloud-auto-deploy-staging-dependencies \
  --description "Dependencies for FastAPI + Mangum + JWT (Python 3.12)" \
  --zip-file fileb://services/api/lambda-layer.zip \
  --compatible-runtimes python3.12 \
  --region ap-northeast-1

# 3. Lambda関数コードをパッケージング（アプリケーションコードのみ）
cd services/api
rm -rf .build lambda.zip
mkdir -p .build/package
cp -r app .build/package/
cp index.py .build/package/
cd .build/package
zip -r ../../lambda.zip .
cd ../..

# 4. Lambda関数を更新（直接アップロード、S3不要）
aws lambda update-function-code \
  --function-name your-lambda-function \
  --zip-file fileb://lambda.zip \
  --region ap-northeast-1

# 5. Lambda関数にLayerをアタッチ
aws lambda update-function-configuration \
  --function-name your-lambda-function \
  --layers arn:aws:lambda:REGION:ACCOUNT_ID:layer:LAYER_NAME:VERSION \
  --region ap-northeast-1
```

**サイズ比較:**

- Layer（依存関係）: ~8-10MB
- Lambda関数（アプリケーションのみ）: ~78KB
- 合計: 50MB未満（直接アップロード可能）

**メリット:**

- ✅ S3経由のアップロード不要
- ✅ デプロイ時間短縮
- ✅ 依存関係の変更時のみLayerを更新
- ✅ boto3除外（Lambdaランタイムに含まれる）

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

| メソッド | パス      | 説明                  |
| -------- | --------- | --------------------- |
| GET      | `/`       | ヘルスチェック        |
| GET      | `/health` | ヘルスチェック        |
| GET      | `/docs`   | API文書（Swagger UI） |
| GET      | `/redoc`  | API文書（ReDoc）      |

## 🔗 関連リンク

- [FastAPI](https://fastapi.tiangolo.com/)
- [Pydantic](https://docs.pydantic.dev/)
- [Uvicorn](https://www.uvicorn.org/)
