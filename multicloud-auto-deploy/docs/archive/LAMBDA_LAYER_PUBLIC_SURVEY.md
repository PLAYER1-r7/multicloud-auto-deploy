# 公開Lambda Layer 利用可能性調査（2026年2月）

> **AIエージェント向けメモ**: 公開 Lambda Layer の調査結果と選定基準。


## 調査結果サマリー

### ✅ 利用可能な公開Lambda Layer（AWS公式）

| Layer名 | ARN | Python 3.12 | 用途 | 状態 |
|---------|-----|-------------|------|------|
| **AWS Lambda Powertools** | `arn:aws:lambda:ap-northeast-1:017000801446:layer:AWSLambdaPowertoolsPythonV2:68` | ✅ | ロギング、トレーシング、メトリクス | ✅ アクセス可能 |
| **AWS SDK for pandas** | `arn:aws:lambda:ap-northeast-1:336392948345:layer:AWSSDKPandas-Python312:13` | ✅ | データ処理（pandas, pyarrow等） | ✅ アクセス可能 |
| **AWS Parameters & Secrets** | `arn:aws:lambda:ap-northeast-1:133490724326:layer:AWS-Parameters-and-Secrets-Lambda-Extension:11` | ✅ | パラメータ/シークレット取得 | ✅ アクセス可能 |

### ❌ 利用不可の公開Lambda Layer

| Layer名 | 理由 |
|---------|------|
| **Klayers** | リソースベースポリシーの制限 |
| **FastAPI/Mangum専用Layer** | 公開されているものが見つからない |

## 詳細調査

### 1. AWS Lambda Powertools for Python v2

**ARN**: `arn:aws:lambda:ap-northeast-1:017000801446:layer:AWSLambdaPowertoolsPythonV2:68`

**特徴**:
- AWS公式サポート
- Python 3.7 - 3.12 対応
- バージョン: 2.36.0

**含まれる機能**:
```python
from aws_lambda_powertools import Logger, Tracer, Metrics
from aws_lambda_powertools.event_handler import APIGatewayRestResolver
from aws_lambda_powertools.utilities.typing import LambdaContext
```

**使用例**:
```python
from aws_lambda_powertools import Logger

logger = Logger()

@logger.inject_lambda_context
def lambda_handler(event, context):
    logger.info("Processing request")
    return {"statusCode": 200}
```

**メリット**:
- ✅ 構造化ロギング
- ✅ X-Ray トレーシング
- ✅ CloudWatch メトリクス
- ✅ イベントハンドラー（API Gateway, ALB等）

**注意**: FastAPI/Mangumは含まれていない

### 2. AWS SDK for pandas (旧AWS Data Wrangler)

**ARN**: `arn:aws:lambda:ap-northeast-1:336392948345:layer:AWSSDKPandas-Python312:13`

**特徴**:
- AWS公式サポート
- Python 3.12 専用
- バージョン: 3.9.1

**含まれるライブラリ**:
- pandas
- numpy
- pyarrow
- awswrangler
- boto3/botocore

**使用例**:
```python
import awswrangler as wr
import pandas as pd

# S3からデータ読み込み
df = wr.s3.read_parquet(path="s3://bucket/path/")

# DynamoDBからデータ取得
df = wr.dynamodb.read_items(table_name="my-table")
```

**メリット**:
- ✅ データ処理に特化
- ✅ S3/DynamoDB/Athena統合
- ✅ 大規模データ処理

**注意**: FastAPI/Mangumは含まれていない。データ処理用途専用。

### 3. AWS Parameters and Secrets Lambda Extension

**ARN**: `arn:aws:lambda:ap-northeast-1:133490724326:layer:AWS-Parameters-and-Secrets-Lambda-Extension:11`

**特徴**:
- AWS公式サポート
- パラメータ/シークレットのキャッシング
- ローカルHTTP APIでアクセス

**使用例**:
```python
import requests
import os

# Secrets Managerからシークレット取得
secrets_extension_endpoint = f"http://localhost:2773/secretsmanager/get?secretId={os.environ['SECRET_NAME']}"
r = requests.get(secrets_extension_endpoint, headers={"X-Aws-Parameters-Secrets-Token": os.environ['AWS_SESSION_TOKEN']})
secret = r.json()
```

**メリット**:
- ✅ シークレット取得の高速化（キャッシュ）
- ✅ IAMコール数削減
- ✅ コスト削減

## FastAPI/Mangum用のソリューション

### 問題点

FastAPI、Mangum、Pydantic等のWebフレームワーク関連のライブラリを含む**公開Lambda Layerは存在しない**か、アクセス制限されています。

### 推奨ソリューション：カスタムLayer + AWS公式Layer の組み合わせ

