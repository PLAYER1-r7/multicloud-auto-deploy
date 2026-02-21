# 10 — Remaining Tasks

> Parent: [AI_AGENT_GUIDE.md](AI_AGENT_GUIDE.md)  
> Last updated: 2026-02-21  
> **AI Agent Note**: Update this file when a task is resolved.

---

## Status Summary

```
Infrastructure (Pulumi):    ✅ All 3 clouds staging+production deployed
AWS API:                    ✅ Operational
GCP API (staging):          ✅ CRUD verified
GCP API (production):       ✅ CRUD verified
GCP Firebase Auth:          ✅ Google Sign-In + image upload/display verified (2026-02-21)
Azure API:                  ✅ Operational (POST 201 / GET 200 confirmed)
All CI/CD pipelines:        ✅ Green (2026-02-21 commit 27a44af)
Custom Domains:             ✅ All 3 clouds live (2026-02-21)
  www.aws.ashnova.jp:       ✅ HTTPS OK
  www.gcp.ashnova.jp:       ✅ HTTPS OK
  www.azure.ashnova.jp:     ✅ HTTPS OK (⚠️ /sns/* 間欠的 502 調査中)
Azure WAF:                  ❌ Not configured
Integration tests:          ⚠️ Not yet run (blockers resolved)
```

---

## 🔴 High Priority Tasks

