# CI/CD セットアップガイド

このドキュメントでは、GitHub Actionsを使用したマルチクラウド自動デプロイのセットアップ方法を説明します。

## 目次
- [概要](#概要)
- [必要なシークレットの設定](#必要なシークレットの設定)
- [ワークフローの使用方法](#ワークフローの使用方法)
- [トラブルシューティング](#トラブルシューティング)

## 概要

このプロジェクトでは、以下のCI/CDワークフローを提供しています：

- **deploy-multicloud.yml**: Azure Container AppsとGCP Cloud Runへの統合デプロイメント
- **deploy-azure.yml**: Azure専用デプロイメント（Terraform使用）
- **deploy-gcp.yml**: GCP専用デプロイメント（Terraform使用）
- **deploy-aws.yml**: AWS専用デプロイメント

## 必要なシークレットの設定

GitHub リポジトリの Settings > Secrets and variables > Actions で以下のシークレットを設定してください。

### Azure Container Apps用

| シークレット名 | 説明 | 取得方法 |
|--------------|------|---------|
| `AZURE_CREDENTIALS` | Azure Service Principalの認証情報 | `az ad sp create-for-rbac --name "github-actions-mcad" --role contributor --scopes /subscriptions/{subscription-id}/resourceGroups/{resource-group} --sdk-auth` |
| `AZURE_CONTAINER_REGISTRY` | ACRのログインサーバー名 | 例: `mcadstagingacr.azurecr.io` |
| `AZURE_CONTAINER_REGISTRY_USERNAME` | ACRのユーザー名 | Azure Portal > Container Registry > Access keys |
| `AZURE_CONTAINER_REGISTRY_PASSWORD` | ACRのパスワード | Azure Portal > Container Registry > Access keys |
| `AZURE_RESOURCE_GROUP` | リソースグループ名 | 例: `multicloud-auto-deploy-staging-rg` |
| `AZURE_CONTAINER_APP_API` | APIのContainer App名 | 例: `mcad-staging-api` |
| `AZURE_CONTAINER_APP_FRONTEND` | FrontendのContainer App名 | 例: `mcad-staging-frontend` |

#### Azure Service Principalの作成

```bash
# サブスクリプションIDとリソースグループを環境変数に設定
SUBSCRIPTION_ID=$(az account show --query id -o tsv)
RESOURCE_GROUP="multicloud-auto-deploy-staging-rg"

# Service Principalを作成
az ad sp create-for-rbac \
  --name "github-actions-mcad" \
  --role contributor \
  --scopes /subscriptions/$SUBSCRIPTION_ID/resourceGroups/$RESOURCE_GROUP \
  --sdk-auth

# 出力されたJSONをGitHub SecretsのAZURE_CREDENTIALSに設定
```

#### Azure Container Registryの認証情報取得

```bash
# ACR名を指定
ACR_NAME="mcadstagingacr"

# Admin userを有効化（まだの場合）
az acr update --name $ACR_NAME --admin-enabled true

# 認証情報を取得
az acr credential show --name $ACR_NAME
```

### GCP Cloud Run用

| シークレット名 | 説明 | 取得方法 |
|--------------|------|---------|
| `GCP_CREDENTIALS` | GCPサービスアカウントキー（JSON） | GCP Console > IAM & Admin > Service Accounts |
| `GCP_PROJECT_ID` | GCPプロジェクトID | 例: `ashnova` |
| `GCP_ARTIFACT_REGISTRY_REPO` | Artifact Registryリポジトリ名 | 例: `mcad-staging-repo` |
| `GCP_CLOUD_RUN_API` | APIのCloud Runサービス名 | 例: `mcad-staging-api` |
| `GCP_CLOUD_RUN_FRONTEND` | FrontendのCloud Runサービス名 | 例: `mcad-staging-frontend` |

#### GCPサービスアカウントの作成

```bash
# プロジェクトIDを設定
PROJECT_ID="ashnova"
SERVICE_ACCOUNT_NAME="github-actions-mcad"

# サービスアカウントを作成
gcloud iam service-accounts create $SERVICE_ACCOUNT_NAME \
  --display-name="GitHub Actions MCAD" \
  --project=$PROJECT_ID

# 必要な権限を付与
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:$SERVICE_ACCOUNT_NAME@$PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/run.admin"

gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:$SERVICE_ACCOUNT_NAME@$PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/artifactregistry.writer"

gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:$SERVICE_ACCOUNT_NAME@$PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/iam.serviceAccountUser"

# サービスアカウントキーを作成（JSONファイル）
gcloud iam service-accounts keys create github-actions-key.json \
  --iam-account=$SERVICE_ACCOUNT_NAME@$PROJECT_ID.iam.gserviceaccount.com

# github-actions-key.jsonの内容をGitHub SecretsのGCP_CREDENTIALSに設定
cat github-actions-key.json
```

### AWS Lambda用（オプション）

| シークレット名 | 説明 |
|--------------|------|
| `AWS_ACCESS_KEY_ID` | AWSアクセスキーID |
| `AWS_SECRET_ACCESS_KEY` | AWSシークレットアクセスキー |
| `AWS_LAMBDA_FUNCTION_NAME` | Lambda関数名 |

## ワークフローの使用方法

### 自動デプロイ

`main`ブランチに以下のパスが変更されたコードをプッシュすると、自動的にデプロイが実行されます：

- `services/**`
- `.github/workflows/deploy-multicloud.yml`

```bash
git add .
git commit -m "feat: Update API endpoint"
git push origin main
```

### 手動デプロイ

GitHub Actionsページから手動でワークフローを実行できます：

1. GitHub リポジトリ > Actions タブ
2. `Deploy to Multi-Cloud (Azure & GCP)` を選択
3. `Run workflow` をクリック
4. オプションを選択：
   - **environment**: `staging` または `production`
   - **deploy_target**: `all`, `azure`, または `gcp`

### デプロイフロー

1. **Build Images**: 
   - APIとFrontendのDockerイメージをビルド
   - Azure ACRとGCP Artifact Registryにプッシュ

2. **Deploy Azure** (並列実行):
   - Azure Container AppsのAPIとFrontendを更新

3. **Deploy GCP** (並列実行):
   - GCP Cloud RunのAPIとFrontendを更新

4. **Health Check**:
   - デプロイされたAPIのヘルスチェック

## デプロイ先URL

### Staging環境

**Azure Container Apps:**
- API: https://mcad-staging-api.livelycoast-fa9d3350.japaneast.azurecontainerapps.io
- Frontend: https://mcad-staging-frontend.livelycoast-fa9d3350.japaneast.azurecontainerapps.io

**GCP Cloud Run:**
- API: https://mcad-staging-api-son5b3ml7a-an.a.run.app
- Frontend: https://mcad-staging-frontend-son5b3ml7a-an.a.run.app

## トラブルシューティング

### イメージのプッシュに失敗する

**問題**: `denied: requested access to the resource is denied`

**解決策**:
1. Container Registryの認証情報が正しいか確認
2. Service Principalに適切な権限があるか確認

```bash
# Azureの場合
az acr check-health --name <ACR_NAME> --yes

# GCPの場合
gcloud auth configure-docker asia-northeast1-docker.pkg.dev
```

### Container Appの更新に失敗する

**問題**: `ContainerAppNotFound`

**解決策**:
1. Container AppとResource Groupの名前が正しいか確認
2. Service Principalに適切な権限があるか確認

```bash
# Container Appの存在確認
az containerapp show \
  --name <APP_NAME> \
  --resource-group <RESOURCE_GROUP>
```

### Cloud Runのデプロイに失敗する

**問題**: `The user-provided container failed to start`

**解決策**:
1. ポート設定が正しいか確認（API: 8000, Frontend: 3002）
2. ログを確認

```bash
# Cloud Runのログ確認
gcloud logging read \
  "resource.type=cloud_run_revision AND resource.labels.service_name=<SERVICE_NAME>" \
  --limit 50
```

### ヘルスチェックが失敗する

**問題**: API起動に時間がかかり、タイムアウト

**解決策**:
1. ワークフローの`sleep`時間を延長
2. APIのヘルスチェックエンドポイントが正しく動作しているか確認

```bash
# 手動でヘルスチェック
curl https://<API_URL>/health
```

## 環境変数の管理

### GitHub Environments

本番環境とステージング環境で異なる設定を使用する場合：

1. Settings > Environments で環境を作成
2. 各環境にシークレットを設定
3. ワークフロー実行時に環境を選択

### ローカル開発

ローカル開発では`.env`ファイルを使用：

```bash
cp .env.example .env
# .envファイルを編集して必要な環境変数を設定
```

## セキュリティのベストプラクティス

1. **最小権限の原則**: Service Principalには必要最小限の権限のみを付与
2. **シークレットのローテーション**: 定期的にシークレットを更新
3. **環境分離**: 本番環境とステージング環境でリソースを分離
4. **監査ログ**: デプロイメントログを定期的に確認

## 関連ドキュメント

- [Production Deployment Guide](./PRODUCTION_DEPLOYMENT.md)
- [Azure Container Apps Documentation](https://learn.microsoft.com/azure/container-apps/)
- [GCP Cloud Run Documentation](https://cloud.google.com/run/docs)
- [GitHub Actions Documentation](https://docs.github.com/actions)
