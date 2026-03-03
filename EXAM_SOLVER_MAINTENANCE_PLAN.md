# Exam Solver メンテナンス計画

**作成日**: 2026年3月3日
**ステータス**: アクティブ
**オーナー**: PLAYER1-r7

---

## 📋 概要

本ドキュメントは、旧大学入試解答アプリ（`/services/api`）のメンテナンス・開発方針を定義します。

新規開発プロジェクト `exam_solver` は **削除済み** です。今後は、既存の `/services/api` をベースにメンテナンスを継続します。

---

## 🏗️ 現在の実装状況

### コードベース

- **総コード量**: 1,105行の Python コード
- **依存パッケージ**: 52個（requirements.txt）
- **Azureパッケージ**: 21個（requirements-azure.txt）

### デプロイメント方式（Multi-Cloud）

- ✅ **Azure Functions**: `function_app.py`
  - ステータス: Production環境で稼働中
  - リージョン: Japan East (`japaneast`) -エントリーポイント: `HttpTrigger`

- ✅ **GCP Cloud Functions**: `function_gcp_wrapper.py`
  - ステータス: Staging環境で検証可能
  - リージョン: `asia-northeast1`

- ✅ **AWS Lambda**: `Dockerfile.lambda`
  - ステータス: Staging環境で検証可能
  - リージョン: `ap-northeast-1`

### テスト実装

- `tests/test_api_endpoints.py` - APIエンドポイント検証
- `tests/test_auth.py` - 認証機能テスト
- `tests/test_backends_integration.py` - マルチクラウド統合テスト
- 計20+個のテストモジュール

---

## 🔧 メンテナンスの優先順位

### 高優先度（今月中）

1. **テストカバレッジの改善**
   - 現在のカバレッジ率を測定
   - 新規機能追加前にカバレッジ70%以上を目標

2. **ドキュメント整備**
   - API仕様書の更新
   - セットアップガイドの整理
   - 既知の問題・制限事項の記録

3. **依存パッケージのセキュリティアップデート**
   - `--audit` でセキュリティ脆弱性チェック
   - CVE対応

### 中優先度（Q2）

1. **パフォーマンス最適化**
   - Azure Document Intelligence OCRのタイムアウト最適化
   - キャッシング層の導入検討

2. **エラーハンドリング改善**
   - ネットワーク障害時の リトライロジック
   - タイムアウト時のユーザー通知

3. **ログ & モニタリング強化**
   - Application Insights統合の拡張
   - 本番環境でのエラー検知ルール追加

### 低優先度（Q3以降）

1. **新機能開発**
   - 複数問題の一括解答機能
   - 図形問題への対応
   - 実装形式問題への対応

2. **UI/UX改善（フロントエンド統合）**
   - `/services/frontend_web` との統合
   - モバイル対応

---

## 📝 開発ワークフロー

### コード変更時

```bash
# 1. ローカル環境で検証
cd /workspaces/multicloud-auto-deploy/services/api

# 2. テスト実行
pytest tests/ --cov=app --cov-report=html

# 3. リント・フォーマット
ruff check --fix app/
black app/ tests/

# 4. ブランチ作成・コミット
git checkout -b feature/fix-description
git add .
git commit -m "fix: 説明"

# 5. プッシュ・PR作成
git push origin feature/fix-description
```

### デプロイメント時

#### フェーズ1: Staging環境での検証（必須）

```bash
# 1. Staging環境にデプロイ
cd /workspaces/multicloud-auto-deploy/services/api
./deploy-to-staging.sh

# 2. Staging環境でのテスト実行
curl -X GET https://staging-exam-solver.azurewebsites.net/health
curl -X POST https://staging-exam-solver.azurewebsites.net/v1/solve \
  -H "Content-Type: application/json" \
  -d '{"imageUrl":"...","university":"tokyo","year":2025}'

# 3. ログ確認（Application Insights）
az functionapp log tail \
  -n exam-solver-staging \
  -g multicloud-auto-deploy-staging-rg

# 4. パフォーマンス測定
# - 応答時間が500ms以下か確認
# - エラー率が0.1%以下か確認
# - リソース使用率が適正か確認
```

#### フェーズ2: Staging環境での検証チェックリスト

以下をすべて満たすまで、Production環境への適用は進まない：

- [ ] **テスト実行成功**
  - `pytest tests/ --cov=app` でカバレッジ70%以上
  - すべてのテストが PASS

- [ ] **APIエンドポイント検証**
  - GET /health → 200 OK
  - GET /v1/config → 200 OK + 正しい設定値
  - POST /v1/solve → 200 OK + 有効なレスポンス
  
- [ ] **エラーハンドリング**
  - 不正なURL入力時のエラー処理
  - ネットワークタイムアウト時の処理
  - Azure サービス障害時のフォールバック

