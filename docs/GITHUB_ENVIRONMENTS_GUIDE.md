# GitHub Environments 設定ガイド

> **目的**: 本番・ステージング・開発環境ごとにデプロイ承認ルールと環境変数を管理
>
> **ステータス**: ✅ **実装完了** (2026-02-28)

---

## 🎯 実装完了（2026-02-28）

✅ **Production 環境**

- 承認者: @PLAYER1-r7 (必須)
- 対応ブランチ: main のみ
- 環境変数: 10 個設定

✅ **Staging 環境**

- 承認: 不要
- 対応ブランチ: develop
- 環境変数: 10 個設定

✅ **Development 環境**

- 承認: 不要
- 対応ブランチ: すべて
- 環境変数: 7 個設定

---

## 📋 3 つの環境構成

このプロジェクトでは 3 つのデプロイ環境を管理します：

| 環境            | ブランチ                | 承認要件            | Cloud プロバイダー | 用途                       |
| --------------- | ----------------------- | ------------------- | ------------------ | -------------------------- |
| **production**  | `main` のみ             | ✅ 必須（Reviewer） | AWS / Azure / GCP  | 本番環境（ユーザー公開）   |
| **staging**     | `develop` + `feature/*` | ❌ 不要             | AWS / Azure / GCP  | ステージング環境（テスト） |
| **development** | 全ブランチ              | ❌ 不要             | ローカル / Dev環境 | 開発環境（個人テスト）     |

---

## 🔧 Web UI での設定

### ステップ 1: GitHub Settings を開く

