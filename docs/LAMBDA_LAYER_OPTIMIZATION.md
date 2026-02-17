# Lambda Layer による最適化ガイド

## 概要

Lambda関数のデプロイサイズを削減するために、Lambda Layerを使用して依存関係とアプリケーションコードを分離します。

**🌟 推奨: Klayers（公開Lambda Layer）を使用することで、さらに効率的なデプロイが可能です！**

詳細は [LAMBDA_LAYER_PUBLIC_RESOURCES.md](LAMBDA_LAYER_PUBLIC_RESOURCES.md) を参照してください。

### 最適化前の問題

- **パッケージサイズ**: 50MB以上（すべての依存関係を含む）
- **デプロイ方法**: S3経由でのアップロードが必須
- **デプロイ時間**: S3アップロード + Lambda更新で遅い
- **非効率**: 依存関係が変わらなくても毎回アップロード

### 最適化後のメリット

- **パッケージサイズ**: 数MB（アプリケーションコードのみ）
- **デプロイ方法**: 直接アップロード可能（50MB未満）
- **デプロイ時間**: 数秒で完了
- **効率化**: 依存関係は Layer で管理、コード変更時のみ更新

## アーキテクチャ

```
Lambda Function (軽量)
├── app/              # アプリケーションコード (~2-5MB)
│   ├── main.py
│   ├── auth.py
│   ├── config.py
│   └── ...
└── index.py

Lambda Layer (依存関係)
└── python/           # 依存関係 (~20-40MB)
    ├── fastapi/
    ├── pydantic/
    ├── mangum/
    ├── jwt/
    └── ...
```

## セットアップ手順

### オプションA: Klayers を使用（推奨）

**メリット:**
- ✅ ビルド不要（即座にデプロイ可能）
- ✅ メンテナンス不要（コミュニティが管理）
- ✅ 最新版に簡単に更新可能

```bash
# Klayers ARN は https://api.klayers.cloud/ で確認できます

# Pulumi で use_klayers=true に設定（デフォルト）
cd infrastructure/pulumi/aws/simple-sns
pulumi config set use_klayers true
pulumi up

# または GitHub Actions で use_klayers を true に設定（デフォルト）
```

詳細は [LAMBDA_LAYER_PUBLIC_RESOURCES.md](LAMBDA_LAYER_PUBLIC_RESOURCES.md) を参照。

### オプションB: カスタム Layer を使用

**メリット:**
- ✅ 完全な制御（特定バージョンの使用）
- ✅ サイズ最適化（必要なものだけ）
- ✅ プライベート環境での使用

### 1. Lambda Layer のビルド

```bash
cd /workspaces/ashnova/multicloud-auto-deploy
./scripts/build-lambda-layer.sh
```

このスクリプトは以下を実行します：
- AWS専用の依存関係のみをインストール
- boto3/botocore は除外（Lambda ランタイムに含まれる）
- Azure/GCP SDK は除外（AWS では不要）
- テストファイルとドキュメントを削除してサイズ削減
- `services/api/lambda-layer.zip` を生成

### 2. Pulumi でカスタム Layer を使用

```bash
cd infrastructure/pulumi/aws/simple-sns

# カスタム Layer を使用するように設定
pulumi config set use_klayers false

# Layer を含めてインフラをデプロイ
pulumi up
```

Pulumi は自動的に：
- カスタム Lambda Layer を作成
- Lambda 関数にアプリケーションコードのみをデプロイ
- Layer を Lambda 関数にアタッチ

### 3. GitHub Actions で自動デプロイ

```bash
# GitHub Actions ワークフローをトリガー
gh workflow run deploy-aws.yml
```

## CI/CD での使用

### Klayers を使用する場合（推奨・デフォルト）

GitHub Actions ワークフローは自動的に：

1. **ARN の取得**: Klayers の最新 ARN を使用
2. **アプリケーションコードのパッケージング**: コードのみを ZIP 化
3. **Lambda 関数の更新**: 
   - パッケージが 50MB 未満: 直接アップロード ✅
   - パッケージが 50MB 以上: S3 経由（フォールバック）
4. **Klayers のアタッチ**: 公開 Layer を Lambda に接続

```yaml
# GitHub Actions でのトリガー例
name: Deploy
on:
  workflow_dispatch:
    inputs:
      use_klayers:
        description: "Use Klayers (public Lambda Layers)"
        default: true  # デフォルトで Klayers を使用
```

### カスタム Layer を使用する場合

GitHub Actions ワークフローで `use_klayers: false` を選択：