#### パターンA: カスタムLayer単独（現在の実装）

```
Lambda Function:
├── Code (78KB)
└── Layer 1: カスタムLayer (8.8MB)
    ├── FastAPI
    ├── Mangum
    ├── Pydantic
    ├── python-jose
    └── requests
```

**メリット:**
- ✅ シンプル（Layer 1つ）
- ✅ 確実に動作
- ✅ 完全な制御

#### パターンB: カスタムLayer + AWS公式Layer

```
Lambda Function:
├── Code (78KB)
├── Layer 1: カスタムLayer (8.8MB)
│   ├── FastAPI
│   ├── Mangum
│   ├── Pydantic
│   ├── python-jose
│   └── requests
└── Layer 2: AWS Lambda Powertools (AWS公式)
    ├── Logger
    ├── Tracer
    └── Metrics
```

**使用例:**
```python
# app/main.py
from fastapi import FastAPI
from mangum import Mangum
from aws_lambda_powertools import Logger, Tracer, Metrics

# Powertools の初期化
logger = Logger()
tracer = Tracer()
metrics = Metrics()

app = FastAPI()

@app.get("/api/posts")
@tracer.capture_method
def get_posts():
    logger.info("Fetching posts")
    metrics.add_metric(name="PostsRequested", unit="Count", value=1)
    return {"posts": []}

handler = Mangum(app, lifespan="off")
```

**メリット:**
- ✅ 構造化ロギング（CloudWatch Logs Insights対応）
- ✅ X-Ray トレーシング
- ✅ CloudWatch メトリクス
- ✅ AWS公式サポート

**Lambda設定例:**
```bash
aws lambda update-function-configuration \
  --function-name multicloud-auto-deploy-staging-api \
  --layers \
    arn:aws:lambda:ap-northeast-1:278280499340:layer:multicloud-auto-deploy-staging-dependencies:2 \
    arn:aws:lambda:ap-northeast-1:017000801446:layer:AWSLambdaPowertoolsPythonV2:68
```

## 推奨アーキテクチャ

### 基本構成（現在）

```
✅ カスタムLayer のみ使用
- FastAPI/Mangum/Pydantic等の全依存関係を含む
- シンプルで確実
- Layer数: 1/5（Lambda制限）
```

### 拡張構成（オプション）

```
✅ カスタムLayer + AWS Lambda Powertools
- FastAPI/Mangum: カスタムLayer
- 観測性（ロギング/トレーシング/メトリクス): Powertools
- Production Ready
- Layer数: 2/5（Lambda制限）
```

### 高度な構成

```
✅ カスタムLayer + Powertools + データ処理
- FastAPI/Mangum: カスタムLayer
- 観測性: Powertools  
- データ処理: AWS SDK for pandas
- Layer数: 3/5（Lambda制限）
```

## 実装ガイド

### 現在の構成を維持（推奨）

```bash
# 既にデプロイ済み・動作確認済み
Layer: multicloud-auto-deploy-staging-dependencies:2
Status: ✅ 稼働中
```

### AWS Lambda Powertools を追加する場合

```bash
# 1. requirements.txt に追加（不要 - Layerに含まれる）
# aws-lambda-powertools は Layer から利用

# 2. コードを更新
# app/main.py に Powertools を import

# 3. Lambda に Powertools Layer を追加
aws lambda update-function-configuration \
  --function-name multicloud-auto-deploy-staging-api \
  --layers \
    arn:aws:lambda:ap-northeast-1:278280499340:layer:multicloud-auto-deploy-staging-dependencies:2 \
    arn:aws:lambda:ap-northeast-1:017000801446:layer:AWSLambdaPowertoolsPythonV2:68

# 4. GitHub Actions でデプロイ
gh workflow run deploy-aws.yml
```

## まとめ

### 利用可能な公開Layer

| 用途 | Layer | 状態 |
|------|-------|------|
| Web フレームワーク（FastAPI/Mangum） | ❌ 公開Layerなし | カスタムLayer使用 |
| 観測性（ロギング/トレーシング） | ✅ AWS Lambda Powertools | 利用可能 |
| データ処理（pandas等） | ✅ AWS SDK for pandas | 利用可能 |
| シークレット管理 | ✅ Parameters & Secrets Extension | 利用可能 |

### 推奨アプローチ

1. **基本構成**: カスタムLayerのみ（現在の実装）✅
2. **拡張構成**: カスタムLayer + Powertools（オプション）
3. **維持**: 現在の構成で十分な性能とメリット

**結論**: FastAPI/Mangum用の公開Layerは存在しないため、カスタムLayerが最適解です。
AWS公式Layerは補完的な機能（観測性、データ処理等）として追加可能です。
