# Simple SNS - GCP版

Google Cloud Platform上で動作するSimple SNSアプリケーション。

## 🏗 アーキテクチャ

- **認証**: Firebase Authentication (Google Sign-In)
- **API**: Cloud Functions (Node.js 20)
- **データベース**: Cloud Firestore
- **画像ストレージ**: Cloud Storage
- **フロントエンド**: React + Vite (Cloud Storage Static Hosting)
- **IaC**: Terraform/OpenTofu

## 📋 前提条件

- Node.js 20以上
- Terraform/OpenTofu
- Google Cloud SDK (gcloud)
- GCPプロジェクト

## 🚀 セットアップ

### 1. GCP プロジェクトの準備

```bash
# 認証
gcloud auth login
gcloud auth application-default login

# プロジェクト作成（既存の場合はスキップ）
gcloud projects create YOUR_PROJECT_ID

# プロジェクト設定
gcloud config set project YOUR_PROJECT_ID

# 課金を有効化（必須）
# https://console.cloud.google.com/billing
```

### 2. Firebaseプロジェクトの設定

```bash
# Firebase CLI をインストール
npm install -g firebase-tools

# Firebase にログイン
firebase login

# Firebase プロジェクトを初期化
firebase init

# Authentication を有効化
# https://console.firebase.google.com/project/YOUR_PROJECT_ID/authentication
# Sign-in method → Google を有効化
```

### 3. Backend (Cloud Functions) のビルド

```bash
cd functions
npm install
npm run build
cd ..

# functions.zip を作成
zip -r functions.zip functions/dist functions/package.json functions/package-lock.json
```

### 4. Terraform でインフラをデプロイ

```bash
cd terraform

# terraform.tfvars を作成
cat > terraform.tfvars <<EOF
gcp_project_id = "YOUR_PROJECT_ID"
gcp_region     = "asia-northeast1"
EOF

# 初期化
tofu init

# デプロイ
tofu apply
```

### 5. Frontend の設定とデプロイ

```bash
cd frontend

# 依存関係をインストール
npm install

# .env.local を作成（Firebase Console から取得）
cat > .env.local <<EOF
VITE_FIREBASE_API_KEY=your-api-key
VITE_FIREBASE_AUTH_DOMAIN=your-project.firebaseapp.com
VITE_FIREBASE_PROJECT_ID=your-project-id
VITE_FIREBASE_STORAGE_BUCKET=your-project.appspot.com
VITE_FIREBASE_MESSAGING_SENDER_ID=your-sender-id
VITE_FIREBASE_APP_ID=your-app-id
VITE_API_BASE_URL=https://asia-northeast1-your-project.cloudfunctions.net
EOF

# ビルド
npm run build

# Cloud Storage にアップロード
gsutil -m rsync -r -d dist/ gs://FRONTEND_BUCKET_NAME/
```

## 🔧 開発

### Backend 開発

```bash
cd functions

# 依存関係インストール
npm install

# TypeScript コンパイル
npm run build

# ウォッチモード
npm run watch
```

### Frontend 開発

```bash
cd frontend

# 開発サーバー起動
npm run dev

# ブラウザで http://localhost:5173 を開く
```

## 📡 API エンドポイント

すべてのエンドポイントは Cloud Functions としてデプロイされます：

### 認証不要

- `GET /listPosts?limit=20&continuationToken=...` - 投稿一覧

### 認証必要 (Firebase ID Token)

- `POST /createPost` - 投稿作成
- `DELETE /deletePost/:postId` - 投稿削除
- `GET /getUploadUrls?count=3` - 画像アップロードURL取得

## 🗂 プロジェクト構造

```
gcp/simple-sns/
├── functions/              # Cloud Functions
│   ├── src/
│   │   ├── functions/      # 各エンドポイント
│   │   ├── common.ts       # 共通ロジック
│   │   ├── types.ts        # 型定義
│   │   └── index.ts        # エントリーポイント
│   ├── package.json
│   └── tsconfig.json
├── frontend/               # React フロントエンド
│   ├── src/
│   │   ├── config/         # Firebase設定
│   │   └── hooks/          # カスタムフック
│   └── package.json
├── terraform/              # インフラ定義
│   ├── main.tf
│   ├── variables.tf
│   ├── outputs.tf
│   └── provider.tf
└── README.md
```

## 🔑 Firebase Console での設定

1. **Authentication 設定**
   - https://console.firebase.google.com/project/YOUR_PROJECT_ID/authentication
   - Sign-in method → Google を有効化
   - 承認済みドメイン に `sns.gcp.ashnova.jp` を追加

2. **Web アプリの登録**
   - Project Overview → Add app → Web
   - アプリのニックネーム: "Simple SNS Web"
   - Firebase SDK configuration をコピーして `.env.local` に設定

## 🧹 クリーンアップ

```bash
# OpenTofu でリソース削除
./destroy.sh

# Firestore の全データ削除も行う場合
DELETE_FIRESTORE=true CONFIRM_DELETE=YES ./destroy.sh

# Firebase プロジェクトは手動で削除
# https://console.firebase.google.com/project/YOUR_PROJECT_ID/settings/general
```

## 📝 ライセンス

Private