- [ ] **パフォーマンス確認**
  - 平均応答時間 < 500ms
  - 99パーセンタイル応答時間 < 2000ms
  - エラー率 < 0.1%

- [ ] **ログ・モニタリング**
  - Application Insightsに异常がないか確認
  - エラーログの内容を確認（存在する場合）

- [ ] **セキュリティ確認**
  - 依存パッケージのセキュリティ脆弱性チェック: `pip audit`
  - 認証トークン・APIキーがログに出力されていないか確認

- [ ] **ドキュメント確認**
  - API仕様書が正確か確認
  - デプロイ手順が明確か確認
  - トラブルシューティングガイドが完全か確認

#### フェーズ3: Production環境への適用

上記チェックリストがすべて完了したら、Production環境へ適用：

```bash
# Production環境でのデプロイ（要承認）
cd /workspaces/multicloud-auto-deploy/services/api
./deploy-to-production.sh

# Production環境でのヘルスチェック
curl -X GET https://exam-solver.azurewebsites.net/health

# 本番環境ログの監視
az functionapp log tail \
  -n exam-solver \
  -g multicloud-auto-deploy-prod-rg
```

#### 本番環境デプロイ後の監視（24時間）

```bash
# 1. エラー率モニタリング
# - ダッシュボード: Azure Portal → Application Insights
# - アラート: エラー率 > 1% で通知

# 2. 応答時間モニタリング
# - ダッシュボード: Application Insights → パフォーマンス
# - アラート: 平均応答時間 > 1000ms で通知

# 3. リソース使用率モニタリング
# - CPU使用率 > 80%
# - メモリ使用率 > 85%

#問題発生時のロールバック
git revert <deployment-commit-hash>
./deploy-to-production.sh
```

---

## 🔍 環境別の設定

### 環境変数（`/services/api/.env`）

```env
# クラウドプロバイダ設定
CLOUD_PROVIDER=azure

# Azure Document Intelligence（OCR）
AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT=https://mcad-di-9e3f88.japaneast.api.cognitive.microsoft.com/
AZURE_DOCUMENT_INTELLIGENCE_KEY=<your-key>

# Azure OpenAI
AZURE_OPENAI_ENDPOINT=https://mcad-oai-d45ihd.openai.azure.com
AZURE_OPENAI_KEY=<your-key>
AZURE_OPENAI_DEPLOYMENT=gpt-4o
AZURE_OPENAI_API_VERSION=2024-12-01-preview

# GCP（オプション）
GCP_PROJECT_ID=<your-project>
GCP_CREDENTIALS_JSON=<path-to-credentials>

# AWS（オプション）
AWS_REGION=ap-northeast-1
AWS_ACCESS_KEY_ID=<your-key>
AWS_SECRET_ACCESS_KEY=<your-secret>
```

---

## 📚 ドキュメント参照

| ドキュメント                 | 説明                       |
| ---------------------------- | -------------------------- |
| `README.md`                  | プロジェクト概要           |
| `/docs/AI_AGENT_03_API.md`   | API仕様書                  |
| `/docs/AI_AGENT_04_INFRA.md` | インフラ構成               |
| `PRODUCTION_CHECKLIST.md`    | 本番デプロイチェックリスト |

---

## 🐛 既知の問題

1. **Dev Container環境のネットワーク制限**
   - ローカル開発環境ではAzure外部接続がタイムアウト
   - **対応**: ローカルではダミーOCRを使用、本番環境で実運用

2. **Azure Functions Cold Start**
   - 初回リクエスト時に3~5秒の遅延あり
   - **対応**: Keep-Alive設定、Application Insightsでのモニタリング

3. **GCP認証周り**
   - サービスアカウント設定が必要
   - **対応**: `gcloud auth` で認証後、credentials.jsonを配置

---

## ✅ チェックリスト

### 月次メンテナンス

- [ ] 依存パッケージのセキュリティアップデート確認
- [ ] テスト実行（手動確認）
- [ ] エラーログレビュー（Application Insights）
- [ ] ドキュメント更新確認

### 四半期ごと

- [ ] パフォーマンス分析
- [ ] ユーザーフィードバック収集
- [ ] 新機能のプランニング

---

## 📞 連絡先

- **プロジェクトオーナー**: PLAYER1-r7
- **GitHub**: https://github.com/PLAYER1-r7/multicloud-auto-deploy

---

## 参考資料

- [Azure Functions Python開発者ガイド](https://docs.microsoft.com/azure/azure-functions/functions-reference-python)
- [GCP Cloud Functions ガイド](https://cloud.google.com/functions/docs)
- [AWS Lambda ベストプラクティス](https://docs.aws.amazon.com/lambda/latest/dg/best-practices.html)
