# マルチクラウド関数デプロイサイズ最適化ガイド

> **AIエージェント向けメモ**: Lambda / Azure Functions / Cloud Run のパッケージサイズ最適化手順。


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

### 🚀 アプローチ 2: AWS Lambda レイヤーの活用（推奨）

AWS では、公開 Lambda レイヤー（Klayers）を使用して、さらにサイズを削減：

#### Klayers とは

[Klayers](https://github.com/keithrozario/Klayers) は、人気の Python ライブラリを Lambda Layer 形式で提供するコミュニティプロジェクトです。

- 🌐 公式サイト: https://api.klayers.cloud/
- 📚 GitHub: https://github.com/keithrozario/Klayers

#### 利用可能なレイヤー

| パッケージ | Klayers対応 | 説明 |
|-----------|------------|------|
| fastapi | ✅ | FastAPI フレームワーク（Pydantic含む） |
| mangum | ✅ | FastAPI → Lambda アダプター |
| python-jose | ✅ | JWT 検証 |
| requests | ✅ | HTTP クライアント |

## 実装詳細

### AWS Lambda

**最適化前:**
- 全依存関係を含む zip: ~15-20 MB

**最適化後:**
- Klayers を使用: ~100-500 KB（アプリケーションコードのみ）

**実装:**

1. `requirements-aws.txt` には Klayers で提供されない依存関係のみ記載：

```txt
# Required dependencies not in Klayers
pydantic-settings==2.5.2
python-multipart==0.0.9
pyjwt==2.9.0

# AWS-specific
boto3==1.35.0
```

2. Pulumi で Klayers ARN を指定：

```python
klayers_arns = [
    "arn:aws:lambda:ap-northeast-1:770693421928:layer:Klayers-p312-fastapi:5",
    "arn:aws:lambda:ap-northeast-1:770693421928:layer:Klayers-p312-mangum:3",
    "arn:aws:lambda:ap-northeast-1:770693421928:layer:Klayers-p312-python-jose:4",
    "arn:aws:lambda:ap-northeast-1:770693421928:layer:Klayers-p312-requests:10",
]
```

**注:** 最新の ARN は https://api.klayers.cloud/ で確認できます。

詳細: [LAMBDA_LAYER_PUBLIC_RESOURCES.md](LAMBDA_LAYER_PUBLIC_RESOURCES.md)

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

| クラウド | 最適化前 | 最適化後 | 削減率 |
|---------|---------|---------|--------|
| AWS Lambda | ~15-20 MB | ~0.5 MB | **97%** ⭐ |
| Azure Functions | ~50-60 MB | ~30-40 MB | **30-40%** |
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

1. **公開レイヤーを優先**
   - Klayers で利用可能な依存関係は使用しない
   - カスタムレイヤーのビルドを避ける

2. **Lambda レイヤーの制限に注意**
   - 最大 5 レイヤー
   - 解凍後の合計サイズ: 250 MB 以下

3. **定期的に ARN を更新**
   - https://api.klayers.cloud/ で最新版を確認

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
- 制限: 50 MB (zip), 250 MB (解凍後)
- 解決: より多くの依存関係を Klayers に移行

**Azure Functions:**
- 制限: なし（ただし大きいと遅い）
- 解決: リモートビルドを使用

**GCP Cloud Functions:**
- 制限: 100 MB (zip), 500 MB (解凍後)
- 解決: 不要なファイルを削除、ソースディレクトリデプロイを検討

## 参考リンク

- [Klayers 公式サイト](https://api.klayers.cloud/)
- [AWS Lambda レイヤー](https://docs.aws.amazon.com/lambda/latest/dg/configuration-layers.html)
- [Azure Functions デプロイ](https://learn.microsoft.com/azure/azure-functions/functions-deployment-technologies)
- [GCP Cloud Functions デプロイ](https://cloud.google.com/functions/docs/deploying/filesystem)

## まとめ

✅ **実装済み:**
- クラウド別 requirements ファイル
- AWS: Klayers による大幅なサイズ削減（97%）
- Azure/GCP: 不要な依存関係の除外（30-40% 削減）
- 積極的なファイルクリーンアップ

🎯 **今後の改善:**
- Azure: リモートビルドの活用
- GCP: ソースディレクトリデプロイ
- 全体: Docker コンテナイメージの検討
