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
- **対象パス**: `services/**`または`infrastructure/terraform/**`の変更時

## GitHub Secrets設定

各クラウドプロバイダーに必要なSecretsをGitHubリポジトリに設定してください。

### 設定場所

1. GitHubリポジトリのページを開く
2. **Settings** → **Secrets and variables** → **Actions**
3. **New repository secret** をクリック

---

### AWS Secrets

| Secret名 | 説明 | 取得方法 |
|---------|------|---------|
| `AWS_ACCESS_KEY_ID` | AWSアクセスキーID | IAMユーザーから取得 |
| `AWS_SECRET_ACCESS_KEY` | AWSシークレットアクセスキー | IAMユーザーから取得 |

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

### Azure Secrets

| Secret名 | 説明 | 取得方法 |
|---------|------|---------|
| `AZURE_CREDENTIALS` | Azure認証情報（JSON） | Service Principalから取得 |
| `ARM_CLIENT_ID` | Service PrincipalのクライアントID | Service Principalから取得 |
| `ARM_CLIENT_SECRET` | Service Principalのシークレット | Service Principalから取得 |
| `ARM_SUBSCRIPTION_ID` | AzureサブスクリプションID | `az account show` |
| `ARM_TENANT_ID` | AzureテナントID | `az account show` |
| `AZURE_API_URL` | バックエンドAPI URL（オプション） | デプロイ後に設定 |

**取得手順**:

```bash
# Service Principalの作成
az ad sp create-for-rbac \
  --name "github-actions-deploy" \
  --role Contributor \
  --scopes /subscriptions/YOUR_SUBSCRIPTION_ID \
  --sdk-auth

# 出力されるJSON全体を AZURE_CREDENTIALS に設定
# 出力から個別の値も取得して設定
```

**AZURE_CREDENTIALS の形式**:
```json
{
  "clientId": "00000000-0000-0000-0000-000000000000",
  "clientSecret": "xxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
  "subscriptionId": "00000000-0000-0000-0000-000000000000",
  "tenantId": "00000000-0000-0000-0000-000000000000"
}
```

---

### GCP Secrets

| Secret名 | 説明 | 取得方法 |
|---------|------|---------|
| `GCP_CREDENTIALS` | GCPサービスアカウントキー（JSON） | サービスアカウントから取得 |
| `GCP_PROJECT_ID` | GCPプロジェクトID | `gcloud config get-value project` |

**取得手順**:

```bash
# サービスアカウントの作成
gcloud iam service-accounts create github-actions-deploy \
  --display-name="GitHub Actions Deploy"

# Editorロールを付与
gcloud projects add-iam-policy-binding YOUR_PROJECT_ID \
  --member="serviceAccount:github-actions-deploy@YOUR_PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/editor"

# キーファイルの作成
gcloud iam service-accounts keys create key.json \
  --iam-account=github-actions-deploy@YOUR_PROJECT_ID.iam.gserviceaccount.com

# key.json の内容を GCP_CREDENTIALS に設定
cat key.json

# セキュリティのため、ローカルのキーファイルを削除
rm key.json
```

**必要な権限**:
- Cloud Run: 管理者
- Artifact Registry: 管理者
- Cloud Storage: 管理者
- Firestore: 管理者
- Compute Engine: 管理者（Load Balancer用）
- IAM: Service Account Admin

---

## ワークフロー説明

### AWS デプロイ (deploy-aws.yml)

**トリガー**:
- `main`ブランチへのプッシュ（`services/**`または`infrastructure/terraform/aws/**`の変更）
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
- `main`ブランチへのプッシュ（`services/**`または`infrastructure/terraform/azure/**`の変更）
- 手動実行

**ステップ**:
1. Azureログイン
2. Node.js・Python・Terraformのセットアップ
3. フロントエンドのビルド
4. Terraformでインフラデプロイ
5. Dockerイメージのビルドとプッシュ
6. Container Appの更新
7. フロントエンドのStorage Accountへのアップロード
8. 成功/失敗通知

**実行時間**: 約10-15分

---

### GCP デプロイ (deploy-gcp.yml)

**トリガー**:
- `main`ブランチへのプッシュ（`services/**`または`infrastructure/terraform/gcp/**`の変更）
- 手動実行

**ステップ**:
1. GCP認証
2. Node.js・Python・Terraformのセットアップ
3. Terraformでインフラデプロイ
4. Dockerイメージのビルドとプッシュ
5. Cloud Runサービスのデプロイ
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

### AWS デプロイが失敗する

**症状**: `Error: Could not load credentials from any providers`

**対処**:
```bash
# GitHub SecretsにAWS認証情報が正しく設定されているか確認
# IAMユーザーに必要な権限があるか確認
aws iam get-user --user-name satoshi
aws iam list-attached-user-policies --user-name satoshi
```

---

### Azure デプロイが失敗する

**症状**: `Error: AuthenticationFailed`

**対処**:
```bash
# Service Principalの認証情報を確認
az login --service-principal \
  -u $ARM_CLIENT_ID \
  -p $ARM_CLIENT_SECRET \
  --tenant $ARM_TENANT_ID

# Contributorロールがあるか確認
az role assignment list \
  --assignee $ARM_CLIENT_ID \
  --output table
```

---

### GCP デプロイが失敗する

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

---

### Docker イメージのプッシュが失敗する

**症状**: `denied: requested access to the resource is denied`

**対処**:

**Azure**:
```bash
# ACRへの認証を確認
az acr login --name <ACR_NAME>

# Service PrincipalにAcrPushロールがあるか確認
az role assignment list \
  --assignee $ARM_CLIENT_ID \
  --scope /subscriptions/$ARM_SUBSCRIPTION_ID/resourceGroups/*/providers/Microsoft.ContainerRegistry/registries/*
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

### Terraform Apply が失敗する

**症状**: `Error: Backend initialization required`

**対処**:
```bash
# Terraformの初期化
cd infrastructure/terraform/aws  # or azure, gcp
terraform init -upgrade

# ステートファイルが破損している場合
terraform state pull > backup.tfstate
terraform init -reconfigure
```

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
