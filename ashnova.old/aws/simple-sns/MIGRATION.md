# 🎉 Simple-SNS 移植完了

simple-snsフォルダの必要なファイルを `aws/simple-sns` に正常に移植しました。

## 📁 移植されたファイル

### Terraformファイル (terraform/)

- `main.tf` - プロバイダーと変数設定
- `lambda.tf` - Lambda関数とIAM設定
- `lambda-layer.tf` - Lambda Layerの定義
- `api-gateway.tf` - API Gateway設定
- `dynamodb.tf` - DynamoDBテーブル
- `cognito.tf` - Cognito認証設定
- `s3.tf` - S3バケット設定
- `frontend-s3.tf` - CloudFront設定
- `waf.tf` - WAFルール設定
- `outputs.tf` - 出力値定義
- `s3-account-settings.tf` - S3アカウント設定

### Lambda関数ソース (src/)

- `createPost.ts` - 投稿作成
- `listPosts.ts` - 投稿一覧取得
- `deletePost.ts` - 投稿削除
- `getUploadUrls.ts` - 画像アップロードURL生成
- `common.ts` - 共通関数
- `types.ts` - TypeScript型定義
- `middleware/` - Middy ミドルウェア
- `utils/` - ユーティリティ関数

### フロントエンド (frontend/)

- `src/` - Reactソースコード
- `public/` - 静的ファイル
- `index.html` - エントリーポイント

### 設定ファイル

- `package.json` - 依存関係とスクリプト（更新済み）
- `tsconfig.json` - TypeScript設定
- `vite.config.ts` - Vite設定
- `tailwind.config.js` - Tailwind CSS設定
- `.env.example` - 環境変数テンプレート
- `.gitignore` - Git除外設定

### スクリプト

- `quickstart.sh` - クイックスタートスクリプト（新規作成）
- `deploy-frontend.sh` - フロントエンドデプロイスクリプト（パス修正済み）

### ドキュメント

- `SETUP.md` - セットアップガイド（新規作成）
- `README.md` - プロジェクト説明

## ✅ 実施した修正

1. **Terraformパス修正**
   - Lambda関数のソースディレクトリを `../dist` に変更
   - 相対パスを terraform サブディレクトリに対応

2. **デプロイスクリプト修正**
   - `deploy-frontend.sh` のTerraform出力取得パスを修正
   - `terraform/` サブディレクトリに対応

3. **package.json更新**
   - Terraformコマンドをサブディレクトリ対応に修正
   - 新しいスクリプトを追加（terraform:init, terraform:plan等）

4. **ドキュメント作成**
   - `SETUP.md` - 詳細なセットアップ手順
   - `quickstart.sh` - 自動デプロイスクリプト
   - `aws/README.md` - プロジェクト一覧に追加

## 🚀 次のステップ

### 1. デプロイ準備

```bash
cd /Users/sat0sh1kawada/Workspace/ashnova/aws/simple-sns
```

### 2. クイックスタートでデプロイ

```bash
./quickstart.sh
```

または手動でステップ実行：

```bash
# 依存関係インストール
npm install

# Lambda関数ビルド
npm run build

# Terraform初期化
npm run terraform:init

# デプロイプラン確認
npm run terraform:plan

# デプロイ実行
npm run terraform:apply
```

### 3. フロントエンドデプロイ

Terraformデプロイ後、出力値を`.env.local`に設定して：

```bash
npm run build:frontend
npm run deploy
```

## 🗂️ ディレクトリ比較

**旧構造（simple-sns/）:**

```
simple-sns/
├── *.tf (ルート)
├── src/
├── frontend/
└── package.json
```

**新構造（aws/simple-sns/）:**

```
aws/simple-sns/
├── terraform/      # Terraformファイル
│   └── *.tf
├── src/           # Lambda関数
├── frontend/      # Reactアプリ
├── package.json
├── quickstart.sh
└── SETUP.md
```

## 🧹 クリーンアップ

simple-snsフォルダは以下のコマンドで削除できます：

```bash
rm -rf /Users/sat0sh1kawada/Workspace/ashnova/simple-sns
```

ただし、削除前に以下を確認：

- 重要な .env ファイルがないか
- カスタム設定がないか
- terraform.tfstate のバックアップ

## 📚 参考ドキュメント

- [SETUP.md](SETUP.md) - 詳細なセットアップ手順
- [terraform/README.md](terraform/README.md) - Terraform設定詳細
- [../iam-policy-simple-sns.json](../iam-policy-simple-sns.json) - 必要なIAM権限
