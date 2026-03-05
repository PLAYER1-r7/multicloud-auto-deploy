# サービス分離アーキテクチャ（SNS API vs Exam Solver API）

## 概要

本リポジトリは大学入試解答サービス（大学入試解答サイト）として、主に以下の2つのサービスを独立したマイクロサービスとして管理しています：

1. **SNS API** (`services/sns-api/`)：社会ネットワーク機能（メッセージ投稿、プロフィール管理、画像アップロード）
2. **Exam Solver API** (`services/exam-solver-api/`)：大学入試解答機能（OCR、AI解答）

## 🎯 分離のメリット

- **独立したスケーリング**: 利用パターンが異なるため、それぞれのサービスを独立してスケールできます
- **デプロイメント独立性**: SNS API の更新が Exam Solver API に影響しません
- **コスト管理**: 各サービスのメトリクスを個別に追跡でき、コスト最適化が容易です
- **セキュリティ**: サービス間の権限を明確に分離できます

## 📁 ディレクトリ構造

```
services/
├── sns-api/          # SNS（メッセージング）API
│   ├── app/
│   │   ├── main.py          # FastAPI アプリケーション
│   │   ├── config.py        # SNS固有の設定
│   │   ├── models.py        # リクエスト/レスポンス モデル
│   │   ├── routes/          # SNS エンドポイント
│   │   ├── services/        # ビジネスロジック
│   │   └── backends/        # クラウド統合
│   ├── index.py             # AWS Lambda ハンドラー
│   ├── function_app.py      # Azure Functions ハンドラー
│   ├── function.py          # GCP Cloud Functions ハンドラー
│   ├── requirements.txt
│   └── tests/
│
└── exam-solver-api/  # 大学入試解答 API
    ├── app/
    │   ├── main.py          # FastAPI アプリケーション
    │   ├── config.py        # Solver固有の設定
    │   ├── models.py        # SolveRequest/Response モデル
    │   ├── routes/
    │   │   ├── solve.py     # OCR + AI 解答エンドポイント
    │   │   └── learning.py  # 学習支援エンドポイント
    │   ├── services/        # 数学求解エンジン
    │   └── backends/        # クラウド統合
    ├── index.py             # AWS Lambda ハンドラー
    ├── function_app.py      # Azure Functions ハンドラー
    ├── function.py          # GCP Cloud Functions ハンドラー
    ├── requirements.txt
    └── tests/
```

## 🚀 デプロイメント

### AWS (Lambda)

```bash
# SNS API - Lambda Function
Name: multicloud-auto-deploy-{env}-api
Entry: services/sns-api/index.py

# Solver API - Lambda Function
Name: multicloud-auto-deploy-{env}-solver
Entry: services/exam-solver-api/index.py

# 自動デプロイ
git push origin develop   # staging にデプロイ
git push origin main      # production にデプロイ
```

**ワークフロー ファイル**:

- [`.github/workflows/deploy-sns-aws.yml`](.github/workflows/deploy-sns-aws.yml)
- [`.github/workflows/deploy-exam-solver-aws.yml`](.github/workflows/deploy-exam-solver-aws.yml)

### Azure (Functions)

```bash
# SNS API - Function App
Name: multicloud-auto-deploy-{env}-api
Plan: Flex Consumption

# Solver API - Function App
Name: multicloud-auto-deploy-{env}-solver
Plan: Flex Consumption
```

**ワークフロー ファイル**:

- [`.github/workflows/deploy-sns-azure.yml`](.github/workflows/deploy-sns-azure.yml)
- [`.github/workflows/deploy-exam-solver-azure.yml`](.github/workflows/deploy-exam-solver-azure.yml)

### GCP (Cloud Functions Gen 2)

```bash
# SNS API - Cloud Function
Name: multicloud-auto-deploy-{env}-api
Runtime: Python 3.13

# Solver API - Cloud Function
Name: multicloud-auto-deploy-{env}-solver
Runtime: Python 3.13
```

**ワークフロー ファイル**:

- [`.github/workflows/deploy-sns-gcp.yml`](.github/workflows/deploy-sns-gcp.yml)
- [`.github/workflows/deploy-exam-solver-gcp.yml`](.github/workflows/deploy-exam-solver-gcp.yml)

## 🛣️ API ルーティング

### SNS API エンドポイント

| メソッド | パス                     | 説明                      |
| -------- | ------------------------ | ------------------------- |
| `POST`   | `/posts`                 | メッセージ投稿            |
| `GET`    | `/posts/{postId}`        | メッセージ取得            |
| `POST`   | `/uploads/presigned-url` | 画像アップロード URL 取得 |
| `GET`    | `/profiles/{userId}`     | プロフィール取得          |
| `GET`    | `/limits/user/{userId}`  | レート制限情報取得        |

### Exam Solver API エンドポイント

| メソッド | パス            | 説明                   |
| -------- | --------------- | ---------------------- |
| `POST`   | `/v1/solve`     | 問題を OCR + AI で解答 |
| `GET`    | `/v1/ocr-debug` | OCR デバッグログ取得   |
| `POST`   | `/learning/*`   | 学習支援機能           |

## 🔗 ルーティング実装

### AWS API Gateway

API Gateway は path-based routing を使用して、異なるパスを異なる Lambda 関数に振り分けます：

