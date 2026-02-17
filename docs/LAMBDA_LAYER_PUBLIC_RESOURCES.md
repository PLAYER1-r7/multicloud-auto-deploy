# Lambda Layer 公開リソース活用ガイド

## 概要

カスタムLayerをビルドする代わりに、公開されているLambda Layerを使用することで：
- ✅ ビルド時間を削減
- ✅ メンテナンス不要
- ✅ 最適化済みのパッケージ
- ✅ 定期的な更新

## ⚠️ 重要な注意事項（2026年2月時点）

**Klayers（公開Lambda Layer）へのアクセスについて：**

現在、Klayersは**リソースベースポリシーの制限**により、他のAWSアカウントからのアクセスが制限されている可能性があります。

```
エラー例：
User is not authorized to perform: lambda:GetLayerVersion 
because no resource-based policy allows the lambda:GetLayerVersion action
```

**原因の可能性：**
1. Python 3.12 のサポートがまだ限定的
2. 特定リージョン（ap-northeast-1など）での公開が未完了
3. Klayers側のポリシー設定変更
4. クロスアカウントアクセスの制限

**推奨アプローチ：**
現時点では**カスタムLambda Layer**の使用を推奨します。
- ✅ 確実に動作
- ✅ 完全な制御
- ✅ プライベート環境対応
- ✅ サイズ最適化可能

詳細は本ドキュメントの「カスタムLayerの作成」セクションを参照してください。

---

## Klayers について（参考情報）

### Klayers とは

**Klayers** は Keith Rozario 氏が管理する、人気のPythonライブラリをLambda Layer形式で提供するプロジェクトです。

- 🌐 GitHub: https://github.com/keithrozario/Klayers
- 📊 Layer検索: https://api.klayers.cloud/

### 対応状況

当プロジェクトで必要な依存関係の対応状況：

| パッケージ | Klayers対応 | 用途 |
|-----------|-------------|------|
| fastapi | ✅ | Webフレームワーク |
| pydantic | ✅ | データバリデーション |
| mangum | ✅ | FastAPI→Lambda変換 |
| python-jose | ✅ | JWT検証 |
| PyJWT | ✅ | JWT処理 |
| requests | ✅ | HTTP クライアント |
| python-multipart | ✅ | ファイルアップロード |

## カスタムLayerの作成（推奨）

### メリット

- ✅ **確実に動作**：リソースベースポリシーの制限なし
- ✅ **完全な制御**：依存関係のバージョンを固定可能
- ✅ **サイズ最適化**：必要なパッケージのみ含める
- ✅ **プライベート環境**：どの環境でも使用可能
- ✅ **低レイテンシー**：同一アカウント内でのアクセス

### 使用手順

```bash
# 1. Layer をビルド
cd /workspaces/ashnova/multicloud-auto-deploy
./scripts/build-lambda-layer.sh

# 2. Layer をデプロイ
aws lambda publish-layer-version \
  --layer-name multicloud-auto-deploy-staging-dependencies \
  --description "Dependencies for FastAPI + Mangum + JWT (Python 3.12)" \
  --zip-file fileb://services/api/lambda-layer.zip \
  --compatible-runtimes python3.12 \
  --region ap-northeast-1

# 3. Lambda 関数にアタッチ
aws lambda update-function-configuration \
  --function-name your-function-name \
  --layers arn:aws:lambda:REGION:ACCOUNT_ID:layer:LAYER_NAME:VERSION
```

### Layer の内容

```python
# FastAPI Core
fastapi==0.115.0
pydantic==2.9.0
pydantic-settings==2.5.2

# Lambda アダプター
mangum==0.17.0

# JWT認証
python-jose[cryptography]==3.3.0
pyjwt==2.9.0

# その他
python-multipart==0.0.9
requests==2.32.3
```

### 実績

- **Layer サイズ**: 8.8MB
- **Lambda コード**: 78KB（アプリケーションのみ）
- **デプロイ時間**: 数秒
- **S3 不要**: 直接アップロード可能

---

## Klayers（参考）- 現在利用不可

### 1. Layer ARN の取得

#### オプションA: Klayers 公式サイトから取得

1. https://api.klayers.cloud/ にアクセス
2. Python バージョン: `3.12` を選択
3. リージョン: `ap-northeast-1` を選択
4. パッケージ名で検索（例: `fastapi`）
5. 最新の ARN をコピー

#### オプションB: API で取得

```bash
# FastAPI の最新 Layer ARN を取得
curl -s "https://api.klayers.cloud/api/v2/p3.12/layers/latest/ap-northeast-1/fastapi"

# 全パッケージのリストを取得
curl -s "https://api.klayers.cloud/api/v2/p3.12/layers/latest/ap-northeast-1/"
```

#### オプションC: AWS CLI で確認

```bash
# Klayers の fastapi Layer を検索
aws lambda list-layer-versions \
  --layer-name Klayers-p312-fastapi \
  --region ap-northeast-1 \
  --query 'LayerVersions[0].LayerVersionArn'
```

### 2. ARN の例（2026年2月時点）

