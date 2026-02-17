# AWS Lambda Layer 最適化戦略

最終更新: 2026-02-17

## 📋 概要

AWS Lambda関数の依存関係管理において、**Pulumi自動管理によるカスタムLayer**の実装戦略を提案します。

### 💡 最新アプローチ（2026-02-17更新）

**Pulumiによる完全自動管理**

従来のARNハードコーディング方式から、**Pulumi Infrastructure as Code**による完全自動管理に移行しました。

#### メリット

✅ **手動作業の完全排除**: Lambda Layer ARNの手動更新が不要  
✅ **バージョン管理の自動化**: Lambda Layerの内容変更時に自動的に新バージョン作成  
✅ **デプロイの一貫性**: インフラとアプリケーションコードを同時にデプロイ  
✅ **ロールバック対応**: Pulumiのスタック履歴で簡単にロールバック可能  

#### 実装方法

```python
# infrastructure/pulumi/aws/__main__.py

# Lambda Layer ZIPを自動検出
layer_zip_path = pathlib.Path(__file__).parent.parent.parent.parent / "services" / "api" / "lambda-layer.zip"

# Pulumi Lambda Layer リソース作成
lambda_layer = aws.lambda_.LayerVersion(
    "dependencies-layer",
    layer_name=f"{project_name}-{stack}-dependencies",
    code=pulumi.FileArchive(str(layer_zip_path)),
    compatible_runtimes=["python3.12"],
    description=f"Dependencies for {project_name} {stack} (FastAPI, Mangum, Pydantic, etc.)",
)

# Lambda関数に自動アタッチ
lambda_function = aws.lambda_.Function(
    "api-function",
    name=f"{project_name}-{stack}-api",
    runtime="python3.12",
    layers=[lambda_layer.arn],  # 動的ARN参照
    # ... その他の設定
)
```

#### デプロイフロー

```bash
# 1. Lambda Layerをビルド
./scripts/build-lambda-layer.sh

# 2. Pulumiで自動デプロイ（Layer + Lambda Function）
cd infrastructure/pulumi/aws
pulumi up

# GitHub Actions経由の場合は自動実行:
git push origin develop  # staging環境に自動デプロイ
```

#### GitHub Actions統合

```yaml
# .github/workflows/deploy-aws.yml

- name: Build Lambda Layer
  run: |
    cd multicloud-auto-deploy
    ./scripts/build-lambda-layer.sh
    
- name: Deploy with Pulumi
  uses: pulumi/actions@v5
  with:
    command: up
    # Lambda LayerとLambda Functionを同時にデプロイ
```

### 従来の課題（解決済み）

- **問題**: Lambda関数で `No module named 'mangum'` エラーが発生
- **原因**: Lambda Layerが正しくアタッチされていない、または内容が不完全
- **影響**: AWS Staging環境のAPIが完全に機能停止（500エラー）

---

## 🎯 推奨戦略：ハイブリッドLayer構成

### 戦略の概要

**2層構成のLayer戦略**を採用することを推奨します：

1. **AWS公式Layer**：安定した基盤ライブラリ（boto3, AWS SDK拡張など）
2. **カスタムLayer**：アプリケーション固有の依存関係（FastAPI, mangum等）

### メリット

| 項目             | AWS公式Layer       | カスタムLayer       |
| ---------------- | ------------------ | ------------------- |
| **信頼性**       | ⭐⭐⭐⭐⭐ AWS保証 | ⭐⭐⭐⭐ 完全制御   |
| **メンテナンス** | ⭐⭐⭐⭐⭐ 不要    | ⭐⭐⭐ 要管理       |
| **サイズ**       | ⭐⭐⭐ AWS最適化   | ⭐⭐⭐⭐ 必要最小限 |
| **ビルド時間**   | ⭐⭐⭐⭐⭐ ゼロ    | ⭐⭐⭐ 数分         |
| **柔軟性**       | ⭐⭐ 限定的        | ⭐⭐⭐⭐⭐ 完全自由 |

---

## 🏗️ 実装プラン

### オプション1：完全カスタムLayer（安全・推奨）

**特徴**：

- ✅ すべての依存関係を1つのカスタムLayerに統合
- ✅ 最もシンプルで確実
- ✅ トラブルシューティングが容易
- ⚠️ Layerサイズが若干大きい（約10-15MB）

#### 実装手順

