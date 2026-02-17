# 環境ステータスレポート

最終更新: 2026-02-17

## 📋 概要

このドキュメントは、staging環境とproduction環境の現在のステータスを記録しています。各チャットで環境の前提知識として参照してください。

---

## 🔄 CI/CD ステータス

### 最新のワークフロー実行状況

| ワークフロー                 | ブランチ | ステータス | 日時             |
| ---------------------------- | -------- | ---------- | ---------------- |
| Deploy to AWS                | main     | ❌ failure | 2026-02-17 17:06 |
| Deploy to Azure              | main     | ❌ failure | 2026-02-17 17:06 |
| Deploy to GCP                | main     | ❌ failure | 2026-02-17 17:06 |
| Deploy Frontend to AWS       | main     | ✅ success | 2026-02-17 17:06 |
| Deploy Frontend to Azure     | main     | ✅ success | 2026-02-17 17:06 |
| Deploy Frontend to GCP       | main     | ✅ success | 2026-02-17 17:06 |
| Deploy Landing Page to AWS   | main     | ❌ failure | 2026-02-17 17:06 |
| Deploy Landing Page to Azure | main     | ✅ success | 2026-02-17 17:06 |
| Deploy Landing Page to GCP   | main     | ❌ failure | 2026-02-17 17:06 |
| Deploy to Azure              | develop  | ❌ failure | 2026-02-17 17:05 |

### 共通の失敗原因

1. **Pulumi Stack初期化エラー**: `Initialize Pulumi Stack` ステップで失敗
   - スタック名のハードコーディング問題は修正済み
   - 最新の失敗は別の原因の可能性

2. **Lambda Layer問題**: AWS Lambda関数で依存関係が見つからない
   - `No module named 'mangum'` エラー
   - Layerビルドの条件分岐に問題がある可能性

---

## ☁️ AWS 環境ステータス

### Staging環境 (ap-northeast-1)

| コンポーネント      | ステータス | URL/ID                                                        | 備考                           |
| ------------------- | ---------- | ------------------------------------------------------------- | ------------------------------ |
| **API**             | ❌ 失敗    | `https://z42qmqdqac.execute-api.ap-northeast-1.amazonaws.com` | Internal Server Error 500      |
| **Frontend**        | ✅ 正常    | `https://d1tf3uumcm4bo1.cloudfront.net`                       | CloudFront配信正常             |
| **Lambda Function** | ⚠️ エラー  | `multicloud-auto-deploy-staging-api`                          | mangumモジュールが見つからない |
| **Runtime**         | -          | Python 3.12                                                   | -                              |
| **Handler**         | -          | index.handler                                                 | -                              |
| **Layers**          | ❌ なし    | null                                                          | 依存関係がデプロイされていない |
| **Code Size**       | ⚠️ 29KB    | -                                                             | 非常に小さい（依存関係なし）   |

#### 問題点

```
[ERROR] Runtime.ImportModuleError: Unable to import module 'index': No module named 'mangum'
```

**原因**: Lambda Layerが正しくデプロイされていない

- ワークフローの `Build Lambda Layer` ステップが条件付き実行
- 条件: `if: ${{ github.event.inputs.use_klayers == 'false' }}`
- push トリガーでは評価されず、Layerがビルドされない

**解決策**:

1. Lambda Layerを手動でデプロイ（推奨）
2. ワークフローの条件を修正
3. 公開Layer + カスタムLayerのハイブリッド構成

👉 **詳細**: [AWS Lambda Layer最適化戦略](./AWS_LAMBDA_LAYER_STRATEGY.md)

#### エンドポイントテスト結果

```bash
# ヘルスチェック
curl https://z42qmqdqac.execute-api.ap-northeast-1.amazonaws.com/
# {"message":"Internal Server Error"}

# GET /api/messages/
curl https://z42qmqdqac.execute-api.ap-northeast-1.amazonaws.com/api/messages/
# {"message":"Internal Server Error"}

# Frontend (正常)
curl -I https://d1tf3uumcm4bo1.cloudfront.net/
# HTTP/2 200
```

### Production環境

**未構築** - mainブランチのデプロイが失敗しているため

---

## 🔵 Azure 環境ステータス

### Staging環境 (japaneast)

