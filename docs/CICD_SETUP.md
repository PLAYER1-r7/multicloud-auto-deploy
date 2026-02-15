# CI/CD Configuration Guide

GitHub Actionsによる自動デプロイの設定ガイド

## 📋 目次

- [概要](#概要)
- [GitHub Secrets設定](#github-secrets設定)
- [ワークフロー説明](#ワークフロー説明)
- [手動デプロイ](#手動デプロイ)
- [トラブルシューティング](#トラブルシューティング)

## 概要

このプロジェクトは、GitHub Actionsを使用してAWS、Azure、GCPへの自動デプロイを実現しています。

### デプロイトリガー

- **自動デプロイ**: `main`ブランチへのプッシュ時
- **手動デプロイ**: GitHub Actions UIからワークフロー実行時
- **対象パス**: `services/**`または`infrastructure/pulumi/**`の変更時

## GitHub Secrets設定

各クラウドプロバイダーに必要なSecretsをGitHubリポジトリに設定してください。

### 設定場所

1. GitHubリポジトリのページを開く
2. **Settings** → **Secrets and variables** → **Actions**
3. **New repository secret** をクリック

---

### AWS Secrets

| Secret名                | 説明                        | 取得方法            |
| ----------------------- | --------------------------- | ------------------- |
| `AWS_ACCESS_KEY_ID`     | AWSアクセスキーID           | IAMユーザーから取得 |
| `AWS_SECRET_ACCESS_KEY` | AWSシークレットアクセスキー | IAMユーザーから取得 |
| `AWS_ROLE_ARN`          | IAMロールARN（オプション）  | OIDC認証用          |

**取得手順**:
```bash
# IAMユーザーのアクセスキーを作成
aws iam create-access-key --user-name satoshi

# 出力からAccessKeyIdとSecretAccessKeyを取得
```

**必要な権限**:
- S3: フルアクセス（バケット作成・削除・アップロード）
- CloudFront: 管理権限
- Lambda: フルアクセス
- API Gateway: フルアクセス
- DynamoDB: フルアクセス
- IAM: ロール作成・ポリシーアタッチ

---

### Pulumi Secrets

| Secret名              | 説明                   | 取得方法             |
| --------------------- | ---------------------- | -------------------- |
| `PULUMI_ACCESS_TOKEN` | Pulumiアクセストークン | Pulumi Cloudから取得 |

**取得手順**:

1. [Pulumi Cloud](https://app.pulumi.com/)にログイン
2. **Settings** → **Access Tokens** をクリック
3. **Create token** をクリックして新しいトークンを作成
4. トークンをコピーして`PULUMI_ACCESS_TOKEN`に設定

**注意**: このトークンはすべてのPulumiベースのデプロイワークフローで必須です。

---

### Azure Secrets

| Secret名                | 説明                  | 取得方法          |
| ------------------------ | ----------------------- | -------------------------- |
| `AZURE_CREDENTIALS`      | Azure認証情報（JSON） | Service Principalから取得 |
| `AZURE_SUBSCRIPTION_ID`  | AzureサブスクリプションID | `az account show`          |
| `AZURE_RESOURCE_GROUP`   | リソースグループ名    | デプロイ後に設定         |

**取得手順**:

```bash
# 現在のAzureアカウント情報を確認
az account show --query "{SubscriptionId:id, TenantId:tenantId, Name:name}" --output table

# サブスクリプションIDを環境変数に設定
SUBSCRIPTION_ID=$(az account show --query id --output tsv)

# Service Principalの作成
az ad sp create-for-rbac \
  --name "github-actions-deploy" \
  --role Contributor \
  --scopes /subscriptions/$SUBSCRIPTION_ID \
  --sdk-auth

# 出力されるJSON全体を AZURE_CREDENTIALS に設定
# 出力から個別の値も取得:
# - subscriptionId → AZURE_SUBSCRIPTION_ID
```

**リソース名の取得**:
```bash
# リソースグループ名
az group list --query "[?contains(name, 'multicloud')].name" -o table

# 確認した値をSecretsに設定:
# AZURE_RESOURCE_GROUP: multicloud-auto-deploy-staging-rg
```

**Service PrincipalにACRアクセス権を付与**:
```bash
# ACRのリソースIDを取得
ACR_RESOURCE_ID=$(az acr show --name YOUR_ACR_NAME --query id --output tsv)

# Service PrincipalにAcrPushロールを付与（Dockerイメージのプッシュに必要）
az role assignment create \
  --assignee YOUR_CLIENT_ID \
  --role AcrPush \
  --scope $ACR_RESOURCE_ID
```

**注意**: 現在のワークフローでは、ACRの名前はPulumi出力から自動的に取得されますが、一部のワークフロー（deploy-multicloud.yml）では明示的な設定が必要です。

---

### GCP Secrets

| Secret名          | 説明                              | 取得方法                          |
| ----------------- | --------------------------------- | --------------------------------- |
| `GCP_CREDENTIALS` | GCPサービスアカウントキー（JSON） | サービスアカウントから取得        |
| `GCP_PROJECT_ID`  | GCPプロジェクトID                 | `gcloud config get-value project` |

**取得手順**:

```bash
# 現在のプロジェクトIDを確認
gcloud config get-value project

# 既存のサービスアカウントを確認
gcloud iam service-accounts list

# 新規サービスアカウントの作成
gcloud iam service-accounts create github-actions-deploy \
  --display-name="GitHub Actions Deploy"

# Editorロールを付与
gcloud projects add-iam-policy-binding YOUR_PROJECT_ID \
  --member="serviceAccount:github-actions-deploy@YOUR_PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/editor"

# キーファイルの作成（このJSON全体をGitHub Secretsに設定）
gcloud iam service-accounts keys create key.json \
  --iam-account=github-actions-deploy@YOUR_PROJECT_ID.iam.gserviceaccount.com

# key.json の内容を GCP_CREDENTIALS に設定
cat key.json

# セキュリティのため、ローカルのキーファイルを削除
rm key.json
```

**GCP_CREDENTIALS の形式**:
```json
{
  "type": "service_account",
  "project_id": "your-project-id",
  "private_key_id": "key-id",
  "private_key": "-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----\n",
  "client_email": "github-actions-deploy@your-project-id.iam.gserviceaccount.com",
  "client_id": "123456789",
  "auth_uri": "https://accounts.google.com/o/oauth2/auth",
  "token_uri": "https://oauth2.googleapis.com/token",
  "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
  "client_x509_cert_url": "https://www.googleapis.com/robot/v1/metadata/x509/..."
}
```

**既存のサービスアカウントから新しいキーを作成する場合**:
```bash
# サービスアカウントの一覧を取得
gcloud iam service-accounts list

# 特定のサービスアカウントに新しいキーを作成
gcloud iam service-accounts keys create key.json \
  --iam-account=YOUR_SERVICE_ACCOUNT_EMAIL

# 例: 
# gcloud iam service-accounts keys create key.json \
#   --iam-account=github-actions-deploy@ashnova.iam.gserviceaccount.com
```

**必要な権限**:
- Cloud Functions: 管理者
- Cloud Storage: 管理者
- Firestore: 管理者
- Compute Engine: 管理者（Load Balancer用）
- IAM: Service Account Admin

---

## ワークフロー説明

### AWS デプロイ (deploy-aws.yml)

**トリガー**:
- `main`ブランチへのプッシュ（`services/**`または`infrastructure/pulumi/aws/**`の変更）
- 手動実行

**ステップ**:
1. AWS認証情報の設定
2. Node.js・Pythonのセットアップ
3. デプロイスクリプトの実行
4. 成功/失敗通知

**実行時間**: 約5-10分

---

### Azure デプロイ (deploy-azure.yml)

**トリガー**:
- `main`ブランチへのプッシュ（`services/**`または`infrastructure/pulumi/azure/**`の変更）
- 手動実行

**ステップ**:
1. Azureログイン
2. Node.js・Python・Pulumiのセットアップ
3. フロントエンドのビルド
4. Pulumiでインフラデプロイ
5. DockerイメージのビルドとプッシュContainer App の更新
7. フロントエンドのStorage Accountへのアップロード
8. 成功/失敗通知

**実行時間**: 約10-15分

---

### GCP デプロイ (deploy-gcp.yml)

**トリガー**:
- `main`ブランチへのプッシュ（`services/**`または`infrastructure/pulumi/gcp/**`の変更）
- 手動実行

**ステップ**:
1. GCP認証
2. Node.js・Python・Pulumiのセットアップ
3. Pulumiでインフラデプロイ
4. Cloud Functionsパッケージのビルド
5. Cloud Functionsのデプロイ
6. IAMポリシーの設定
7. フロントエンドのビルドとデプロイ
8. Cloud Storageへのアップロード
9. 成功/失敗通知

**実行時間**: 約10-15分

---

## 手動デプロイ

### GitHub UI から実行

1. GitHubリポジトリの **Actions** タブを開く
2. 実行したいワークフローを選択（例: Deploy to AWS）
3. **Run workflow** ボタンをクリック
4. environment を選択（`staging`または`production`）
5. **Run workflow** で実行

### ローカルから実行

**act** というツールを使用してローカルでGitHub Actionsを実行できます：

```bash
# actのインストール
brew install act  # macOS
# または
curl https://raw.githubusercontent.com/nektos/act/master/install.sh | sudo bash

# ワークフローの実行
act -W .github/workflows/deploy-aws.yml

# Secretsを指定して実行
act -W .github/workflows/deploy-aws.yml \
  --secret AWS_ACCESS_KEY_ID=xxx \
  --secret AWS_SECRET_ACCESS_KEY=xxx
```

---

## トラブルシューティング

> 💡 **詳細なトラブルシューティング情報は [TROUBLESHOOTING.md](TROUBLESHOOTING.md) を参照してください**
> 
> 以下の問題と解決策が記載されています：
> - Azure認証問題（Service Principal、Terraform Wrapper、CLI認証競合）
> - GCPリソース競合（GCS Backend、既存リソースインポート）
> - フロントエンドAPI接続問題（ビルド順序、API URL設定）
> - 権限エラー（IAM、RBAC、Service Account）

### よくある問題（クイックリファレンス）

#### AWS デプロイが失敗する

**症状**: `Error: Could not load credentials from any providers`

**対処**:
```bash
# GitHub SecretsにAWS認証情報が正しく設定されているか確認
# IAMユーザーに必要な権限があるか確認
aws iam get-user --user-name satoshi
aws iam list-attached-user-policies --user-name satoshi
```

---

#### Azure デプロイが失敗する

**症状**: `Error: AuthenticationFailed`

**対処**:
```bash
# AZURE_CREDENTIALSから認証情報を抽出
export AZURE_CLIENT_ID=$(echo $AZURE_CREDENTIALS | jq -r '.clientId')
export AZURE_CLIENT_SECRET=$(echo $AZURE_CREDENTIALS | jq -r '.clientSecret')
export AZURE_TENANT_ID=$(echo $AZURE_CREDENTIALS | jq -r '.tenantId')

# Service Principalで認証
az login --service-principal \
  -u $AZURE_CLIENT_ID \
  -p $AZURE_CLIENT_SECRET \
  --tenant $AZURE_TENANT_ID

# Contributorロールがあるか確認
az role assignment list \
  --assignee $AZURE_CLIENT_ID \
  --output table
```

**よくある問題**:
- "Authenticating using the Azure CLI is only supported as a User" → [詳細](TROUBLESHOOTING.md#azure認証問題)

---

#### GCP デプロイが失敗する

**症状**: `Error: google: could not find default credentials`

**対処**:
```bash
# サービスアカウントキーが有効か確認
gcloud auth activate-service-account \
  --key-file=key.json

# 必要な権限があるか確認
gcloud projects get-iam-policy YOUR_PROJECT_ID \
  --flatten="bindings[].members" \
  --filter="bindings.members:serviceAccount:github-actions-deploy@*"
```

**よくある問題**:
- "Error 409: Resource already exists" → [詳細](TROUBLESHOOTING.md#gcpリソース競合)
- GCS Backendの設定とリソースインポート → [詳細](TROUBLESHOOTING.md#解決策永続的なremote-state)

---

#### フロントエンドがAPIに接続できない

**症状**: メッセージ送信が「送信中」のまま固まる

**原因**: フロントエンドビルド時にAPI URLが正しく設定されていない

**対処**: [詳細な解決策](TROUBLESHOOTING.md#フロントエンドapi接続問題)

**重要**: フロントエンドは必ずインフラデプロイ**後**にビルドすること

---

#### Docker イメージのプッシュが失敗する

**症状**: `denied: requested access to the resource is denied`

**対処**:

**Azure**:
```bash
# ACRへの認証を確認
az acr login --name <ACR_NAME>

# Service PrincipalにAcrPushロールがあるか確認
az role assignment list \
  --assignee $AZURE_CLIENT_ID \
  --scope /subscriptions/$AZURE_SUBSCRIPTION_ID/resourceGroups/*/providers/Microsoft.ContainerRegistry/registries/*
```

**GCP**:
```bash
# Artifact Registryの認証を確認
gcloud auth configure-docker asia-northeast1-docker.pkg.dev

# サービスアカウントに権限があるか確認
gcloud projects get-iam-policy YOUR_PROJECT_ID \
  --flatten="bindings[].members" \
  --filter="bindings.role:roles/artifactregistry.writer"
```

---

#### Pulumi Up が失敗する

**症状**: `error: could not load plugin`

**対処**:
```bash
# Pulumiプラグインの更新
cd infrastructure/pulumi/aws  # or azure, gcp
pulumi plugin install

# スタックの確認
pulumi stack ls
pulumi config
```

#### GCP Pulumi State が永続化されない

**症状**: 毎回 "Resource already exists" エラーが発生

**解決策**: Pulumi Backend（GCS/S3/Azure Blob）を設定

```bash
# GCS Backendの設定
pulumi login gs://multicloud-auto-deploy-pulumi-state
  --uniform-bucket-level-access

# 既存リソースのインポート
./scripts/import-gcp-resources.sh
```

詳細は [TROUBLESHOOTING.md - GCPリソース競合](TROUBLESHOOTING.md#gcpリソース競合) を参照

---

## 環境変数のカスタマイズ

各ワークフローファイルの`env`セクションで設定をカスタマイズできます：

```yaml
env:
  AWS_REGION: us-east-1        # 変更可能
  AZURE_REGION: japaneast      # 変更可能
  GCP_REGION: asia-northeast1  # 変更可能
  NODE_VERSION: "18"
  PYTHON_VERSION: "3.11"
```

---

## セキュリティのベストプラクティス

1. **最小権限の原則**
   - 各Service AccountやIAMユーザーには必要最小限の権限のみ付与

2. **キーのローテーション**
   - 定期的にアクセスキーやサービスアカウントキーを更新

3. **環境の分離**
   - staging環境とproduction環境でSecretsを分ける

4. **監査ログ**
   - デプロイアクティビティのログを記録・監視

5. **ブランチ保護**
   - `main`ブランチへの直接プッシュを制限
   - プルリクエストレビューを必須化

---

## 次のステップ

- [ ] GitHub Secretsの設定
- [ ] 初回の手動デプロイテスト
- [ ] ブランチ保護ルールの設定
- [ ] Slack/Discord等への通知統合
- [ ] 自動テストの追加
- [ ] ステージング環境でのE2Eテスト
