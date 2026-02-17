# マルチクラウド関数デプロイサイズ最適化ガイド

## 概要

AWS、Azure、GCP の関数サービス（Lambda、Functions、Cloud Functions）のデプロイパッケージサイズを最小化するための戦略と実装方法を説明します。

## 問題

元の `requirements.txt` には全クラウドプロバイダーの依存関係が含まれていました：

```txt
# AWS
boto3==1.35.0
mangum==0.17.0

# Azure
azure-cosmos==4.8.0
azure-storage-blob==12.23.0
azure-identity==1.18.0
azure-functions==1.20.0

# GCP
google-cloud-firestore==2.19.0
google-cloud-storage==2.18.0
functions-framework==3.5.0
```

これにより、各クラウドで不要な依存関係もデプロイされ、パッケージサイズが肥大化していました。

## 最適化戦略

### 🎯 アプローチ 1: クラウド別 requirements ファイル

各クラウドプロバイダー専用の requirements ファイルを作成：

- `requirements-aws.txt` - AWS Lambda 専用
- `requirements-azure.txt` - Azure Functions 専用
- `requirements-gcp.txt` - GCP Cloud Functions 専用

### 🚀 アプローチ 2: AWS Lambda カスタムレイヤーの活用（推奨）

AWS では、カスタム Lambda レイヤーを使用して、サイズを削減：

#### カスタムレイヤーの利点

- ✅ **確実に動作**: パブリックレイヤーのアクセス制限問題なし
- ✅ **完全な制御**: 依存関係のバージョンを固定可能
- ✅ **サイズ最適化**: 必要なパッケージのみ含める
- ✅ **直接アップロード**: 50MB未満でS3不要
- ✅ **低レイテンシー**: 同一アカウント内でのアクセス

#### レイヤーに含まれる依存関係

| パッケージ       | バージョン | 説明                        |
| ---------------- | ---------- | --------------------------- |
| fastapi          | 0.115.0    | FastAPI フレームワーク      |
| pydantic         | 2.9.0      | データバリデーション        |
| mangum           | 0.17.0     | FastAPI → Lambda アダプター |
| python-jose      | 3.3.0      | JWT 検証                    |
| pyjwt            | 2.9.0      | JWT 処理                    |
| requests         | 2.32.3     | HTTP クライアント           |
| python-multipart | 0.0.9      | ファイルアップロード        |

## 実装詳細

### AWS Lambda

**最適化前:**

- 全依存関係を含む zip: ~58MB（S3経由デプロイ必須）

**最適化後:**

- カスタムレイヤーを使用: ~78KB（アプリケーションコードのみ、直接アップロード可能）
- レイヤーサイズ: ~8-10MB

**実装:**

1. `requirements-layer.txt` にレイヤーの依存関係を記載：

```txt
# FastAPI Core
fastapi==0.115.0
pydantic==2.9.0
pydantic-settings==2.5.2

# Lambda adapter
mangum==0.17.0

# Auth & JWT
python-jose[cryptography]==3.3.0
pyjwt==2.9.0

# HTTP client
requests==2.32.3

# File upload support
python-multipart==0.0.9

# Note: boto3 excludes (pre-installed in Lambda runtime)
```

2. `requirements-aws.txt` は空（全て Layer に含まれる）：

```txt
# All dependencies are in Lambda Layer
# boto3 is pre-installed in Lambda runtime
```

3. レイヤーをビルド：

```bash
cd /workspaces/ashnova/multicloud-auto-deploy
./scripts/build-lambda-layer.sh
```

4. CI/CDで自動デプロイ：

```yaml
- name: Deploy Lambda Layer
  run: |
    LAYER_VERSION_ARN=$(aws lambda publish-layer-version \
      --layer-name multicloud-auto-deploy-staging-dependencies \
      --description "Dependencies for FastAPI + Mangum + JWT (Python 3.12)" \
      --zip-file fileb://multicloud-auto-deploy/services/api/lambda-layer.zip \
      --compatible-runtimes python3.12 \
      --region ap-northeast-1 \
      --query LayerVersionArn \
      --output text)
```

### Azure Functions

**最適化前:**

- 全依存関係を含む zip: ~50-60 MB

**最適化後:**

- Azure 専用依存関係のみ: ~30-40 MB（約 30-40% 削減）

**実装:**

1. `requirements-azure.txt` には Azure 関連依存関係のみ記載：

```txt
# FastAPI Core
fastapi==0.115.0
pydantic==2.9.0
pydantic-settings==2.5.2

# Azure-specific
azure-cosmos==4.8.0
azure-storage-blob==12.23.0
azure-identity==1.18.0
azure-functions==1.20.0
```

2. GitHub Actions でクリーンアップを強化：

```yaml
# Install Azure-specific dependencies only
pip install --target .deployment --no-cache-dir -r requirements-azure.txt

# Aggressive cleanup
find .deployment -type d -name "__pycache__" -exec rm -rf {} +
find .deployment -type d -name "tests" -exec rm -rf {} +
find .deployment -type d -name "*.dist-info" -exec rm -rf {} +
find .deployment -type f -name "*.pyc" -delete
```

### GCP Cloud Functions

**最適化前:**

- 全依存関係を含む zip: ~50-60 MB

**最適化後:**

- GCP 専用依存関係のみ: ~30-40 MB（約 30-40% 削減）

**実装:**

1. `requirements-gcp.txt` には GCP 関連依存関係のみ記載：