| コンポーネント      | ステータス | URL/ID                                                                                                        | 備考                 |
| ------------------- | ---------- | ------------------------------------------------------------------------------------------------------------- | -------------------- |
| **API**             | ✅ 正常    | `https://multicloud-auto-deploy-staging-func-d8a2guhfere0etcq.japaneast-01.azurewebsites.net/api/HttpTrigger` | version 3.0.0        |
| **Frontend**        | ✅ 正常    | `https://multicloud-frontend-f9cvamfnauexasd8.z01.azurefd.net`                                                | Azure Front Door配信 |
| **Function App**    | ✅ 稼働中  | `multicloud-auto-deploy-staging-func`                                                                         | -                    |
| **Storage Account** | ✅ 正常    | `mcadwebd45ihd`                                                                                               | -                    |
| **Resource Group**  | -          | `multicloud-auto-deploy-staging-rg`                                                                           | -                    |
| **Runtime**         | -          | Python 3.12                                                                                                   | -                    |

#### エンドポイントテスト結果

```bash
# ヘルスチェック (正常)
curl https://multicloud-auto-deploy-staging-func-d8a2guhfere0etcq.japaneast-01.azurewebsites.net/api/HttpTrigger/
# {"status":"ok","provider":"azure","version":"3.0.0"}

# Frontend (正常)
curl -I https://multicloud-frontend-f9cvamfnauexasd8.z01.azurefd.net/
# HTTP/2 200
```

#### 注意事項

- `/api/messages/` エンドポイントは空のレスポンスを返す
- エンドポイントパスが異なる可能性（要確認）

### Production環境

**未構築** - mainブランチのデプロイが失敗しているため

---

## 🟢 GCP 環境ステータス

### Staging環境 (asia-northeast1)

| コンポーネント     | ステータス    | URL/ID                                                               | 備考                               |
| ------------------ | ------------- | -------------------------------------------------------------------- | ---------------------------------- |
| **API**            | ⚠️ エラー     | `https://multicloud-auto-deploy-staging-api-son5b3ml7a-an.a.run.app` | ヘルスチェックは200、messagesは500 |
| **Frontend**       | ✅ 正常       | `http://34.117.111.182`                                              | Load Balancer経由                  |
| **Cloud Run**      | ⚠️ 部分的稼働 | `multicloud-auto-deploy-staging-api`                                 | -                                  |
| **Storage Bucket** | ✅ 正常       | `ashnova-multicloud-auto-deploy-staging-frontend`                    | -                                  |
| **Project ID**     | -             | `ashnova`                                                            | -                                  |
| **Firestore**      | -             | (default)                                                            | messages, posts collections        |

#### エンドポイントテスト結果

```bash
# ヘルスチェック (正常)
curl https://multicloud-auto-deploy-staging-api-son5b3ml7a-an.a.run.app/
# {"status":"ok","provider":"gcp","version":"3.0.0"}

# GET /api/messages/ (エラー)
curl https://multicloud-auto-deploy-staging-api-son5b3ml7a-an.a.run.app/api/messages/
# 500

# Frontend (正常)
curl -I http://34.117.111.182/
# HTTP/1.1 200 OK
```

#### 問題点

- ルートパス `/` は正常に応答
- `/api/messages/` は500エラーを返す
- Firestore接続またはルーティングの問題の可能性

### Production環境

**未構築** - mainブランチのデプロイが失敗しているため

---

## 📊 環境比較サマリー

| 項目                   | AWS Staging | Azure Staging    | GCP Staging   |
| ---------------------- | ----------- | ---------------- | ------------- |
| **API ヘルスチェック** | ❌ 500      | ✅ 200           | ✅ 200        |
| **API CRUD操作**       | ❌ 500      | ⚠️ 要確認        | ❌ 500        |
| **Frontend**           | ✅ 200      | ✅ 200           | ✅ 200        |
| **CDN**                | CloudFront  | Azure Front Door | Load Balancer |
| **API実装**            | Lambda      | Azure Functions  | Cloud Run     |
| **ストレージ**         | DynamoDB    | Cosmos DB        | Firestore     |

---

## 🔧 優先度の高い修正項目

### 1. AWS Lambda依存関係の修復 (最優先)

