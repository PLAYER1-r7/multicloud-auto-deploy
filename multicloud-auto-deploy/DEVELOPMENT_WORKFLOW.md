# 開発ワークフロー

## 概要

このプロジェクトは、2ブランチ構成の開発フローを採用しています。

## ブランチ戦略

- **develop** - 開発ブランチ（staging環境に自動デプロイ）
- **main** - 本番ブランチ（production環境に自動デプロイ）
- **feature/xxx** - 機能開発ブランチ（ローカルのみ、pushしない）

## 開発フロー

```
feature/xxx (local) → ローカル開発・コミット（pushしない）
    ↓ 開発完了、developにマージ
develop → push → staging自動デプロイ（動作確認）
    ↓ 確認OK、mainにマージ
main → push → production自動デプロイ（本番リリース）
```

## ステップ別ガイド

### 1. 機能開発開始

```bash
# developブランチから最新を取得
git checkout develop
git pull origin develop

# featureブランチを作成
git checkout -b feature/your-feature-name
```

### 2. ローカル開発

```bash
# コードを編集
# テストを実行
# コミット（ローカルのみ、pushしない）
git add .
git commit -m "feat: add new feature"

# ローカル環境でテスト
docker compose up -d
# テスト実行...

# コミットは何度でもOK（pushしない限りデプロイされない）
```

### 3. Staging環境で確認（developにマージ）

```bash
# 開発完了、developにマージ
git checkout develop
git pull origin develop
git merge feature/your-feature-name

# developにpush → staging自動デプロイ
git push origin develop
```

**自動実行されるもの：**
- `services/**` または `infrastructure/**` が変更された場合
- AWS/Azure/GCP の該当するデプロイワークフローが**staging環境**に自動デプロイ

**GitHub Actionsで確認：**
- https://github.com/PLAYER1-r7/multicloud-auto-deploy/actions
- 実行状況とログを確認

### 4. Production環境へリリース（mainにマージ）

Staging環境で問題なければ、mainにマージしてproductionへリリース：

```bash
# developで最終確認完了
git checkout main
git pull origin main
git merge develop

# mainにpush → production自動デプロイ
git push origin main
```

**重要：mainへのpush = production環境への本番リリースです**

### 5. 緊急時の手動デプロイ

必要に応じて、GitHub ActionsのUIから手動でデプロイ可能：

1. https://github.com/PLAYER1-r7/multicloud-auto-deploy/actions
2. 該当するワークフロー（Deploy to AWS/Azure/GCPなど）を選択
3. 「Run workflow」ボタンをクリック
4. Branch: 対象ブランチを選択
5. Environment: `staging` または `production` を選択
6. 「Run workflow」を実行

## トリガー条件

### 自動デプロイ

#### Staging環境
- **ブランチ**: `develop`
- **トリガー**: `develop` ブランチへのpush
- **対象パス**:
  - `services/**` → APIデプロイ
  - `infrastructure/**` → インフラデプロイ
  - `services/frontend_react/**` → フロントエンドデプロイ
  - `static-site/**` → ランディングページデプロイ

#### Production環境
- **ブランチ**: `main`
- **トリガー**: `main` ブランチへのpush
- **対象パス**: staging環境と同じ
- **⚠️ 重要**: mainへのpushは即座にproduction環境へデプロイされます

### 手動デプロイ

- GitHub Actions UI から workflow_dispatch で実行
- Environment を選択可能: `staging` または `production`
- 任意のブランチから実行可能

## 注意事項

### ⚠️ Main = Production環境

- **mainブランチへのpush = production本番リリース**
- mainブランチは常に安定版を保つ
- 開発中の機能はdevelopブランチで管理

### 🔄 ローカル開発は自由にコミット

- Feature ブランチでコミットを重ねても、pushしない限りデプロイされません
- 開発中は好きなだけコミットして構いません

### 🚀 Staging確認のタイミング

- 機能が一区切りついたタイミングでdevelopにマージ
- Staging環境でE2Eテストや動作確認を実施
- 問題なければmainにマージしてproductionリリース

### 🗑️ Feature ブランチの削除

```bash
# developにマージ後、ローカルのfeatureブランチを削除
git branch -d feature/your-feature-name

# リモートにpushしていた場合は削除（通常はpushしない）
# git push origin --delete feature/your-feature-name
```

## ブランチ保護の推奨設定

GitHub リポジトリで以下の保護設定を推奨：

### mainブランチ
- Require pull request reviews before merging
- Require status checks to pass before merging
- Include administrators（管理者も同じルールに従う）

### developブランチ
- Require status checks to pass before merging（任意）

## 緊急時の対応

### Staging環境のロールバック

```bash
# developブランチで前のコミットに戻す
git checkout develop
git revert HEAD
git push origin develop  # staging自動デプロイ
```

### Production環境のロールバック

```bash
# mainブランチで前のコミットに戻す
git checkout main
git revert HEAD
git push origin main  # production自動デプロイ
```

または、GitHub Actions UIから古いコミットを指定して手動実行

### Hotfix（緊急修正）

Production環境に緊急の修正が必要な場合：

```bash
# mainから直接hotfixブランチを作成
git checkout main
git pull origin main
git checkout -b hotfix/urgent-fix

# 修正・テスト・コミット
git add .
git commit -m "hotfix: urgent security fix"

# mainに直接マージ（本番リリース）
git checkout main
git merge hotfix/urgent-fix
git push origin main  # production自動デプロイ

# developにも反映
git checkout develop
git merge hotfix/urgent-fix
git push origin develop
```

## ワークフロー一覧

### メインデプロイ

- `deploy-aws.yml` - AWS Pulumi Infrastructure + API
- `deploy-azure.yml` - Azure Pulumi Infrastructure + API
- `deploy-gcp.yml` - GCP Pulumi Infrastructure + API

### フロントエンド

- `deploy-frontend-aws.yml` - React フロントエンド (AWS S3)
- `deploy-frontend-azure.yml` - React フロントエンド (Azure Blob)
- `deploy-frontend-gcp.yml` - React フロントエンド (GCP Storage)

### ランディングページ

- `deploy-landing-aws.yml` - 静的サイト (AWS S3)
- `deploy-landing-azure.yml` - 静的サイト (Azure Blob)
- `deploy-landing-gcp.yml` - 静的サイト (GCP Storage)

## 環境変数とシークレット

各環境（staging/production）で以下のシークレットが設定されています：

### AWS
- `AWS_ACCESS_KEY_ID`
- `AWS_SECRET_ACCESS_KEY`

### Azure
- `AZURE_CREDENTIALS`

### GCP
- `GCP_CREDENTIALS`

### Pulumi
- `PULUMI_ACCESS_TOKEN`

これらはGitHub リポジトリの Settings → Secrets and variables → Actions で管理されています。