```txt
# FastAPI Core
fastapi==0.115.0
pydantic==2.9.0
pydantic-settings==2.5.2

# GCP-specific
google-cloud-firestore==2.19.0
google-cloud-storage==2.18.0
functions-framework==3.5.0
```

2. GitHub Actions で最適化されたパッケージング：

```yaml
# Install GCP-specific dependencies only
pip install --target .deployment --no-cache-dir -r requirements-gcp.txt

# Create optimized ZIP with maximum compression
zip -r9 -q ../function-source.zip .
```

## サイズ比較

| クラウド            | 最適化前  | 最適化後  | 削減率     |
| ------------------- | --------- | --------- | ---------- |
| AWS Lambda          | ~15-20 MB | ~0.5 MB   | **97%** ⭐ |
| Azure Functions     | ~50-60 MB | ~30-40 MB | **30-40%** |
| GCP Cloud Functions | ~50-60 MB | ~30-40 MB | **30-40%** |

## さらなる最適化オプション

### Azure Functions

1. **リモートビルドの活用**

```yaml
env:
  SCM_DO_BUILD_DURING_DEPLOYMENT: "true"
```

requirements.txt のみをデプロイし、Azure 側でビルドする方法。

2. **Docker コンテナの使用**

Premium プランで Docker コンテナイメージを使用し、レイヤーキャッシュを活用。

### GCP Cloud Functions

1. **ソースディレクトリデプロイ**

ZIP の代わりに、requirements.txt とソースコードを直接指定：

```bash
gcloud functions deploy FUNCTION_NAME \
  --source=services/api \
  --runtime=python312
```

GCP が自動的に最適化されたビルドを実行。

2. **Cloud Run への移行**

Cloud Functions Gen2 は内部的に Cloud Run を使用。コンテナイメージを直接デプロイすることで、より細かい最適化が可能。

## ベストプラクティス

### 📋 共通

1. **不要なファイルを削除**
   - `__pycache__`
   - `*.pyc`, `*.pyo`
   - `tests/` ディレクトリ
   - `*.dist-info` ディレクトリ
   - Documentation files

2. **最大圧縮を使用**

   ```bash
   zip -r9 package.zip .
   ```

3. **クラウド固有の依存関係のみをインストール**
   - AWS: `requirements-aws.txt`
   - Azure: `requirements-azure.txt`
   - GCP: `requirements-gcp.txt`

### 🎯 AWS 固有

1. **カスタムレイヤーの活用**
   - `scripts/build-lambda-layer.sh` でレイヤーをビルド
   - 依存関係のバージョンを固定
   - boto3をレイヤーから除外（Lambdaランタイムに含まれる）

2. **Lambda レイヤーの制限に注意**
   - 最大 5 レイヤー
   - 解凍後の合計サイズ: 250 MB 以下

3. **直接ZIPアップロードを優先**
   - 50MB未満: 直接アップロード（高速）
   - 50MB以上: S3経由（遅い）
   - アプリケーションコードのみで50MB未満を維持

### ☁️ Azure 固有

1. **Flex Consumption プランを活用**
   - 高速なコールドスタート
   - 効率的なスケーリング

2. **App Settings で環境変数を管理**
   - デプロイパッケージにシークレットを含めない

### 🌐 GCP 固有

1. **Cloud Build を活用**
   - 自動的な依存関係解決
   - キャッシュによる高速ビルド

2. **Gen2 を使用**
   - Cloud Run ベースで効率的
   - より大きなメモリとタイムアウト

## トラブルシューティング

### 依存関係の競合

**問題:** クラウド固有の requirements ファイルで依存関係が不足

**解決策:**

1. ローカルでテスト

   ```bash
   pip install -r requirements-aws.txt
   python -c "import app.main"
   ```

2. 不足している依存関係を追加

### デプロイサイズ超過

**AWS Lambda:**

- 制限: 50 MB (zip 直接アップロード), 250 MB (解凍後)
- 解決1: より多くの依存関係をカスタムレイヤーに移行
- 解決2: boto3をレイヤーから除外（Lambdaランタイムに含まれる）
- 解決3: 不要なファイルを削除（テスト、ドキュメント、.pycなど）

**Azure Functions:**

- 制限: なし（ただし大きいと遅い）
- 解決: リモートビルドを使用

**GCP Cloud Functions:**

- 制限: 100 MB (zip), 500 MB (解凍後)
- 解決: 不要なファイルを削除、ソースディレクトリデプロイを検討

## 参考リンク

- [AWS Lambda レイヤー](https://docs.aws.amazon.com/lambda/latest/dg/configuration-layers.html)
- [AWS Lambda Powertools](https://docs.powertools.aws.dev/lambda/python/)
- [Azure Functions デプロイ](https://learn.microsoft.com/azure/azure-functions/functions-deployment-technologies)
- [GCP Cloud Functions デプロイ](https://cloud.google.com/functions/docs/deploying/filesystem)

## まとめ

✅ **実装済み:**

- クラウド別 requirements ファイル
- AWS: カスタムレイヤーによる大幅なサイズ削減（~99%）
- AWS: 直接ZIPアップロード（S3不要）
- Azure/GCP: 不要な依存関係の除外（30-40% 削減）
- 積極的なファイルクリーンアップ

🎯 **今後の改善:**

- Azure: リモートビルドの活用
- GCP: ソースディレクトリデプロイ
- 全体: Docker コンテナイメージの検討