```bash
# 注意: これらのARNは参考例です。最新版は上記の方法で確認してください

# FastAPI (Pydantic, Starlette含む)
arn:aws:lambda:ap-northeast-1:770693421928:layer:Klayers-p312-fastapi:5

# Mangum (FastAPI → Lambda変換)
arn:aws:lambda:ap-northeast-1:770693421928:layer:Klayers-p312-mangum:3

# python-jose (JWT検証)
arn:aws:lambda:ap-northeast-1:770693421928:layer:Klayers-p312-python-jose:4

# Requests
arn:aws:lambda:ap-northeast-1:770693421928:layer:Klayers-p312-requests:10

# python-multipart
arn:aws:lambda:ap-northeast-1:770693421928:layer:Klayers-p312-python-multipart:2
```

### 3. Pulumi での設定

```python
# infrastructure/pulumi/aws/simple-sns/__main__.py

# Klayers の ARN を使用（最大5つまで）
klayers_arns = [
    "arn:aws:lambda:ap-northeast-1:770693421928:layer:Klayers-p312-fastapi:5",
    "arn:aws:lambda:ap-northeast-1:770693421928:layer:Klayers-p312-mangum:3",
    "arn:aws:lambda:ap-northeast-1:770693421928:layer:Klayers-p312-python-jose:4",
    "arn:aws:lambda:ap-northeast-1:770693421928:layer:Klayers-p312-requests:10",
]

lambda_function = aws.lambda_.Function(
    "api-lambda",
    name=f"{project_name}-api-{environment}",
    runtime="python3.12",
    handler="app.main.handler",
    role=lambda_role.arn,
    code=pulumi.FileArchive(build_lambda_package()),
    layers=klayers_arns,  # Klayers を使用
    timeout=30,
    memory_size=512,
    environment=aws.lambda_.FunctionEnvironmentArgs(
        variables={
            "CLOUD_PROVIDER": "aws",
            "AWS_REGION": aws_region,
            "DYNAMODB_TABLE_NAME": messages_table.name,
            "S3_BUCKET_NAME": images_bucket.bucket,
        }
    ),
    tags=tags,
)
```

### 4. GitHub Actions での設定

```yaml
- name: Update Lambda Function
  run: |
    # Klayers の ARN を設定
    KLAYERS_ARNS=$(cat <<EOF
    arn:aws:lambda:ap-northeast-1:770693421928:layer:Klayers-p312-fastapi:5
    arn:aws:lambda:ap-northeast-1:770693421928:layer:Klayers-p312-mangum:3
    arn:aws:lambda:ap-northeast-1:770693421928:layer:Klayers-p312-python-jose:4
    arn:aws:lambda:ap-northeast-1:770693421928:layer:Klayers-p312-requests:10
    EOF
    )
    
    # Lambda 更新（Layerなし、直接アップロード）
    aws lambda update-function-code \
      --function-name $LAMBDA_FUNCTION \
      --zip-file fileb://services/api/lambda.zip
    
    # Klayers をアタッチ
    aws lambda update-function-configuration \
      --function-name $LAMBDA_FUNCTION \
      --layers $KLAYERS_ARNS
```

### 5. AWS CLI での設定

```bash
# Lambda 関数作成時
aws lambda create-function \
  --function-name my-api \
  --runtime python3.12 \
  --handler app.main.handler \
  --role arn:aws:iam::123456789012:role/lambda-role \
  --zip-file fileb://lambda.zip \
  --layers \
    arn:aws:lambda:ap-northeast-1:770693421928:layer:Klayers-p312-fastapi:5 \
    arn:aws:lambda:ap-northeast-1:770693421928:layer:Klayers-p312-mangum:3 \
    arn:aws:lambda:ap-northeast-1:770693421928:layer:Klayers-p312-python-jose:4

# 既存の Lambda 関数に Klayers を追加
aws lambda update-function-configuration \
  --function-name my-api \
  --layers \
    arn:aws:lambda:ap-northeast-1:770693421928:layer:Klayers-p312-fastapi:5 \
    arn:aws:lambda:ap-northeast-1:770693421928:layer:Klayers-p312-mangum:3 \
    arn:aws:lambda:ap-northeast-1:770693421928:layer:Klayers-p312-python-jose:4
```

## その他の公開 Lambda Layer

### AWS Lambda Powertools for Python (AWS公式)

ロギング、トレーシング、メトリクスなどの観測性機能を提供：

```python
# Layer ARN
arn:aws:lambda:ap-northeast-1:017000801446:layer:AWSLambdaPowertoolsPythonV2:68

# 使用例
from aws_lambda_powertools import Logger, Tracer, Metrics

logger = Logger()
tracer = Tracer()
metrics = Metrics()
```

詳細: https://docs.powertools.aws.dev/lambda/python/

### AWS SDK for pandas (旧 AWS Data Wrangler)

データ処理用（DynamoDB、S3、Athenaなど）：

```python
# Layer ARN (例)
arn:aws:lambda:ap-northeast-1:336392948345:layer:AWSSDKPandas-Python312:5

# 大規模データ処理が必要な場合に有用
```

詳細: https://aws-sdk-pandas.readthedocs.io/

## Layer の制限事項