| #   | Task                                       | Description                                                                                           | Reference                                                                          |
| --- | ------------------------------------------ | ----------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------- |
| 0   | **Azure AFD 502 間欠的エラー解消**         | AFD 経由 `/sns/*` が約 50% の確率で即時 502 を返す。Dynamic Consumption の stale TCP 接続が疑われる。 | [AZURE_SNS_FIX_REPORT.md](AZURE_SNS_FIX_REPORT.md#issue-2)                         |
| 1   | **Run integration tests (≥80% pass)**      | All backend blockers resolved. Run full suite on AWS/GCP/Azure and confirm.                           | [INTEGRATION_TESTS_GUIDE.md](INTEGRATION_TESTS_GUIDE.md)                           |
| 2   | **Verify Azure `PUT /posts` endpoint**     | End-to-end PUT routing on Azure has not been confirmed. Test and fix.                                 | —                                                                                  |
| 3   | **Confirm DynamoDB `PostIdIndex` GSI**     | GSI presence not confirmed. `GET /posts/{id}` may return 500.                                         | [RB-09](AI_AGENT_08_RUNBOOKS.md#rb-09-verify--create-the-dynamodb-postidindex-gsi) |
| 4   | **Fix `SNS:Unsubscribe` permission error** | `DELETE /posts` fails on SNS Unsubscribe call. Add `sns:Unsubscribe` to IAM or redesign the flow.     | —                                                                                  |
| 5   | **GCP HTTPS**                              | GCP frontend is HTTP only. Requires `TargetHttpsProxy` + Managed SSL certificate.                     | [09_SECURITY](AI_AGENT_09_SECURITY.md)                                             |
| 6   | **Enable Azure WAF**                       | WAF policy not applied to Front Door Standard SKU.                                                    | [09_SECURITY](AI_AGENT_09_SECURITY.md)                                             |

---

## 🟡 中優先タスク

| #   | タスク                                  | 概要                                                                                                                                                                                                                                                                                                                                               |
| --- | --------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 7   | **GCP 未使用静的IP 解放**               | RESERVED 状態の静的IP 3件（`ashnova-production-ip-c41311` / `multicloud-frontend-ip` / `simple-sns-frontend-ip`）を解放してコスト削減。詳細: [07_STATUS FinOps 節](AI_AGENT_07_STATUS.md#finops--gcp-未使用静的ipアドレス調査-2026-02-21)。                                                                                                        |
| 8   | **GCP 不要 Cloud Storage バケット削除** | Terraform 残骸バケット 4件（`ashnova-staging-frontend` / `ashnova-staging-function-source` / `multicloud-auto-deploy-tfstate` / `multicloud-auto-deploy-tfstate-gcp`）と FAILED 状態の Cloud Function `mcad-staging-api` を削除。詳細: [07_STATUS Cloud Storage 節](AI_AGENT_07_STATUS.md#finops--gcp-cloud-storage-不要バケット調査-2026-02-21)。 |
| 9   | **監視・アラート設定**                  | CloudWatch Alarms (AWS) / Azure Monitor (Azure) / Cloud Monitoring (GCP) を設定。                                                                                                                                                                                                                                                                  |
| 10  | **セキュリティ強化**                    | CORS `allowedOrigins` を実ドメインに変更。GCP SSL 証明書の `example.com` プレースホルダを更新。Azure Key Vault ネットワーク ACL 強化。                                                                                                                                                                                                             |
| 11  | **WAF ログ集約**                        | 3 クラウドの WAF ログを一箇所に集約して統一視点を持つ。                                                                                                                                                                                                                                                                                            |
| 12  | **Lambda Layer CI/CD 完全自動化**       | Layer ビルド・公開時の non-fatal warning を解消。                                                                                                                                                                                                                                                                                                  |
| 13  | **README 最終更新**                     | 最新エンドポイント・認証挙動・CI/CD 状態を README に反映。                                                                                                                                                                                                                                                                                         |
| 14  | **ブランチ保護ルール**                  | `main` への直接 push を禁止。PR + CI パス必須にする。                                                                                                                                                                                                                                                                                              |

---

## 🟢 低優先タスク

| #   | タスク                          | 概要                                                                                       |
| --- | ------------------------------- | ------------------------------------------------------------------------------------------ |
| 15  | **~~カスタムドメイン設定~~** ✅ | 全3クラウド設定完了（2026-02-21）。[CUSTOM_DOMAIN_SETUP.md](CUSTOM_DOMAIN_SETUP.md) 参照。 |
| 16  | **負荷テスト**                  | Locust などで性能ベースラインを確立。                                                      |
| 17  | **CI/CD 失敗通知**              | Slack / Discord webhook を追加。                                                           |
| 18  | **テストカバレッジ拡充**        | 現在は最小限。E2E + 認証テストを追加。                                                     |
| 19  | **カオスエンジニアリング**      | ネットワーク断・DB 停止・コールドスタートスパイクをシミュレート。                          |

---

## 推奨作業順序

```
1 → 統合テスト実行（現状確認）
2 → Azure PUT /posts 確認
3 → DynamoDB GSI 確認
4 → SNS:Unsubscribe 修正（DELETE フロー回復）
5 → GCP HTTPS（本番品質化）
6 → Azure WAF（本番品質化）
7 → GCP 未使用静的IP 解放（コスト削減・即対応可）
8 → GCP 不要 Cloud Storage バケット削除（コスト削減・即対応可）
9 → 監視・アラート
10 → セキュリティ強化
11-14 → 運用ポリッシュ
15-19 → 低優先
```

---

## 解決済みタスク（履歴）

| タスク                                       | 解決内容                                                                                        | コミット             |
| -------------------------------------------- | ----------------------------------------------------------------------------------------------- | -------------------- |
| GCP GCS CORSエラー                           | `x-ms-blob-type` ヘッダーをCORSに追加。uploads.jsでAzure URLのみに送信するよう修正。            | `1cf53b7`, `b5b4de5` |
| GCP Firebase Auth実装                        | Google Sign-Inフロー、httponly Cookieセッション、Firebase SDK v10.8.0、authorized domains設定。 | `3813577`            |
| GCS署名URL content_typeハードコード          | `generate_upload_urls()` で `content_types[index]` を正しく使用。拡張子マッピングも追加。       | `148b7b5`            |
| Firebase IDトークン期限切れ (401)            | `onIdTokenChanged` で自動リフレッシュ。`/sns/session` を再呼び出し。                            | `8110d20`            |
| GCP_SERVICE_ACCOUNT欠落                      | `deploy-gcp.yml` に `GCP_SERVICE_ACCOUNT` パラメータ追加。impersonated_credentials有効化。      | `27b10cc`            |
| CSS SVG 404 (starfield/ring-dark)            | `url("/static/...")` → `url("./...")` に修正。`app.css` v=4 にバージョンアップ。                | `0ed0805`            |
| GCS uploadsバケットの画像非公開              | `allUsers:objectViewer` を付与。Pulumi定義にもIAMBindingを追加。                                | `0ed0805`            |
| Azure `/posts` 404                           | Azure Function ルーティングは正常。テストレポートが古かった。POST 201/GET 200 確認。            | —                    |
| AWS Staging POST 401                         | `AUTH_DISABLED=true` → staging に追加。                                                         | `a2b8bb8`            |
| GCP Production GET /posts 500                | python312、`GCP_POSTS_COLLECTION=posts`、`SecretVersion` 削除、`functions-framework==3.10.1`    | `05829e60`           |
| deploy-gcp.yml ConcurrentUpdateError         | 全3ワークフローに `concurrency` グループ追加。                                                  | `a2b8bb8`            |
| GCP バックエンド実装                         | Firestore CRUD 完全実装。                                                                       | —                    |
| Azure バックエンド実装                       | Cosmos DB CRUD 完全実装。                                                                       | —                    |
| AWS CI/CD Lambda Layer 条件                  | 重複/条件分岐ステップを削除して単一の無条件ビルドに統一。                                       | `eaf8071c`           |
| Azure ハードコードリソースグループ           | 3ワークフローのハードコード `multicloud-auto-deploy-staging-rg` を Pulumi output に変更。       | `0912ac3`            |
| ワークフローファイルの二重管理               | サブディレクトリではなくルート `.github/workflows/` を編集するよう修正。                        | `c347727`            |
| ランディングページが SNS アプリを上書き      | フロントエンド CI のデプロイ先を `sns/` プレフィックスに変更。                                  | `c347727`            |
| AUTH_DISABLED=true バグ（AWS/Azure staging） | 条件分岐を削除して常に `AUTH_DISABLED=false` に統一。                                           | `6699586`            |
| ランディングページ SNS リンクが `:8080`      | ホスト名検出ロジックを3環境対応（local/devcontainer/CDN）に修正。                               | `0c485b7`            |