```bash
# ステップ1: Layerのビルド
cd /workspaces/ashnova/multicloud-auto-deploy/services/api
bash ../../scripts/build-lambda-layer.sh

# ステップ2: ビルド結果の確認
ls -lh lambda-layer.zip
# 期待サイズ: 8-10MB

# ステップ3: Layerの公開
LAYER_ARN=$(aws lambda publish-layer-version \
  --layer-name multicloud-auto-deploy-staging-dependencies \
  --description "FastAPI + Mangum + JWT (Python 3.12)" \
  --zip-file fileb://lambda-layer.zip \
  --compatible-runtimes python3.12 \
  --region ap-northeast-1 \
  --query LayerVersionArn \
  --output text)

echo "✅ Layer ARN: $LAYER_ARN"

# ステップ4: Lambda関数にアタッチ
aws lambda update-function-configuration \
  --function-name multicloud-auto-deploy-staging-api \
  --layers "$LAYER_ARN" \
  --region ap-northeast-1

echo "✅ Layer attached to Lambda function"

# ステップ5: 動作確認
sleep 10  # 設定反映待機
curl https://z42qmqdqac.execute-api.ap-northeast-1.amazonaws.com/
```

#### Layer内容

```ini
# requirements-layer.txt
typing_extensions==4.12.2
fastapi==0.115.0
pydantic==2.9.0
pydantic-settings==2.5.2
mangum==0.17.0
python-jose[cryptography]==3.3.0
pyjwt==2.9.0
requests==2.32.3
python-multipart==0.0.9
```

**推定サイズ**: 約8.8MB（実測値）

---

### オプション2：AWS公式 + カスタムLayer（ハイブリッド）

**特徴**：

- ✅ AWS公式Layerで基盤ライブラリをカバー
- ✅ カスタムLayerを最小サイズに削減
- ⚠️ AWS公式Layerの可用性に依存
- ⚠️ 設定が複雑

#### 実装手順

##### ステップ1: 利用可能なAWS公式Layerを確認

```bash
# AWS Lambda Powertools Layer (AWS公式)
aws lambda list-layer-versions \
  --layer-name AWSLambdaPowertoolsPythonV2 \
  --region ap-northeast-1 \
  --compatible-runtime python3.12 \
  --max-items 1

# AWS SDK Boto3 Layer (AWS公式 - 最新版)
# 注: Lambda runtimeには既にboto3が含まれているため、通常は不要
```

**AWS Lambda Powertools**:

- SDK拡張機能（ロギング、メトリクス、トレーシング等）
- Python 3.12対応
- ARN例: `arn:aws:lambda:ap-northeast-1:017000801446:layer:AWSLambdaPowertoolsPythonV2:53`

##### ステップ2: カスタムLayerの依存関係を最小化

```ini
# requirements-layer-minimal.txt
# AWS公式Layerに含まれないもののみ
fastapi==0.115.0
pydantic==2.9.0
pydantic-settings==2.5.2
mangum==0.17.0
python-jose[cryptography]==3.3.0
pyjwt==2.9.0
python-multipart==0.0.9
```

##### ステップ3: 最小カスタムLayerのビルド

```bash
cd /workspaces/ashnova/multicloud-auto-deploy/services/api

# 一時的なrequirementsファイルを作成
cat > requirements-layer-minimal.txt << 'EOF'
fastapi==0.115.0
pydantic==2.9.0
pydantic-settings==2.5.2
mangum==0.17.0
python-jose[cryptography]==3.3.0
pyjwt==2.9.0
python-multipart==0.0.9
EOF

# Layerをビルド
rm -rf .build-layer lambda-layer-minimal.zip
mkdir -p .build-layer/python

pip install \
  -r requirements-layer-minimal.txt \
  -t .build-layer/python/ \
  --platform manylinux2014_x86_64 \
  --only-binary=:all: \
  --python-version 3.12

# ZIPファイル作成
cd .build-layer
zip -r ../lambda-layer-minimal.zip python/
cd ..

# サイズ確認
ls -lh lambda-layer-minimal.zip
```

##### ステップ4: 複数Layerのアタッチ

```bash
# AWS公式Layer ARN（要確認）
AWS_POWERTOOLS_ARN="arn:aws:lambda:ap-northeast-1:017000801446:layer:AWSLambdaPowertoolsPythonV2:53"

# カスタムLayerを公開
CUSTOM_LAYER_ARN=$(aws lambda publish-layer-version \
  --layer-name multicloud-auto-deploy-staging-minimal \
  --description "FastAPI + Mangum (minimal)" \
  --zip-file fileb://lambda-layer-minimal.zip \
  --compatible-runtimes python3.12 \
  --region ap-northeast-1 \
  --query LayerVersionArn \
  --output text)

# 複数Layerをアタッチ（最大5つまで）
aws lambda update-function-configuration \
  --function-name multicloud-auto-deploy-staging-api \
  --layers "$AWS_POWERTOOLS_ARN" "$CUSTOM_LAYER_ARN" \
  --region ap-northeast-1
```

**推定サイズ削減**:

- オプション1（完全カスタム）: 約10MB
- オプション2（ハイブリッド）: カスタム部分 約7MB + AWS公式Layer

---

### オプション3：レイヤー分離戦略（上級者向け）

**特徴**：