- **最大数**: Lambda 関数につき最大 5 Layer
- **最大サイズ**: 全 Layer の合計が 250MB（解凍後）
- **互換性**: Python バージョンとの互換性を確認

## トラブルシューティング

### Layer バージョンが古い

```bash
# Klayers の最新バージョンを確認
curl -s "https://api.klayers.cloud/api/v2/p3.12/layers/latest/ap-northeast-1/fastapi" | jq

# または Layer バージョン一覧を取得
aws lambda list-layer-versions \
  --layer-name Klayers-p312-fastapi \
  --region ap-northeast-1
```

### パッケージが見つからない

一部のパッケージは Klayers に含まれていない場合があります。その場合：

1. **オプションA**: 複数の Layer を組み合わせる
2. **オプションB**: カスタム Layer を作成（`build-lambda-layer.sh`）
3. **オプションC**: Lambda パッケージに直接含める

### 依存関係の競合

FastAPI の Layer には Pydantic も含まれているため、重複しないよう注意：

```python
# ❌ 悪い例: 重複
layers = [
    "arn:aws:lambda:...:layer:Klayers-p312-fastapi:5",  # Pydantic含む
    "arn:aws:lambda:...:layer:Klayers-p312-pydantic:3", # 重複！
]

# ✅ 良い例: FastAPI だけで十分
layers = [
    "arn:aws:lambda:...:layer:Klayers-p312-fastapi:5",  # Pydantic含む
]
```

## ベストプラクティス

### 1. Layer ARN のバージョン管理

```bash
# .env または Pulumi Config に保存
cat > .env << EOF
KLAYER_FASTAPI_ARN=arn:aws:lambda:ap-northeast-1:770693421928:layer:Klayers-p312-fastapi:5
KLAYER_MANGUM_ARN=arn:aws:lambda:ap-northeast-1:770693421928:layer:Klayers-p312-mangum:3
KLAYER_JOSE_ARN=arn:aws:lambda:ap-northeast-1:770693421928:layer:Klayers-p312-python-jose:4
EOF
```

### 2. 定期的な更新チェック

```bash
#!/bin/bash
# scripts/check-klayers-updates.sh

PACKAGES=("fastapi" "mangum" "python-jose" "requests")
REGION="ap-northeast-1"

for pkg in "${PACKAGES[@]}"; do
    echo "Checking $pkg..."
    curl -s "https://api.klayers.cloud/api/v2/p3.12/layers/latest/$REGION/$pkg" | \
        jq -r '.arn'
done
```

### 3. フォールバック戦略

Klayers が利用できない場合のフォールバック：

```python
# Pulumi 設定例
klayers_available = config.get_bool("use_klayers") or True

if klayers_available:
    layers = [
        "arn:aws:lambda:ap-northeast-1:770693421928:layer:Klayers-p312-fastapi:5",
        # ...
    ]
else:
    # カスタム Layer にフォールバック
    layers = [custom_layer.arn]
```

## 比較: Klayers vs カスタム Layer

| 項目 | Klayers | カスタム Layer |
|------|---------|---------------|
| ビルド時間 | 不要 | 5-10分 |
| メンテナンス | 自動 | 手動 |
| カスタマイズ | 制限あり | 完全制御 |
| サイズ最適化 | 標準 | 可能 |
| バージョン管理 | コミュニティ | 自己管理 |
| 利用コスト | 無料 | 無料 |

## まとめ

### 推奨アプローチ（2026年2月時点）

**🌟 カスタムLambda Layerの使用を強く推奨します**

| 項目 | カスタムLayer | Klayers |
|------|--------------|---------|
| 利用可能性 | ✅ 確実 | ❌ アクセス制限あり |
| ビルド時間 | 5-10分（初回のみ） | N/A |
| メンテナンス | 自己管理 | N/A |
| カスタマイズ | ✅ 完全制御 | 制限あり |
| サイズ最適化 | ✅ 可能 | 標準 |
| プライベート環境 | ✅ 対応 | 制限あり |

### 実装済み・検証済み

当プロジェクトでは、カスタムLambda Layerの実装が完了し、動作確認済みです：

- ✅ ビルドスクリプト: [scripts/build-lambda-layer.sh](../scripts/build-lambda-layer.sh)
- ✅ Pulumi設定: 自動デプロイ対応
- ✅ GitHub Actions: CI/CD統合済み
- ✅ 最適化ガイド: [LAMBDA_LAYER_OPTIMIZATION.md](LAMBDA_LAYER_OPTIMIZATION.md)

### 将来的な展開

Klayersのアクセス制限が解除され次第、公開Layerの利用も検討できます。
それまでは、カスタムLayerで十分な性能とメリットが得られます。

## 参考リンク

- [Klayers GitHub](https://github.com/keithrozario/Klayers)
- [Klayers API](https://api.klayers.cloud/)
- [AWS Lambda Layers Documentation](https://docs.aws.amazon.com/lambda/latest/dg/configuration-layers.html)
- [AWS Lambda Powertools](https://docs.powertools.aws.dev/lambda/python/)
- [AWS SDK for pandas](https://aws-sdk-pandas.readthedocs.io/)