```
/posts/* → Lambda: multicloud-auto-deploy-{env}-api
/uploads/* → Lambda: multicloud-auto-deploy-{env}-api
/profiles/* → Lambda: multicloud-auto-deploy-{env}-api
/limits/* → Lambda: multicloud-auto-deploy-{env}-api
/v1/solve* → Lambda: multicloud-auto-deploy-{env}-solver
/learning/* → Lambda: multicloud-auto-deploy-{env}-solver
```

### Azure Functions

Azure Front Door または Application Gateway でホストベース・パスベースのルーティングを実装：

```
multicloud-auto-deploy-{env}-api.azurewebsites.net → SNS API Function App
multicloud-auto-deploy-{env}-solver.azurewebsites.net → Solver API Function App
```

### GCP Cloud Functions

複数のエンドポイント URL でそれぞれデプロイ：

```
https://{region}-{project}.cloudfunctions.net/{project_name}-{env}-api
https://{region}-{project}.cloudfunctions.net/{project_name}-{env}-solver
```

## 💾 インフラストラクチャ (Pulumi)

### AWS (`infrastructure/pulumi/aws/__main__.py`)

- **IAM Roles**: `{project_name}-{env}-lambda-role` (SNS), `{project_name}-{env}-solver-lambda-role` (Solver)
- **Lambda Layers**:
  - `{project_name}-{env}-sns-dependencies`
  - `{project_name}-{env}-solver-dependencies`
- **Lambda Functions**:
  - `multicloud-auto-deploy-{env}-api` (SNS)
  - `multicloud-auto-deploy-{env}-solver` (Solver)
- **API Gateway**: Path-based routing で両方の Lambda を管理

### Azure (`infrastructure/pulumi/azure/__main__.py`)

- **Resource Group**: `{project_name}-{env}-rg`
- **App Service Plan**: Flex Consumption (共有)
- **Function Apps**:
  - `multicloud-auto-deploy-{env}-api` (SNS)
  - `multicloud-auto-deploy-{env}-solver` (Solver)
- **Storage Accounts**: Functions 用と Frontend 用（共有）

### GCP (`infrastructure/pulumi/gcp/__main__.py`)

- **Cloud Storage Buckets**: Function source, uploads, frontend
- **Cloud Functions**: `multicloud-auto-deploy-{env}-api` と `{env}-solver` (gcloud deploy 経由)
- **Service Accounts**: IAM 権限管理

## 🚨 マイグレーションノート（2025年2月）

### 削除されたファイル

以下の古いモノリシック デプロイワークフロー は削除されました：

- `.github/workflows/deploy-aws.yml`
- `.github/workflows/deploy-azure.yml`
- `.github/workflows/deploy-gcp.yml`

**新しいワークフロー を使用してください**:

- `deploy-sns-{cloud}.yml` (SNS API 用)
- `deploy-exam-solver-{cloud}.yml` (Solver API 用)

### 削除されたディレクトリ

- `services/api/` → `services/sns-api/` にリネーム

### 古いワークフロー の参照

既存のスクリプトやドキュメント が古いワークフロー を参照している場合、以下のように更新してください：

```bash
# 古いコマンド（使用不可）
git push origin develop  # deploy-aws.yml トリガー

# 新しいコマンド（使用するワークフロー を明示的に指定）
git push origin develop  # deploy-sns-aws.yml + deploy-exam-solver-aws.yml トリガー
```

## 🔍 トラブルシューティング

### ワークフロー がトリガされない

1. ブランチ の `develop` または `main` にプッシュしているか確認
2. ファイルパスが正しい trigger を実行しているか確認：
   - SNS API 変更 → `services/sns-api/**` にマッチするか
   - Solver API 変更 → `services/exam-solver-api/**` にマッチするか
3. `.github/workflows/{workflow-name}.yml` が存在し、正しい設定か確認

### デプロイ エラー

1. Lambda Layer ZIP ファイルが作成されているか：

   ```bash
   ./scripts/build-lambda-layer.sh
   ls -la services/sns-api/lambda-layer.zip
   ls -la services/exam-solver-api/lambda-layer.zip
   ```

2. Pulumi スタック の状態を確認：
   ```bash
   cd infrastructure/pulumi/aws
   pulumi stack select staging
   pulumi preview
   ```

## 📚 関連ドキュメント

- [SNS API README](services/sns-api/README.md)
- [Exam Solver API README](services/exam-solver-api/README.md)
- [Pulumi Infrastructure](infrastructure/pulumi/)
- [CI/CD パイプライン](.github/workflows/)

## 🤝 貢献ガイドライン

新機能または bug fix の際：

1. **どのサービスに関連しているか判断**
   - メッセージング機能 → `services/sns-api/`
   - 解答機能 → `services/exam-solver-api/`

2. **正しいディレクトリで変更を行う**
   - 他のサービスに無用な変更を加えない

3. **テストを実行**

   ```bash
   pytest services/{service-name}/tests/ -v
   ```

4. **Git コミット でサービス を明記**
   ```
   feat(sns-api): メッセージ機能の改善
   feat(exam-solver-api): OCR 精度向上
   ```

## 📞 サポート

質問または問題は GitHub Issues で報告してください。