1. **Layer のビルド**: `build-lambda-layer.sh` を実行
2. **アプリケーションコードのパッケージング**: コードのみを ZIP 化
3. **カスタム Layer のデプロイ**: Lambda Layer として公開
4. **Lambda 関数の更新**: 直接アップロードまたは S3 経由
5. **Layer のアタッチ**: カスタム Layer を Lambda に接続

## Layer に含まれる依存関係

```
fastapi==0.115.0
pydantic==2.9.0
pydantic-settings==2.5.2
python-jose[cryptography]==3.3.0
python-multipart==0.0.9
pyjwt==2.9.0
mangum==0.17.0
requests==2.32.3
```

### 除外される依存関係

- **boto3/botocore**: Lambda ランタイムに含まれる
- **Azure SDK**: AWS では不要
- **GCP SDK**: AWS では不要
- **PostgreSQL/SQLAlchemy**: DynamoDB のみ使用

## サイズ比較

### 最適化前

```
Lambda パッケージ: 65MB (コード + 全依存関係)
└── S3 経由デプロイ必須
```

### 最適化後

```
Lambda パッケージ: 3MB (コードのみ)
├── 直接アップロード可能
└── Layer: 25MB (依存関係)
    └── 依存関係更新時のみ再デプロイ
```

## トラブルシューティング

### Layer が見つからないエラー

```bash
# Layer を再ビルド
./scripts/build-lambda-layer.sh

# Layer が作成されたか確認
ls -lh services/api/lambda-layer.zip
```

### Lambda 関数でモジュールが見つからない

```bash
# Layer が正しくアタッチされているか確認
aws lambda get-function-configuration \
  --function-name multicloud-auto-deploy-staging-api \
  --query 'Layers[*].Arn'
```

### Layer サイズが大きすぎる

Lambda Layer の制限:
- **ZIP サイズ**: 50MB
- **解凍後サイズ**: 250MB

サイズ削減方法:
1. `build-lambda-layer.sh` で不要なファイルを削除
2. `--no-deps` オプションで余分な依存関係を除外
3. テストファイルとドキュメントを削除

## ベストプラクティス

### 1. Layer の更新頻度を減らす

- 依存関係のバージョンを固定
- アプリケーションコードの変更時は Lambda のみ更新
- 依存関係の変更時のみ Layer を更新

### 2. Layer のバージョン管理

```bash
# Layer のバージョンを確認
aws lambda list-layer-versions \
  --layer-name multicloud-auto-deploy-staging-dependencies

# 古いバージョンを削除
aws lambda delete-layer-version \
  --layer-name multicloud-auto-deploy-staging-dependencies \
  --version-number 1
```

### 3. 環境ごとに Layer を分離

```yaml
# staging 環境
LAYER_NAME: multicloud-auto-deploy-staging-dependencies

# production 環境
LAYER_NAME: multicloud-auto-deploy-production-dependencies
```

## 参考リンク

- [Lambda Layer 公開リソース活用ガイド](LAMBDA_LAYER_PUBLIC_RESOURCES.md) ⭐ **推奨**
- [Klayers GitHub](https://github.com/keithrozario/Klayers)
- [Klayers API](https://api.klayers.cloud/)
- [AWS Lambda Layers Documentation](https://docs.aws.amazon.com/lambda/latest/dg/configuration-layers.html)
- [Lambda デプロイパッケージ](https://docs.aws.amazon.com/lambda/latest/dg/python-package.html)
- [Lambda のクォータ](https://docs.aws.amazon.com/lambda/latest/dg/gettingstarted-limits.html)

## まとめ

### 推奨アプローチ

**🌟 Klayers（公開 Layer）を使用することを強く推奨します**

Lambda Layer を使用することで：

✅ デプロイサイズを **65MB → 3MB** に削減  
✅ デプロイ時間を **数分 → 数秒** に短縮  
✅ S3 アップロードを **不要** に  
✅ 依存関係の管理を **分離** して効率化  
✅ ビルド時間を **ゼロ** に（Klayers使用時）  

**選択基準:**

| シナリオ | 推奨アプローチ |
|---------|---------------|
| 通常の開発・本番環境 | **Klayers** ✅ |
| 迅速なプロトタイピング | **Klayers** ✅ |
| 特定バージョンが必要 | カスタム Layer |
| プライベート依存関係 | カスタム Layer |
| サイズを極限まで削減 | カスタム Layer |

詳細は [Lambda Layer 公開リソース活用ガイド](LAMBDA_LAYER_PUBLIC_RESOURCES.md) を参照してください。