- ✅ 頻繁に更新される依存関係とそうでないものを分離
- ✅ 更新効率が向上
- ⚠️ 管理が複雑
- ⚠️ デバッグが困難

#### Layer構成例

**Layer 1: 安定ライブラリ（更新頻度低）**

```ini
python-jose[cryptography]==3.3.0
pyjwt==2.9.0
requests==2.32.3
```

**Layer 2: フレームワーク（更新頻度中）**

```ini
fastapi==0.115.0
pydantic==2.9.0
pydantic-settings==2.5.2
```

**Layer 3: アダプター（更新頻度高）**

```ini
mangum==0.17.0
python-multipart==0.0.9
```

---

## 📊 戦略比較表

| 戦略                          | シンプル   | 信頼性     | サイズ     | 更新容易性 | 推奨度      |
| ----------------------------- | ---------- | ---------- | ---------- | ---------- | ----------- |
| **オプション1: 完全カスタム** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐   | ⭐⭐⭐⭐   | **🥇 推奨** |
| **オプション2: ハイブリッド** | ⭐⭐⭐     | ⭐⭐⭐⭐   | ⭐⭐⭐⭐⭐ | ⭐⭐⭐     | 🥈 次点     |
| **オプション3: 分離戦略**     | ⭐⭐       | ⭐⭐⭐     | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | 上級者向け  |

---

## 🚀 即時実行：オプション1の実装

### 現在の環境修復（最優先）

以下のコマンドを**順番に**実行してください：

```bash
# === ステップ1: プロジェクトディレクトリに移動 ===
cd /workspaces/ashnova/multicloud-auto-deploy/services/api

# === ステップ2: Layerをビルド ===
bash ../../scripts/build-lambda-layer.sh

# 出力例:
# ✅ Lambda Layer built successfully
# 📦 Size: 8.8MB
# 📄 File: lambda-layer.zip

# === ステップ3: Layerを公開 ===
LAYER_ARN=$(aws lambda publish-layer-version \
  --layer-name multicloud-auto-deploy-staging-dependencies \
  --description "FastAPI + Mangum + JWT + Auth (Python 3.12)" \
  --zip-file fileb://lambda-layer.zip \
  --compatible-runtimes python3.12 \
  --region ap-northeast-1 \
  --query LayerVersionArn \
  --output text)

# ARNを表示
echo "✅ Layer ARN: $LAYER_ARN"
echo "$LAYER_ARN" > /tmp/layer-arn.txt

# === ステップ4: Lambda関数にアタッチ ===
aws lambda update-function-configuration \
  --function-name multicloud-auto-deploy-staging-api \
  --layers "$LAYER_ARN" \
  --region ap-northeast-1

echo "✅ Layer attached successfully"

# === ステップ5: 設定反映を待機 ===
echo "⏳ Waiting for configuration update..."
sleep 15

# === ステップ6: 動作確認 ===
echo "🧪 Testing API endpoint..."
echo ""
echo "1. Health Check:"
curl -s https://z42qmqdqac.execute-api.ap-northeast-1.amazonaws.com/ | jq '.'

echo ""
echo "2. GET /api/messages/:"
curl -s https://z42qmqdqac.execute-api.ap-northeast-1.amazonaws.com/api/messages/ | jq '.'

echo ""
echo "3. POST /api/messages/:"
curl -s -X POST https://z42qmqdqac.execute-api.ap-northeast-1.amazonaws.com/api/messages/ \
  -H "Content-Type: application/json" \
  -d '{"content":"Layer test message","author":"System"}' | jq '.'
```

### 成功確認

以下の出力が得られれば成功です：

```json
// Health Check
{"status":"ok","provider":"aws","version":"3.0.0"}

// GET /api/messages/
[]  // または既存のメッセージ配列

// POST /api/messages/
{
  "id": "xxx-xxx-xxx",
  "content": "Layer test message",
  "author": "System",
  "created_at": "2026-02-17T..."
}
```

### トラブルシューティング

#### エラー: タイムアウト

```bash
# Lambdaログを確認
aws logs tail /aws/lambda/multicloud-auto-deploy-staging-api \
  --region ap-northeast-1 \
  --since 5m \
  --format short
```

#### エラー: 依然として ImportModuleError

```bash
# Layer設定を確認
aws lambda get-function-configuration \
  --function-name multicloud-auto-deploy-staging-api \
  --region ap-northeast-1 \
  --query 'Layers[*].Arn'

# 期待結果:
# [
#   "arn:aws:lambda:ap-northeast-1:278280499340:layer:multicloud-auto-deploy-staging-dependencies:X"
# ]
```

---

## 🔄 CI/CDワークフローとの統合

### GitHub Actionsでの自動Layer管理

現在のワークフローを修正して、Layerを自動的にビルド・デプロイします。