1. リポジトリ → [Settings](https://github.com/PLAYER1-r7/multicloud-auto-deploy/settings)
2. 左サイドメニュー → **Environments**
3. **New environment** をクリック

### ステップ 2: Production 環境を作成

#### 環境名

```
Name: production
```

#### Protection Rules（保護ルール）

```
✅ Required reviewers
   → @PLAYER1-r7 (Owner のみ可)

✅ Deployment branches and tags
   → Include deployment branches and tags
   → Branch name pattern: main only
```

#### 環境変数

Production 環境用の環境変数を設定（本番用エンドポイント・認証情報など）：

```
AWS_ACCOUNT_ID=<本番 AWS Account ID>
AWS_REGION=us-east-1
AZURE_SUBSCRIPTION_ID=<本番 Azure Subscription ID>
AZURE_RESOURCE_GROUP=multicloud-auto-deploy-prod-rg
GCP_PROJECT_ID=<本番 GCP Project ID>
GCP_REGION=us-central1
API_GATEWAY_ENDPOINT=https://api.prod.ashnova.jp
FRONTEND_DOMAIN=prod.ashnova.jp
AUTH_DISABLED=false
LOG_LEVEL=INFO
```

#### Secrets（機密情報）

本番用の認証情報（後で GitHub Secrets から推奨）：

```
AWS_PROD_ACCESS_KEY_ID=***
AWS_PROD_SECRET_ACCESS_KEY=***
AZURE_PROD_CLIENT_ID=***
AZURE_PROD_CLIENT_SECRET=***
GCP_PROD_SERVICE_ACCOUNT=***
```

**💾 Save protection rules**

---

### ステップ 3: Staging 環境を作成

#### 環境名

```
Name: staging
```

#### Protection Rules

```
✅ Required reviewers: ❌ なし（開発スピード重視）

✅ Deployment branches and tags
   → Include deployment branches and tags
   → Branch name pattern: develop
```

#### 環境変数

Staging 用の環境変数：

```
AWS_ACCOUNT_ID=<ステージング AWS Account ID>
AWS_REGION=us-east-1
AZURE_SUBSCRIPTION_ID=<ステージング Azure Subscription ID>
AZURE_RESOURCE_GROUP=multicloud-auto-deploy-staging-rg
GCP_PROJECT_ID=<ステージング GCP Project ID>
GCP_REGION=us-central1
API_GATEWAY_ENDPOINT=https://api.staging.ashnova.jp
FRONTEND_DOMAIN=staging.ashnova.jp
AUTH_DISABLED=false
LOG_LEVEL=DEBUG
```

**💾 Save protection rules**

---

### ステップ 4: Development 環境を作成（オプション）

#### 環境名

```
Name: development
```

#### Protection Rules

```
✅ Required reviewers: ❌ なし

✅ Deployment branches and tags: ❌ なし
   （全ブランチから deploy 可能）
```

#### 環境変数

```
AWS_ACCOUNT_ID=<開発用 AWS Account ID>
API_GATEWAY_ENDPOINT=http://localhost:8000
AUTH_DISABLED=true
LOG_LEVEL=DEBUG
```

**💾 Save protection rules**

---

## 🔧 REST API での設定（CLI）

GitHub CLI で環境を管理することも可能です：

### Production 環境の作成

```bash
# 環境を作成・更新する場合は REST API を使用
curl -X PUT \
  -H "Authorization: token $(gh auth token)" \
  -H "Accept: application/vnd.github+json" \
  "https://api.github.com/repos/PLAYER1-r7/multicloud-auto-deploy/environments/production" \
  -d '{
    "wait_timer": 0,
    "reviewers": [
      {
        "type": "User",
        "id": <REVIEWER_USER_ID>
      }
    ],
    "deployment_branch_policy": {
      "protected_branches": false,
      "custom_branch_policies": true
    }
  }'
```

### 環境変数の設定

```bash
# 環境変数を設定
curl -X POST \
  -H "Authorization: token $(gh auth token)" \
  -H "Accept: application/vnd.github+json" \
  "https://api.github.com/repos/PLAYER1-r7/multicloud-auto-deploy/environments/production/variables" \
  -d '{
    "name": "AWS_ACCOUNT_ID",
    "value": "123456789012"
  }'
```

---

## 🚀 GitHub Actions での使用

### デプロイワークフロー例

`.github/workflows/deploy-prod.yml`:

```yaml
name: Deploy to Production

on:
  push:
    branches: [main]

jobs:
  deploy:
    name: Deploy to AWS/Azure/GCP
    runs-on: ubuntu-latest
    environment: production # ← 自動承認ゲート付き

    steps:
      - uses: actions/checkout@v4

      - name: Configure AWS credentials
        uses: aws-actions/configure-aws-credentials@v4
        with:
          aws-access-key-id: ${{ secrets.AWS_PROD_ACCESS_KEY_ID }}
          aws-secret-access-key: ${{ secrets.AWS_PROD_SECRET_ACCESS_KEY }}
          aws-region: ${{ vars.AWS_REGION }}

      - name: Configure Azure
        uses: azure/login@v1
        with:
          creds: ${{ secrets.AZURE_PROD_CLIENT_SECRET }}

      - name: Deploy to production
        run: |
          echo "🚀 Deploying to production..."
          bash scripts/deploy-production.sh

      - name: Notification
        if: success()
        run: |
          echo "✅ Production deployment successful"
          echo "API: ${{ vars.API_GATEWAY_ENDPOINT }}"
          echo "Frontend: ${{ vars.FRONTEND_DOMAIN }}"
```

### Staging へのデプロイ（承認不要）

`.github/workflows/deploy-staging.yml`:

```yaml
name: Deploy to Staging

on:
  push:
    branches: [develop]

jobs:
  deploy:
    runs-on: ubuntu-latest
    environment: staging # ← 承認ゲート なし

    steps:
      - uses: actions/checkout@v4
      - name: Deploy to staging
        run: bash scripts/deploy-staging.sh
```

---

## 📊 ワークフロー

```
develop ブランチに push
    ↓
GitHub Actions ワークフロー開始
    ↓
environment: staging → 承認なしでデプロイ
    ↓
staging にデプロイ完了 ✅

---

main ブランチに push
    ↓
GitHub Actions ワークフロー開始
    ↓
environment: production → 承認待ち ⏳
    ↓
Reviewer (@PLAYER1-r7) が承認
    ↓
production にデプロイ開始 🚀
    ↓
production デプロイ完了 ✅
```

---

## ⚠️ Protection Rules の確認

デプロイ前にルールが正しく設定されてるか確認：

```bash
# 環境一覧を確認
curl -s -H "Authorization: token $(gh auth token)" \
  "https://api.github.com/repos/PLAYER1-r7/multicloud-auto-deploy/environments" | jq '.environments[] | {name, protection_rules}'

# Production のルールを確認
curl -s -H "Authorization: token $(gh auth token)" \
  "https://api.github.com/repos/PLAYER1-r7/multicloud-auto-deploy/environments/production" | jq '.protection_rules'
```

---

## 🎯 注意点

### ⚠️ Production 環境は慎重に

- 本番環境へのデプロイには **必ず Reviewer 承認** が必須
- `main` ブランチからのみデプロイ可能
- デプロイ実行前に **テストと staging 検証を完了** すること
- ロールバック手順を事前に準備（緊急時対応用）

### ⚠️ Secret の管理

- 認証情報（API Key、Token など）は **Environment Secrets** に保管（GitHub が暗号化）
- ローカル `.env` ファイルにはコミットしない（`.gitignore` で除外）
- Secrets の定期ローテーションを実施

### ⚠️ 環境変数の上書き

- 同じ名前の環境変数が複数の場所（repository secrets、environment variables）に存在する場合、**environment variables** が優先される
- 環境ごとに異なる値を設定する場合は **environment variables** を使用

---

## 📝 チェックリスト

- [ ] Production 環境を作成（Reviewer 設定必須）
- [ ] Staging 環境を作成（Reviewer 不要）
- [ ] 各環境に必要な環境変数を設定
- [ ] 各環境に必要な Secrets を設定
- [ ] デプロイワークフロー（`.github/workflows/deploy-*.yml`）で `environment:` を指定
- [ ] Staging へのテストデプロイを実行
- [ ] Production へのデプロイフローを検証

---

## 📚 参考資料

- [GitHub Environments](https://docs.github.com/en/actions/deployment/targeting-different-environments)
- [Environment Protection Rules](https://docs.github.com/en/actions/deployment/targeting-different-environments/using-environments-for-deployment)
- [Environment Secrets](https://docs.github.com/en/actions/security-guides/encrypted-secrets#creating-encrypted-secrets-for-an-environment)
- [Deployment Status](https://docs.github.com/en/rest/deployments/statuses)