**問題**: mangumモジュールが見つからない

**📘 推奨ドキュメント**: [AWS Lambda Layer最適化戦略](./AWS_LAMBDA_LAYER_STRATEGY.md)

- 完全カスタムLayer（推奨）
- 公開Layer + カスタムLayerのハイブリッド構成
- Layer分離戦略（上級者向け）

**解決手順**:

#### オプションA: Lambda Layerを手動デプロイ（最速）

```bash
cd /workspaces/ashnova/multicloud-auto-deploy/services/api
bash ../../scripts/build-lambda-layer.sh
aws lambda publish-layer-version \
  --layer-name multicloud-auto-deploy-staging-dependencies \
  --zip-file fileb://lambda-layer.zip \
  --compatible-runtimes python3.12 \
  --region ap-northeast-1

# 出力されたLayerVersionArnをコピー
LAYER_ARN="arn:aws:lambda:ap-northeast-1:ACCOUNT_ID:layer:multicloud-auto-deploy-staging-dependencies:VERSION"

# Lambda関数にLayerをアタッチ
aws lambda update-function-configuration \
  --function-name multicloud-auto-deploy-staging-api \
  --layers $LAYER_ARN \
  --region ap-northeast-1
```

#### オプションB: ワークフローの修正

[deploy-aws.yml](file:///workspaces/ashnova/multicloud-auto-deploy/.github/workflows/deploy-aws.yml#L110-L111):

```yaml
- name: Build Lambda Layer
  # ❌ 削除: if: ${{ github.event.inputs.use_klayers == 'false' }}
  id: build_layer
  run: |
    # ...
```

### 2. GCP API /api/messages/ エンドポイントの修正

**問題**: ルートは正常だが、/api/messages/が500エラー

**調査手順**:

```bash
# Cloud Runログの確認
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=multicloud-auto-deploy-staging-api" \
  --limit 50 \
  --format json \
  --project ashnova
```

### 3. CI/CDワークフローの修正

**問題**: Pulumi Stack初期化エラー

**確認手順**:

```bash
# 最新の失敗ログを確認
curl -s "https://api.github.com/repos/PLAYER1-r7/multicloud-auto-deploy/actions/runs/22107983145/jobs" | \
  jq -r '.jobs[0].steps[] | select(.conclusion == "failure") | {name, conclusion}'
```

---

## 📝 次のステップ

### 短期（今日中）

1. ✅ 環境ステータスの確認と文書化（完了）
2. ⬜ AWS Lambda依存関係の修復
3. ⬜ GCP API /api/messages/ エンドポイントの調査と修復
4. ⬜ CI/CDワークフローの修正とテスト

### 中期（今週中）

1. ⬜ Production環境のセットアップ
2. ⬜ Azure /api/messages/ エンドポイントの確認
3. ⬜ 各環境の完全なCRUDテスト
4. ⬜ モニタリングとアラート設定の確認

### 長期（今月中）

1. ⬜ 環境間の設定統一化
2. ⬜ デプロイプロセスの自動化改善
3. ⬜ ドキュメントの整備と最新化
4. ⬜ セキュリティ監査とベストプラクティスの適用

---

## 📚 関連ドキュメント

- [AWS Lambda Layer最適化戦略](./AWS_LAMBDA_LAYER_STRATEGY.md) ⭐ **NEW**
- [デプロイ失敗調査レポート](./DEPLOYMENT_FAILURE_INVESTIGATION.md)
- [デプロイ監視ガイド](./DEPLOYMENT_MONITORING.md)
- [環境診断ガイド](./ENVIRONMENT_DIAGNOSTICS.md)
- [AWS デプロイメントガイド](./AWS_DEPLOYMENT.md)
- [Azure デプロイメントガイド](./AZURE_DEPLOYMENT.md)
- [GCP デプロイメントガイド](./GCP_DEPLOYMENT.md)
- [エンドポイント一覧](./ENDPOINTS.md)
- [クイックリファレンス](./QUICK_REFERENCE.md)
- [CI/CD設定ガイド](./CICD_SETUP.md)

---

## 🔄 更新履歴

- **2026-02-17**: 初版作成
  - 3クラウド全環境の動作確認実施
  - 問題点の特定と文書化
  - 修復手順の記載
