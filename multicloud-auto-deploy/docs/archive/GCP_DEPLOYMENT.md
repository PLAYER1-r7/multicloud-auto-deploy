# GCP Deployment Guide


![GCP](images/icons/gcp.svg){width=25%}
Cloud Runを使用したマルチクラウド自動デプロイシステムのデプロイガイド

## 📋 目次

- [前提条件](#前提条件)
- [デプロイ手順](#デプロイ手順)
- [リソース構成](#リソース構成)
- [検証](#検証)
- [トラブルシューティング](#トラブルシューティング)

## 🔧 前提条件

### 必要なツール

```bash
# Google Cloud SDK
curl https://sdk.cloud.google.com | bash
exec -l $SHELL

# Pulumi
curl -fsSL https://get.pulumi.com | sh
export PATH=$PATH:$HOME/.pulumi/bin

# Docker
sudo apt-get update
sudo apt-get install docker.io
```

### GCP認証情報

1. **GCPにログイン**
```bash
gcloud auth login
gcloud auth application-default login
```

2. **プロジェクトの設定**
```bash
gcloud projects list
gcloud config set project YOUR_PROJECT_ID
```

3. **必要なAPIの有効化**
```bash
gcloud services enable \
  run.googleapis.com \
  artifactregistry.googleapis.com \
  firestore.googleapis.com \
  compute.googleapis.com \
  storage.googleapis.com
```

4. **Editorロールの付与**（デプロイ用アカウント）
```bash
gcloud projects add-iam-policy-binding YOUR_PROJECT_ID \
  --member="user:your-email@gmail.com" \
  --role="roles/editor"
```

## 🚀 デプロイ手順

### Step 1: Pulumiスタックの初期化

```bash
cd infrastructure/pulumi/gcp
pulumi stack init staging
pulumi config set gcp:project YOUR_PROJECT_ID
pulumi config set environment staging
```

### Step 2: Artifact Registryの手動作成（権限不足の場合）

```bash
# Artifact Registryリポジトリの作成
gcloud artifacts repositories create mcad-staging-repo \
  --repository-format=docker \
  --location=asia-northeast1 \
  --description="Multi-Cloud Auto Deploy Docker images"
```

### Step 3: Firestoreの手動作成（権限不足の場合）

```bash
# Firestoreデータベースの作成（Nativeモード）
gcloud firestore databases create --location=asia-northeast1
```

### Step 4: インフラストラクチャのデプロイ

```bash
pulumi up
```

デプロイされるリソース：
- Cloud Storage Bucket (Frontend)
- Artifact Registry Repository
- Cloud Run Service (Backend)
- Firestore Database
- Backend Bucket (CDN)
- Global IP Address
- URL Map
- HTTP Proxy
- Forwarding Rule

### Step 5: Dockerイメージのビルドとプッシュ

```bash
cd ../../../services/backend

# Artifact Registryの認証設定
gcloud auth configure-docker asia-northeast1-docker.pkg.dev

# Dockerイメージのビルド（linux/amd64プラットフォーム）
docker build --platform linux/amd64 \
  -t asia-northeast1-docker.pkg.dev/YOUR_PROJECT_ID/mcad-staging-repo/multicloud-auto-deploy-api:latest \
  -f Dockerfile.gcp .

# イメージのプッシュ
docker push asia-northeast1-docker.pkg.dev/YOUR_PROJECT_ID/mcad-staging-repo/multicloud-auto-deploy-api:latest
```

### Step 6: Cloud Runの更新

```bash
# Cloud Runサービスを再デプロイ（新しいイメージを使用）
cd ../../infrastructure/pulumi/gcp
pulumi up
```

### Step 7: Cloud Run IAMの設定（手動）

```bash
# allUsersにinvokerロールを付与
gcloud run services add-iam-policy-binding mcad-staging-api \
  --region=asia-northeast1 \
  --member="allUsers" \
  --role="roles/run.invoker"
```

### Step 8: フロントエンドのデプロイ

```bash
cd ../../../services/frontend

# Cloud RunのURLを取得
API_URL=$(gcloud run services describe mcad-staging-api \
  --region=asia-northeast1 \
  --format="value(status.url)")

# 環境変数を設定してビルド
VITE_API_URL=$API_URL npm run build

# Cloud Storageにアップロード
gsutil -m cp -r dist/* gs://mcad-staging-frontend/

# オブジェクトを公開
gsutil -m acl ch -u AllUsers:R gs://mcad-staging-frontend/**
```

## 🏗️ リソース構成

### デプロイされるリソース

| リソース | 名前 | 目的 |
|---------|------|------|
| Cloud Storage | `mcad-staging-frontend` | フロントエンドホスティング |
| Artifact Registry | `mcad-staging-repo` | Dockerイメージの保存 |
| Cloud Run | `mcad-staging-api` | バックエンドAPI |
| Firestore | `(default)` | NoSQLデータベース |
| Backend Bucket | `mcad-staging-backend` | CDN統合 |
| Global IP | `mcad-staging-frontend-ip` | 固定IPアドレス |
| URL Map | `mcad-staging-urlmap` | ルーティング設定 |
| HTTP Proxy | `mcad-staging-http-proxy` | HTTP終端 |
| Forwarding Rule | `mcad-staging-http-rule` | トラフィック転送 |

### ネットワーク構成

```
Internet
   │
   ├─→ Cloud Load Balancer (CDN)
   │       └─→ Backend Bucket
   │              └─→ Cloud Storage (Frontend)
   │
   └─→ Cloud Run (Backend) ──→ Firestore
           └─→ Public URL
```

### アーキテクチャ図

```
┌──────────────────────────────────────────────────┐
│                    Internet                       │
└─────────────┬───────────────────┬────────────────┘
              │                   │
              ▼                   ▼
    ┌──────────────────┐  ┌──────────────────┐
    │  Load Balancer   │  │   Cloud Run      │
    │  (34.117.111.182)│  │  (Backend API)   │
    └────────┬─────────┘  └────────┬─────────┘
             │                     │
             ▼                     ▼
    ┌──────────────────┐  ┌──────────────────┐
    │ Cloud Storage    │  │   Firestore      │
    │   (Frontend)     │  │   (Database)     │
    └──────────────────┘  └──────────────────┘
```

## ✅ 検証

### 1. バックエンドAPIの確認

```bash
# Cloud RunのURLを取得
BACKEND_URL=$(gcloud run services describe mcad-staging-api \
  --region=asia-northeast1 \
  --format="value(status.url)")

# ヘルスチェック
curl $BACKEND_URL/api/health

# クラウド情報の確認
curl $BACKEND_URL/ | jq '.'

# メッセージ作成
curl -X POST $BACKEND_URL/api/messages \
  -H "Content-Type: application/json" \
  -d '{"text":"GCP Cloud Run test"}'

# メッセージ取得
curl $BACKEND_URL/api/messages | jq '.'
```

### 2. フロントエンドの確認（Cloud Storage直接）

```bash
# Cloud Storageへの直接アクセス
curl -I https://storage.googleapis.com/mcad-staging-frontend/index.html
```

### 3. フロントエンドの確認（Load Balancer経由）

```bash
# Load BalancerのIPアドレスを取得
FRONTEND_IP=$(terraform output -raw frontend_cdn_ip)

# Load Balancer経由でアクセス
curl -I http://$FRONTEND_IP/

# HTMLコンテンツの取得
curl -s http://$FRONTEND_IP/ | head -20
```

ブラウザで `http://$FRONTEND_IP` にアクセスして動作確認

### 4. Firestoreの確認

```bash
# Firestoreのデータを確認（Firebaseコンソール）
gcloud firestore databases list

# ドキュメント数の確認（gcloud firestore CLIを使用）
gcloud firestore collections list
```

## 🔧 トラブルシューティング

### Cloud Runが起動しない

**症状**: Cloud RunサービスがFAILEDステータス

**原因と対処**:

1. **イメージが見つからない**
```bash
# Artifact Registryのイメージを確認
gcloud artifacts docker images list \
  asia-northeast1-docker.pkg.dev/YOUR_PROJECT_ID/mcad-staging-repo

# イメージの詳細情報
gcloud artifacts docker images describe \
  asia-northeast1-docker.pkg.dev/YOUR_PROJECT_ID/mcad-staging-repo/multicloud-auto-deploy-api:latest
```

2. **プラットフォームの不一致**
```bash
# linux/amd64でビルドし直す
docker build --platform linux/amd64 -f Dockerfile.gcp .
```

3. **権限エラー**
```bash
# Cloud Runサービスアカウントの確認
gcloud run services describe mcad-staging-api \
  --region=asia-northeast1 \
  --format="value(spec.template.spec.serviceAccountName)"

# Firestoreへのアクセス権限を確認
gcloud projects get-iam-policy YOUR_PROJECT_ID \
  --flatten="bindings[].members" \
  --filter="bindings.members:serviceAccount:*"
```

### Load Balancerが動作しない

**症状**: Load BalancerのIPアドレスにアクセスできない

**対処**:

1. **Backend Bucketの確認**
```bash
# Backend Bucketの設定を確認
gcloud compute backend-buckets describe mcad-staging-backend \
  --format=yaml

# Cloud Storageバケットの存在確認
gsutil ls gs://mcad-staging-frontend/
```

2. **Forwarding Ruleの確認**
```bash
# Forwarding Ruleの詳細
gcloud compute forwarding-rules describe mcad-staging-http-rule \
  --global

# URL Mapの確認
gcloud compute url-maps describe mcad-staging-urlmap
```

3. **Cloud Storage権限の確認**
```bash
# バケットのIAMポリシーを確認
gsutil iam get gs://mcad-staging-frontend/

# オブジェクトを公開
gsutil iam ch allUsers:objectViewer gs://mcad-staging-frontend
```

### Firestoreへの接続エラー

**症状**: バックエンドがFirestoreに接続できない

**対処**:

1. **Firestoreの初期化確認**
```bash
# Firestoreデータベースの確認
gcloud firestore databases list

# Firestoreのロケーション確認
gcloud firestore databases describe "(default)"
```

2. **サービスアカウント権限の確認**
```bash
# Cloud Runのサービスアカウントを確認
SA_EMAIL=$(gcloud run services describe mcad-staging-api \
  --region=asia-northeast1 \
  --format="value(spec.template.spec.serviceAccountName)")

# Firestore権限を付与
gcloud projects add-iam-policy-binding YOUR_PROJECT_ID \
  --member="serviceAccount:$SA_EMAIL" \
  --role="roles/datastore.user"
```

### Backend Bucketsクォータ超過

**症状**: `Quota 'BACKEND_BUCKETS' exceeded`

**対処**:

```bash
# 既存のBackend Bucketsを確認
gcloud compute backend-buckets list

# 不要なBackend Bucketsを削除
# 注意: URL Mapなどの依存リソースを先に削除する必要があります

# 1. Forwarding Rulesを削除
gcloud compute forwarding-rules delete <forwarding-rule-name> --global --quiet

# 2. Target Proxiesを削除
gcloud compute target-http-proxies delete <proxy-name> --quiet

# 3. URL Mapsを削除
gcloud compute url-maps delete <urlmap-name> --quiet

# 4. Backend Bucketを削除
gcloud compute backend-buckets delete <backend-bucket-name> --quiet
```

### Docker pushが失敗する

**症状**: `unauthorized: You don't have the needed permissions`

**対処**:

```bash
# Artifact Registry認証の再設定
gcloud auth configure-docker asia-northeast1-docker.pkg.dev

# 権限の確認
gcloud artifacts repositories get-iam-policy mcad-staging-repo \
  --location=asia-northeast1

# 権限の追加（必要に応じて）
gcloud artifacts repositories add-iam-policy-binding mcad-staging-repo \
  --location=asia-northeast1 \
  --member="user:your-email@gmail.com" \
  --role="roles/artifactregistry.writer"
```

## 📊 クォータと制限

### Cloud Run

- 無料プラン: 2,000,000リクエスト/月、180,000 vCPU秒/月、360,000 GiB秒/月
- CPU: 1〜8 vCPU
- メモリ: 128 MiB〜32 GiB
- リクエストタイムアウト: 最大60分
- 同時実行数: 最大1,000

### Firestore

- 無料プラン: 1 GiB、50,000読み取り/日、20,000書き込み/日、20,000削除/日
- ドキュメントサイズ: 最大1 MiB
- トランザクション: 最大500ドキュメント
- インデックス: 40,000エントリ/ドキュメント

### Cloud Storage

- 無料プラン: 5 GB、5,000 Class Aオペレーション/月、50,000 Class Bオペレーション/月
- 静的Webサイト: 追加費用なし
- 帯域幅: 1 TB送信/月（中国・オーストラリア以外は無料）

### Backend Buckets

- クォータ: プロジェクトあたり3個（デフォルト）
- クォータ増加: Google Cloud Consoleから申請可能

## 🔗 関連リンク

- [Cloud Run Documentation](https://cloud.google.com/run/docs)
- [Firestore Documentation](https://cloud.google.com/firestore/docs)
- [Cloud Storage Documentation](https://cloud.google.com/storage/docs)
- [Cloud Load Balancing Documentation](https://cloud.google.com/load-balancing/docs)
- [Artifact Registry Documentation](https://cloud.google.com/artifact-registry/docs)

## 📝 次のステップ

- ✅ デプロイ完了
- [ ] カスタムドメインの設定
- [ ] SSL証明書の設定（HTTPS対応）
- [ ] Cloud Armorの設定（WAF）
- [ ] Cloud Monitoringの設定
- [ ] CI/CDパイプラインの構築
- [ ] Backend Bucketsクォータの増加申請（必要に応じて）