#### 修正案（deploy-aws.yml）

```yaml
- name: Build and Deploy Lambda Layer
  id: deploy_layer
  run: |
    cd multicloud-auto-deploy/services/api

    # Layerをビルド
    bash ../../scripts/build-lambda-layer.sh

    # Layerを公開
    LAYER_ARN=$(aws lambda publish-layer-version \
      --layer-name multicloud-auto-deploy-${{ github.event.inputs.environment || 'staging' }}-dependencies \
      --description "FastAPI + Mangum + JWT (Python 3.12) - ${{ github.sha }}" \
      --zip-file fileb://lambda-layer.zip \
      --compatible-runtimes python3.12 \
      --region ${{ env.AWS_REGION }} \
      --query LayerVersionArn \
      --output text)

    echo "layer_arn=$LAYER_ARN" >> $GITHUB_OUTPUT
    echo "✅ Layer published: $LAYER_ARN"

- name: Update Lambda Function Configuration
  run: |
    aws lambda update-function-configuration \
      --function-name ${{ steps.pulumi_outputs.outputs.lambda_function_name }} \
      --layers ${{ steps.deploy_layer.outputs.layer_arn }} \
      --region ${{ env.AWS_REGION }}

    echo "✅ Lambda function configuration updated"
```

---

## 📈 パフォーマンス最適化のヒント

### 1. Layer内容の最小化

```bash
# 不要なファイルを除外
cd .build-layer/python
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
find . -type d -name "*.dist-info" -exec rm -rf {} + 2>/dev/null || true
find . -type f -name "*.pyc" -delete
find . -type f -name "*.pyo" -delete
```

### 2. 圧縮率の向上

```bash
# 高圧縮率でZIP作成
cd .build-layer
zip -r9 ../lambda-layer.zip python/  # -9 = 最大圧縮
```

### 3. Layer ARNのキャッシュ

Layerの内容が変わっていない場合は再ビルドをスキップ：

```bash
# requirements-layer.txtのハッシュ値を計算
LAYER_HASH=$(md5sum requirements-layer.txt | awk '{print $1}')

# ハッシュ値をLayerの説明に含める
aws lambda publish-layer-version \
  --layer-name multicloud-auto-deploy-staging-dependencies \
  --description "Hash: $LAYER_HASH | Python 3.12" \
  --zip-file fileb://lambda-layer.zip \
  --compatible-runtimes python3.12 \
  --region ap-northeast-1
```

---

## 🔍 Layerの検証

### Layerの内容確認

```bash
# Layerをダウンロード
LAYER_ARN="arn:aws:lambda:ap-northeast-1:278280499340:layer:multicloud-auto-deploy-staging-dependencies:6"

# Layer URLを取得
LAYER_URL=$(aws lambda get-layer-version-by-arn \
  --arn "$LAYER_ARN" \
  --region ap-northeast-1 \
  --query 'Content.Location' \
  --output text)

# Layerをダウンロードして解凍
curl -o /tmp/layer.zip "$LAYER_URL"
unzip -l /tmp/layer.zip | head -30

# 特定のパッケージを検索
unzip -l /tmp/layer.zip | grep mangum
unzip -l /tmp/layer.zip | grep fastapi
```

### Lambda関数でのインポートテスト

```python
# Lambda関数のテストコード
import json

def handler(event, context):
    try:
        import fastapi
        import mangum
        import pydantic

        return {
            'statusCode': 200,
            'body': json.dumps({
                'status': 'ok',
                'packages': {
                    'fastapi': fastapi.__version__,
                    'mangum': mangum.__version__,
                    'pydantic': pydantic.__version__
                }
            })
        }
    except ImportError as e:
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }
```

---

## 📚 関連ドキュメント

- [環境ステータスレポート](./ENVIRONMENT_STATUS.md) - 現在の環境状態
- [環境診断ガイド](./ENVIRONMENT_DIAGNOSTICS.md) - トラブルシューティング
- [Lambda Layer 公開リソース](./LAMBDA_LAYER_PUBLIC_RESOURCES.md) - Klayersについて
- [AWS デプロイメントガイド](./AWS_DEPLOYMENT.md) - AWS全体のデプロイ手順

---

## 🎓 学習リソース

- [AWS Lambda Layers](https://docs.aws.amazon.com/lambda/latest/dg/configuration-layers.html)
- [AWS Lambda Powertools](https://docs.powertools.aws.dev/lambda/python/)
- [Mangum - AWS Lambda adapter for ASGI](https://mangum.io/)
- [FastAPI Deployment](https://fastapi.tiangolo.com/deployment/)

---

## 🔄 更新履歴

- **2026-02-17**: 初版作成
  - 3つの実装戦略を提案
  - ハイブリッドLayer構成の詳細化
  - 即座実行可能なコマンド集を追加
  - CI/CD統合手順を追加
