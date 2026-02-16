# ツールリファレンス

最終更新: 2026-02-15

## 📋 目次

- [デプロイツール](#デプロイツール)
- [テストツール](#テストツール)
- [管理・監視ツール](#管理監視ツール)
- [ユーティリティ](#ユーティリティ)

---

## デプロイツール

### deploy-aws.sh

**用途**: AWS環境へのTerraformベースデプロイ

**使用方法**:
```bash
./scripts/deploy-aws.sh
```

**機能**:
- Terraform初期化・適用
- Lambda関数のデプロイ
- API Gateway設定
- DynamoDB構築

**前提条件**:
- AWS CLI認証設定済み
- Terraform 1.5+インストール済み

**関連ファイル**:
- `infrastructure/terraform/aws/`

---

### deploy-azure.sh

**用途**: Azure環境へのデプロイ

**使用方法**:
```bash
./scripts/deploy-azure.sh
```

**機能**:
- Azure Functions (Flex Consumption) デプロイ
- Cosmos DB設定
- Blob Storage設定
- Azure Front Door設定

**前提条件**:
- Azure CLI認証設定済み
- リソースグループ作成済み

**関連ファイル**:
- `.github/workflows/deploy-azure.yml`

---

### deploy-gcp.sh

**用途**: GCP環境へのデプロイ

**使用方法**:
```bash
./scripts/deploy-gcp.sh
```

**機能**:
- Cloud Run デプロイ
- Firestore設定
- Cloud Storage設定
- Cloud CDN設定

**前提条件**:
- gcloud CLI認証設定済み
- プロジェクトID設定済み

**関連ファイル**:
- `infrastructure/terraform/gcp/`

---

## テストツール

### test-e2e.sh

**用途**: マルチクラウドE2Eテストスイート

**使用方法**:
```bash
./scripts/test-e2e.sh
```

**テストカバレッジ**:
- **Total**: 18テスト（3環境 × 6テスト）
- AWS: Lambda + API Gateway + DynamoDB
- GCP: Cloud Run + Firestore
- Azure: Functions Flex + Cosmos DB

**テスト項目**:
1. Health Check
2. Create Message
3. List Messages
4. Get Message by ID
5. Update Message
6. Delete Message

**出力例**:
```
═══════════════════════════════════════════════════════
        Multi-Cloud E2E Test Suite
═══════════════════════════════════════════════════════

AWS: 6/6 tests passed ✅
GCP: 6/6 tests passed ✅
Azure: 6/6 tests passed ✅

Total Tests: 18
Passed: 18
All tests passed! ✓
```

**関連ドキュメント**:
- [README.md - E2Eテストスイート](../README.md#e2eテストスイート)

---

### test-endpoints.sh

**用途**: 全環境のエンドポイント疎通確認

**使用方法**:
```bash
./scripts/test-endpoints.sh
```

**テスト対象**:
- AWS API / Frontend
- Azure API / Frontend
- GCP API / Frontend

**機能**:
- HTTPステータスコード確認
- レスポンス内容検証
- レスポンスタイム測定

---

### test-api.sh

**用途**: 単一環境のAPI統合テスト

**使用方法**:
```bash
./scripts/test-api.sh -e <API_ENDPOINT> [--verbose]
```

**パラメータ**:
- `-e, --endpoint`: APIエンドポイントURL（必須）
- `--verbose`: 詳細モード

**使用例**:
```bash
# AWS環境のテスト
./scripts/test-api.sh -e https://YOUR_API_ID.execute-api.ap-northeast-1.amazonaws.com

# 詳細モード
./scripts/test-api.sh -e https://YOUR_API_ID.execute-api.ap-northeast-1.amazonaws.com --verbose
```

**テスト項目**:
- ヘルスチェック
- メッセージCRUD操作
- ページネーション
- エラーハンドリング
- バリデーション

---

### test-deployments.sh

**用途**: マルチクラウドデプロイメント統合テスト

**使用方法**:
```bash
./scripts/test-deployments.sh
```

**機能**:
- 全クラウドのAPI疎通確認
- フロントエンド疎通確認
- テスト結果サマリー表示

---

### test-cicd.sh

**用途**: GitHub Actionsワークフローのローカル検証

**使用方法**:
```bash
./scripts/test-cicd.sh
```

**検証項目**:
1. 環境検証（Terraform, Node.js, Python等）
2. ワークフローファイル構文確認
3. AWS Lambda パッケージングテスト
4. フロントエンドビルドテスト
5. AWS認証情報確認
6. GitHub Secrets確認
7. デプロイターゲット確認

---

## 管理・監視ツール

### manage-github-secrets.sh

**用途**: GitHub Secrets管理（統合版）

**使用方法**:
```bash
# ガイドモード（デフォルト）
./scripts/manage-github-secrets.sh

# 自動設定モード
./scripts/manage-github-secrets.sh --auto
```

**モード**:
- **ガイドモード**: 手動設定用のコマンド表示
- **自動設定モード**: ローカル環境変数から自動設定

**対象Secrets**:
- AWS: `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`
- Azure: `AZURE_CREDENTIALS`, `AZURE_*`
- GCP: `GCP_CREDENTIALS`, `GCP_PROJECT_ID`

**前提条件**:
- GitHub CLI (`gh`) インストール済み
- リポジトリへのアクセス権限

---

### setup-monitoring.sh

**用途**: CloudWatch監視設定（AWS専用）

**使用方法**:
```bash
# 基本設定
./scripts/setup-monitoring.sh

# メール通知付き
ALERT_EMAIL=your@email.com ./scripts/setup-monitoring.sh
```

**設定内容**:
- SNSトピック作成
- Lambda エラー/スロットリング/実行時間/同時実行数アラーム
- API Gateway 5XXエラーアラーム
- DynamoDB スロットリングアラーム
- CloudWatch Logsメトリクスフィルター
- CloudWatchダッシュボード作成

**環境変数**:
- `ALERT_EMAIL`: アラート通知先メールアドレス（任意）
- `AWS_REGION`: リージョン（デフォルト: ap-northeast-1）
- `PROJECT_NAME`: プロジェクト名（デフォルト: multicloud-auto-deploy）
- `ENVIRONMENT`: 環境名（デフォルト: staging）

---

### monitor-cicd.sh

**用途**: GitHub Actions実行状態の継続監視

**使用方法**:
```bash
# 全ワークフロー監視
./scripts/monitor-cicd.sh

# 特定ワークフロー監視
./scripts/monitor-cicd.sh --workflow=deploy-aws.yml
```

**パラメータ**:
- `--workflow=NAME`: 特定ワークフローのみ監視

**機能**:
- リアルタイム実行状態表示
- 成功/失敗/実行中の色分け
- 自動更新（30秒間隔）

---

### trigger-workflow.sh

**用途**: GitHub Actionsワークフローの手動トリガー

**使用方法**:
```bash
./scripts/trigger-workflow.sh <workflow> [environment]
```

**パラメータ**:
- `workflow`: aws / azure / gcp / multicloud
- `environment`: staging（デフォルト） / production

**使用例**:
```bash
# AWS デプロイ（staging）
./scripts/trigger-workflow.sh aws

# Azure デプロイ（production）
./scripts/trigger-workflow.sh azure production

# マルチクラウドデプロイ
./scripts/trigger-workflow.sh multicloud
```

---

## ユーティリティ

### generate-changelog.sh

**用途**: Git履歴からCHANGELOG.md自動生成

**使用方法**:
```bash
./scripts/generate-changelog.sh [output-file]
```

**パラメータ**:
- `output-file`: 出力ファイルパス（デフォルト: CHANGELOG.md）

**機能**:
- Gitコミット履歴を解析
- Conventional Commitsフォーマットで分類
- 日付ごとにグループ化
- Markdown形式で出力

**カテゴリ分類**:
- ✨ **feat**: 新機能
- 🐛 **fix**: バグ修正
- 📚 **docs**: ドキュメント変更
- ♻️ **refactor**: リファクタリング
- ⚡ **perf**: パフォーマンス改善
- 🧪 **test**: テスト追加・変更
- 💄 **style**: コードスタイル変更
- 🔧 **chore**: ビルド/ツール変更

**生成例**:
```bash
# デフォルト出力（CHANGELOG.md）
./scripts/generate-changelog.sh

# カスタム出力
./scripts/generate-changelog.sh docs/HISTORY.md
```

**前提条件**:
- Gitリポジトリ
- Conventional Commits形式のコミットメッセージ

---

### diagnostics.sh

**用途**: システム診断・ヘルスチェック

**使用方法**:
```bash
./scripts/diagnostics.sh
```

**診断項目**:
- インストール済みツール確認
- クラウドプロバイダー認証状態
- デプロイメントエンドポイント疎通
- Terraformリソース状態

---

### generate-pdf-documentation.sh

**用途**: 全Markdownドキュメントから包括的なPDFドキュメント生成

**使用方法**:
```bash
./scripts/generate-pdf-documentation.sh [output-filename]
```

**パラメータ**:
- `output-filename`: 出力PDFファイル名（デフォルト: multicloud-auto-deploy-documentation.pdf）

**機能**:
- 全Markdownファイルを章立てで結合
- 目次自動生成
- 日本語フォント対応（Noto CJK）
- 絵文字をテキスト表現に変換
- XeLaTeXによるPDF生成

**含まれるドキュメント**:
1. プロジェクト概要（README.md）
2. システムアーキテクチャ
3. セットアップガイド
4. デプロイメントガイド（AWS/Azure/GCP）
5. CI/CD設定
6. ツールリファレンス
7. APIエンドポイント
8. トラブルシューティング
9. サービス情報
10. コントリビューションガイド
11. 変更履歴（CHANGELOG.md）

**生成例**:
```bash
# デフォルト出力
./scripts/generate-pdf-documentation.sh

# カスタムファイル名
./scripts/generate-pdf-documentation.sh my-docs.pdf
```

**前提条件**:
- pandoc
- texlive-xetex
- texlive-lang-cjk
- fonts-noto-cjk
- librsvg2-bin

**インストールコマンド**:
```bash
sudo apt-get install -y pandoc texlive-xetex texlive-lang-cjk \
  fonts-noto-cjk fonts-noto-color-emoji librsvg2-bin
```

**終了コード**:
- 0: 成功
- 1: pandoc未インストール
- 2: ソースファイル不足
- 3: PDF生成失敗

---

## 推奨ワークフロー

### 初回セットアップ
```bash
1. ./scripts/manage-github-secrets.sh --auto   # Secrets設定
2. ./scripts/deploy-aws.sh                      # AWSデプロイ
3. ./scripts/test-endpoints.sh                  # 疎通確認
4. ./scripts/setup-monitoring.sh                # 監視設定
```

### 日常開発
```bash
1. git push                                     # 自動デプロイ（GitHub Actions）
2. ./scripts/monitor-cicd.sh                    # デプロイ監視
3. ./scripts/test-e2e.sh                        # E2Eテスト
```

### トラブルシューティング
```bash
1. ./scripts/diagnostics.sh                     # システム診断
2. ./scripts/test-deployments.sh                # 全環境テスト
3. docs/TROUBLESHOOTING.md                      # 問題解決ガイド参照
```

---

## 関連ドキュメント

- [README.md](../README.md) - プロジェクト概要
- [TROUBLESHOOTING.md](TROUBLESHOOTING.md) - トラブルシューティング
- [SETUP.md](SETUP.md) - セットアップガイド
- [CICD_SETUP.md](CICD_SETUP.md) - CI/CD設定
- [QUICK_REFERENCE.md](QUICK_REFERENCE.md) - クイックリファレンス
