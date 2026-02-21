# 10 — Remaining Tasks

> Parent: [AI_AGENT_GUIDE.md](AI_AGENT_GUIDE.md)  
> Last updated: 2026-02-21 (高優先 #1-6 全解決)  
> **AI Agent Note**: Update this file when a task is resolved.

---

## Status Summary

```
Infrastructure (Pulumi):    ✅ All 3 clouds staging+production deployed
AWS API:                    ✅ Operational, auth tests passed
GCP API (staging):          ✅ CRUD verified, auth tests passed
GCP API (production):       ✅ CRUD verified
GCP Firebase Auth:          ✅ Google Sign-In + image upload/display verified (2026-02-21)
Azure API:                  ✅ Operational, auth tests passed (AUTH_DISABLED=false fixed 2026-02-21)
All CI/CD pipelines:        ✅ Green (2026-02-21 commit d8b6afe)
Azure WAF:                  ❌ Not configured (deferred: cost consideration)
Staging SNS tests (unauth): ✅ Run on all 3 clouds (2026-02-21) — 9/10 each (SPA deep link known)
Authenticated CRUD tests:   ✅ AWS 6/6 PASS, Azure/GCP auth-rejection verified (2026-02-21)
SPA deep link fallback:     ✅ frontend_web catch-all route added (redirect → home on 404)
```

---

## 🔴 高優先タスク ─ 解決済み

| #   | タスク                                       | 解決日       | 結果                                                                                       |
| --- | -------------------------------------------- | ------------ | ------------------------------------------------------------------------------------------ |
| 1   | **認証付きCRUDテスト実行**                   | 2026-02-21   | AWS 6/6 PASS (POST/GET/PUT/DELETE + 未認証401確認)。Azure/GCP は health+auth-rejection ✅  |
| 2   | **Azure `PUT /posts` エンドポイント確認**    | 2026-02-21   | PUT `/api/posts/{id}` → 401 (正常)。エンドポイント存在・認証正常確認済み                  |
| 3   | **SPA deep link 404 修正 (Azure/GCP)**       | 2026-02-21   | `frontend_web` に `GET /{path:path}` catch-all 追加。未知パス → home 302 リダイレクト     |
| 4   | **DynamoDB `PostIdIndex` GSI 確認**          | 2026-02-21   | `PostIdIndex` (hash: `postId`) ACTIVE確認、22 items。`GET /posts/{id}` 正常動作            |
| 5   | **`SNS:Unsubscribe` 権限エラー修正**         | 2026-02-21   | コード調査により `delete_post` にSNS呼び出しなし。タスク無効 (誤検知)                     |
| 6   | **GCP HTTPS**                                | 2026-02-21   | ⚠️ LB 443 portは存在するがSSL証明書が`example.com`プレースホルダでPROVISIONING_FAILED。カスタムドメイン設定が前提条件。**黄優先#14に移動** |

---

## 🟡 残存高優先タスク

| #   | タスク                   | 概要                                                                                                                                                       |
| --- | ------------------------ | ---------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 7   | ~~**Azure WAF**~~        | **見送り** (コスト見合い)。Front Door Standard SKU ではWAFポリシー適用にPremium SKUへのアップグレードが必要                                               |

---

## 🟡 中優先タスク

| #   | タスク                            | 概要                                                                                                                                   |
| --- | --------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------- |
| 8   | **監視・アラート設定**            | CloudWatch Alarms (AWS) / Azure Monitor (Azure) / Cloud Monitoring (GCP) を設定。                                                      |
| 9   | **セキュリティ強化**              | CORS `allowedOrigins` を実ドメインに変更。GCP SSL 証明書の `example.com` プレースホルダを更新。Azure Key Vault ネットワーク ACL 強化。 |
| 10  | **WAF ログ集約**                  | 3 クラウドの WAF ログを一箇所に集約して統一視点を持つ。                                                                                |
| 11  | **Lambda Layer CI/CD 完全自動化** | Layer ビルド・公開時の non-fatal warning を解消。                                                                                      |
| 12  | **README 最終更新**               | 最新エンドポイント・認証挙動・CI/CD 状態を README に反映。                                                                             |
| 13  | **ブランチ保護ルール**            | `main` への直接 push を禁止。PR + CI パス必須にする。                                                                                  |

---

## 🟢 低優先タスク

| #   | タスク                     | 概要                                                                                                                                 |
| --- | -------------------------- | ------------------------------------------------------------------------------------------------------------------------------------ |
| 14  | **カスタムドメイン設定**   | `aws.yourdomain.com` / `azure.yourdomain.com` / `gcp.yourdomain.com` を設定。[CUSTOM_DOMAIN_SETUP.md](CUSTOM_DOMAIN_SETUP.md) 参照。 |
| 15  | **負荷テスト**             | Locust などで性能ベースラインを確立。                                                                                                |
| 16  | **CI/CD 失敗通知**         | Slack / Discord webhook を追加。                                                                                                     |
| 17  | **テストカバレッジ拡充**   | 現在は最小限。E2E + 認証テストを追加。                                                                                               |
| 18  | **カオスエンジニアリング** | ネットワーク断・DB 停止・コールドスタートスパイクをシミュレート。                                                                    |

---

## 推奨作業順序

```
高優先 #1-6 完了 (2026-02-21) ✅
高優先 #7 (Azure WAF) → 見送り (コスト)
8 → 監視・アラート (次の高優先)
9 → セキュリティ強化 (CORS 実ドメイン化、GCP カスタムドメイン設定)
10-13 → 運用ポリッシュ
14 → カスタムドメイン設定 (GCP HTTPS も含む)
15-18 → 低優先
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
| Azure staging AUTH_DISABLED=true (再発)      | deploy-azure.yml のステージング分岐が `true` を再設定していた。常に `false` に統一。            | `d8b6afe`            |
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
