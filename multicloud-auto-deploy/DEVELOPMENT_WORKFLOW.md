# 開発ワークフロー

## 概要

このプロジェクトは、ブランチベースの開発フローを採用しています。

## 開発フロー

```
feature/xxx → ローカル開発（コミットのみ、pushしない）
    ↓ staging確認したいとき push
feature/xxx → staging自動デプロイ（動作確認）
    ↓ 開発完了、mainにマージ
main        → staging自動デプロイ（最終確認）
    ↓ 確認OK、手動でproduction選択
main        → production手動デプロイ
```

## ステップ別ガイド

### 1. 機能開発開始

```bash
# mainブランチから最新を取得
git checkout main
git pull origin main

# featureブランチを作成
git checkout -b feature/your-feature-name
```

### 2. ローカル開発

```bash
# コードを編集
# テストを実行
# コミット（ローカルのみ）
git add .
git commit -m "feat: add new feature"

# ローカル環境でテスト
docker compose up -d
# テスト実行...
```

### 3. Staging環境で確認

```bash
# featureブランチをpush → staging自動デプロイ
git push origin feature/your-feature-name
```

**自動実行されるもの：**
- `services/**` または `infrastructure/**` が変更された場合
- AWS/Azure/GCP の該当するデプロイワークフローが**staging環境**に自動デプロイ

**GitHub Actionsで確認：**
- https://github.com/PLAYER1-r7/multicloud-auto-deploy/actions
- 実行状況とログを確認

### 4. Mainにマージ（開発完了）

```bash
# featureブランチで開発完了
git checkout main
git pull origin main
git merge feature/your-feature-name

# mainにpush → staging自動デプロイ（最終確認）
git push origin main
```

**この時点で：**
- mainブランチへのpush = staging環境に自動デプロイ
- 本番環境へは**まだデプロイされない**

### 5. Production環境へデプロイ（手動）

Staging環境で問題なければ、GitHub ActionsのUIから手動でproductionへデプロイ：

1. https://github.com/PLAYER1-r7/multicloud-auto-deploy/actions
2. 該当するワークフロー（Deploy to AWS/Azure/GCPなど）を選択
3. 「Run workflow」ボタンをクリック
4. Branch: `main` を選択
5. Environment: `production` を選択
6. 「Run workflow」を実行

## トリガー条件

### 自動デプロイ（Staging）

以下の場合に**staging環境**へ自動デプロイ：

- **ブランチ**: `main` または `feature/**`
- **対象パス**:
  - `services/**` → APIデプロイ
  - `infrastructure/**` → インフラデプロイ
  - `services/frontend_react/**` → フロントエンドデプロイ
  - `static-site/**` → ランディングページデプロイ

### 手動デプロイ

- GitHub Actions UI から workflow_dispatch で実行
- Environment を選択可能: `staging` または `production`

## 注意事項

### ⚠️ Production環境への自動デプロイはありません

- Production環境へは**必ず手動で承認・実行**が必要
- 誤ってproductionへデプロイされることはありません

### 🔄 ローカル開発は自由にコミット

- ローカルでコミットを重ねても、pushしない限りデプロイされません
- 開発中は好きなだけコミットして構いません

### 🚀 Staging確認のタイミング

- 機能が一区切りついたタイミングでpush
- Staging環境でE2Eテストや動作確認を実施

### 🗑️ Feature ブランチの削除

```bash
# マージ後、ローカルとリモートのfeatureブランチを削除
git branch -d feature/your-feature-name
git push origin --delete feature/your-feature-name
```

## 緊急時の対応

### Staging環境のロールバック

```bash
# 前のコミットに戻す
git revert HEAD
git push origin main  # staging自動デプロイ
```

### Production環境のロールバック

1. GitHub Actions UIから古いコミットを指定して手動実行
2. または緊急修正ブランチを作成してhotfix適用

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
