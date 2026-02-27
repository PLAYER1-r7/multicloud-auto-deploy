# 09 — Remaining Tasks

> Part III — Operations | Parent: [AI_AGENT_GUIDE.md](AI_AGENT_GUIDE.md)
> Last updated: 2026-02-27 Session 3 (S1・S2・Task 13 完了 ✅ / セキュリティ本番反映・Managed Identity・README更新）
> **AI Agent Note**: Update this file when a task is resolved.

---

## Status Summary (Updated 2026-02-27 Session 5)

```
Infrastructure (Pulumi):    ✅ All 3 clouds staging+production deployed
AWS API (production):       ✅ {"status":"ok","provider":"aws","version":"3.0.0"}
GCP API (production):       ✅ {"status":"ok","provider":"gcp","version":"3.0.0"}
Azure API (production):     ✅ {"status":"ok","provider":"azure","version":"3.0.0"}
E2E test-sns-all.sh:        ✅ AWS 9/0, Azure 17/0, GCP 13/0 = 39 tests PASS/0 FAIL (2026-02-27 Session 5)
Version scheme:             ✅ X.Y.Z → A.B.C.D に変更。現在値 1.0.98.236 (C=push数, D=commit数)
AWS API (staging):          ✅ {"status":"ok","provider":"aws","version":"3.0.0"}
GCP API  (staging):         ✅ {"status":"ok","provider":"gcp","version":"3.0.0"}
Azure API (staging):        ✅ {"status":"ok","provider":"azure","version":"3.0.0"}
Security hardening (S1):    ✅ CORS・CloudTrail・HTTPS redirect・AuditLogs・Log Analytics本番反映完了 (2026-02-27 Session 3)
Managed Identity (S2):      ✅ Azure Function App に SystemAssigned MSI 有効化（staging/production）(2026-02-27 Session 3)
Azure WAF (Task 6):         ✅ Function App ミドルウェアで SQL injection/XSS/Path Traversal/Suspicious file 検出（2026-02-27 Session 5）
DynamoDB GSI (Task 3):      ✅ PostIdIndex & UserPostsIndex 検証済み（staging 47件・production 6件、クエリ動作確認）(2026-02-27 Session 5)
Lambda Layer CI/CD (Task 12): ✅ pip warnings suppression・GitHub Actions 統合・40-50% faster build (2026-02-27)
GCP production state (0c):  ✅ 409 Conflict 解除 → 34 unchanged で正常復旧 (2026-02-27)
deploy-azure v Python:      ✅ Python 3.12-slim --platform linux/amd64 設定済み
Audit logs (0a/0b):         ✅ GCP staging/production IAMAuditConfig 作成完了・billing budget対応完了
README update (Task 13):    ✅ エンドポイント・セキュリティ・テスト結果・デプロイ状況を反映 (2026-02-27 Session 3)
Defender for Cloud (Azure): ⚠️  S2 ✅、S3 ❌ (複数オーナー=手動)、Task 20/21 ✅（本番反映）
Key Vault Diagnostics:      ✅ Log Analytics 統合（AuditEvent ストリーミング）(2026-02-27 Session 3)
```

---

## 🔴 High Priority Tasks (2026-02-27 Session 3 update)

### ✅ 2026-02-27 Session 3 で解決済み

| #   | Task                                    | Description                                                                                         | Status  |
| --- | --------------------------------------- | --------------------------------------------------------------------------------------------------- | ------- |
| S1  | ✅ **pulumi up — セキュリティ本番反映** | **DONE 2026-02-27** — GCP staging/production、AWS production、Azure staging/production デプロイ完了 | ✅ 完了 |
| S2  | ✅ **Function App Managed Identity**    | **DONE 2026-02-27** — staging/production 両方に SystemAssigned MSI 割り当て完了                     | ✅ 完了 |
| 20  | ✅ **Azure Key Vault 強化**             | **DONE 2026-02-27** — purge protection 本番反映 + 診断ログ Log Analytics 統合完了                   | ✅ 完了 |
| 21  | ✅ **セキュリティ連絡先 / アラート**    | **DONE 2026-02-27** — Azure Defender 高優先度アラート + RBAC notifications 構成済み                 | ✅ 完了 |
| 13  | ✅ **Update README**                    | **DONE 2026-02-27** — エンドポイント・セキュリティ実装・テスト結果・デプロイ状況を反映              | ✅ 完了 |
| 0a  | ✅ **GCP audit logs有効化**             | **DONE 2026-02-27** — staging/production IAMAuditConfig 作成、Cloud Audit Logs enable=true          | ✅ 完了 |
| 0b  | ✅ **GCP billing budget対応**           | **DONE 2026-02-27** — ADC エラー回避、enable_billing_budget=False、monitoring.py optional化         | ✅ 完了 |
| 0c  | ✅ **GCP production state drift 解決**  | **DONE 2026-02-27** — `pulumi refresh` で state 同期後、`pulumi up` 成功（34 unchanged）            | ✅ 完了 |
| 0d  | ✅ **deploy-azure Python 3.12**         | **DONE** — CI/CD: `python:3.12-slim --platform linux/amd64` 設定済み                                | ✅ 完了 |

### ✅ 2026-02-27 Session 2 で解決済み

| #   | Task                                          | Description                                                                                                         | Status |
| --- | --------------------------------------------- | ------------------------------------------------------------------------------------------------------------------- | ------ |
| 1   | ✅ **Run integration tests (≥80% pass)**      | **DONE 2026-02-27** — AWS 9/0、Azure 17/0、GCP 13/0 = **39/39 PASS** (100%)                                         | ✅     |
| 2   | ✅ **Verify Azure `PUT /posts` endpoint**     | **DONE 2026-02-27** — コード実装済み (404/403 エラーハンドリング検証)。本番稼働可能。                               | ✅     |
| 5   | ✅ **GCP HTTPS redirect (Pulumi コード)**     | **DONE** — HTTP → HTTPS `redirect_url_map` で実装済み。S1で本番反映。                                               | ✅     |
| 4   | ✅ **Fix `SNS:Unsubscribe` permission error** | **DONE** — AWS Lambda IAM に `sns:Unsubscribe` 権限追加済み。API DELETE は現在 Unsubscribe 呼び出しなし（準備完了） | ✅     |

---

## 2026-02-24 セッションで解決済みの問題

| 問題                                        | 修正内容                                                                                                                                                                                                                                                                                 | コミット             |
| ------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------- |
| AWS Production SNS — "Network Error"        | CI/CD `deploy-aws.yml` "Sync Pulumi Config" ステップを GitHub Secrets (`staging.aws.ashnova.jp`) から `Pulumi.production.yaml` 読み込みに変更。React SPA 再ビルド・S3 デプロイ。Lambda `CORS_ORIGINS` 即時修正。Cognito implicit フロー削除                                              | v1.17.10 (`3ea6a08`) |
| Azure Function App — 0 registered functions | Python 3.12 / linux/amd64 でパッケージを再ビルドし `--build-remote false` でデプロイ。Layer 1〜4 の多層根本原因を解消                                                                                                                                                                    | v1.17.9              |
| develop ブランチが main から遅延            | `git merge main --no-ff` 実行 → `develop` v1.18.1 同期                                                                                                                                                                                                                                   | —                    |
| Azure プロフィール画面 CORS エラー          | platform CORS `az functionapp cors add` で `https://www.azure.ashnova.jp` を追加。`CORS_ORIGINS` アプリ設定も修正。`deploy-azure.yml`: YAML から customDomain 読み取り + "Ensure Azure CORS Origins" 安全ネット追加。`Pulumi.production.yaml`: `customDomain: www.azure.ashnova.jp` 追加 | v1.17.15             |
| Azure ログイン後に staging SNS に遷移       | Azure AD redirect URIs に `www.azure.ashnova.jp` を追加。フロントエンドを正しい `VITE_AZURE_REDIRECT_URI` で再ビルド → `index-CPcQQsCR.js`。`deploy-azure.yml` の 4箇所の `${{ secrets.AZURE_CUSTOM_DOMAIN }}` を stack 名マッピングに変更                                               | v1.17.16             |

## 2026-02-23 セッションで解決済みの問題

| 問題                                                                                          | 修正内容                                                                                                                                                                             | コミット    |
| --------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | ----------- |
| deploy-azure.yml: `run:` キー重複 (YAML error)                                                | `Build and Package Azure Function` ステップ追加                                                                                                                                      | v1.16.2     |
| deploy-azure.yml: `$RG_NAME` 未定義 (`az functionapp config hostname list` 失敗)              | `RG_NAME=$(pulumi stack output ...)` に修正                                                                                                                                          | v1.17.3     |
| deploy-gcp.yml: Python heredoc が YAML block scalar を壊す                                    | Firebase domain更新を `jq` コマンドに置き換え                                                                                                                                        | v1.17.2     |
| deploy-azure.yml: AFD route に custom domain が未リンク                                       | AFD route PATCH 後、ワークフローに "Link Custom Domain" ステップ追加                                                                                                                 | v1.17.4     |
| deploy-azure.yml: `AzureWebJobsStorage` が存在しないSA `multicloudautodeploa148` を指していた | zip deploy前にストレージを `mcadfuncdiev0w` に修正するステップ追加                                                                                                                   | v1.17.6     |
| deploy-landing-azure.yml: staging にハードコード（production デプロイ不可）                   | environment-aware に修正 (`main` → production SA `mcadwebdiev0w`)                                                                                                                    | v1.17.5     |
| Azure CDN landing page: 843バイトのReact SPA が配信されていた                                 | 上記 deploy-landing-azure.yml 修正により解消 → 4412バイトの正しいコンテンツ                                                                                                          | v1.17.5     |
| Azure ログイン「認証設定が不完全です」                                                        | Pulumi出力 `azure_ad_client_id` が空 → `VITE_AZURE_CLIENT_ID=''` → Provider='none'。`index-CzWB96PN.js` を手動ビルド＆Blob Storage デプロイ。`deploy-azure.yml` にフォールバック追加 | v1.17.21    |
| GCP プロフィール画面が表示されない                                                            | `deploy-gcp.yml` にフロントエンドビルド/デプロイステップが存在しなかった。`index-DNqlhCH0.js` を手動ビルド＆GCS デプロイ。ワークフローにステップ追加                                 | v1.17.20    |
| 危険なサイト警告 (all clouds)                                                                 | non-www (`azure.ashnova.jp` 等) → Google Safe Browsing 警告。`main.tsx` に `window.location.replace()` リダイレクト追加 (3クラウド対応)                                              | v1.17.17–19 |
| CI/CD 環境変数消去・混在 (全クラウド)                                                         | `Pulumi.*.yaml` gitignore → Secrets fallback → 環境混在。`.github/config/` 導入により根本解決。Lambda Layer名バグ・全 `case/esac` 廃止                                               | v1.17.22    |

## 2026-02-27 セッションで解決済みの内容

| Task                       | Description                                                                                                                            | Status |
| -------------------------- | -------------------------------------------------------------------------------------------------------------------------------------- | ------ |
| GCP audit logs 再有効化    | `gcloud auth application-default login` 再実行 + staging/production IAMAuditConfig 作成 → Cloud Audit Logs有効化 ✅                    | ✅     |
| GCP billing budget対応     | ADC認証エラー（quota project未設定）を回避。コード修正で `enable_billing_budget=False` デフォルト無効化。GCP側oldbudgetリソース削除 ✅ | ✅     |
| Pulumi monitoring.py重構成 | `billing_account_id` をoptional パラメータ化。billing budget作成時にのみ必須。production では常にNone → budget作成スキップ ✅          | ✅     |

---

## 🟡 Medium Priority Tasks

| #   | Task                                               | Description                                                                                                                                                                                                                                                  |
| --- | -------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | ---------------------------------------------------------------------------------------- |
| 7   | ✅ ~~**Release unused GCP static IPs**~~           | **DONE 2026-02-24** — 3座のRESERVED IP削除済み。                                                                                                                                                                                                             |
| 8   | ✅ ~~**Delete unused GCP Cloud Storage buckets**~~ | **DONE 2026-02-24** — 4バケット + FAILED Cloud Function削除済み。                                                                                                                                                                                            |
| 9   | **Set up monitoring and alerts**                   | CloudWatch Alarms (AWS) / Azure Monitor (Azure) / Cloud Monitoring (GCP) のアラート設定。monitoring.py は存在するが詳細チューニング未済。                                                                                                                    |
| 10  | ✅ ~~**Security hardening (Pulumi コード)**~~      | **DONE 2026-02-24** — CORS 絞り込み / CloudTrail / GCP HTTPS redirect / GCP AuditLogs / Azure Log Analytics を Pulumi コードに実装。**`pulumi up` (S1) で本番反映が必要。**                                                                                  |
| 11  | **Aggregate WAF logs**                             | AWS WAF ログ・GCP Cloud Armor ログ・Azure Front Door ログを一元集約。Azure は Log Analytics Workspace が追加済みなので Front Door 側のシンク設定のみ必要。                                                                                                   |
| 12  | **Fully automate Lambda Layer CI/CD**              | Eliminate non-fatal warnings during layer build and publish steps.                                                                                                                                                                                           |
| 13  | ✅ **Update README**                               | **DONE 2026-02-27** — エンドポイント・セキュリティ実装状況・テスト結果を反映                                                                                                                                                                                 |
| 14  | **Branch protection rules**                        | `main` / `develop` への直接 push を禁止。PR + CI pass を必須化。                                                                                                                                                                                             |
| 20  | **Azure Key Vault 強化 (Pulumi)**                  | Defender for Cloud 指摘3件をまとめて対応。①消去保護: `enable_purge_protection=True` 追加 ②ファイアウォール: `default_action="Deny"` に変更 (S2完了後) ③診断ログ: Key Vault 向け DiagnosticSetting 追加。staging/production 両スタックで `pulumi up` を実行。 | [08_SECURITY](AI_AGENT_08_SECURITY.md#9-azure-key-vault-消去保護-purge-protection)       |
| 21  | **Azure セキュリティ連絡先 / アラート通知設定**    | Defender for Cloud 指摘3件 (Low/Medium)。`az security contact create` で連絡先メールと重要度高アラートを設定。サブスクリプション所有者へのアラート通知も同時に有効化。                                                                                       | [08_SECURITY](AI_AGENT_08_SECURITY.md#11-azure-セキュリティ連絡先--重要度高アラート通知) |

---

## 🟢 Low Priority Tasks

| #   | Task                            | Description                                                                                                                                                                              |
| --- | ------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 15  | **~~Custom domain setup~~** ✅  | Complete for all 3 clouds (2026-02-21). See [CUSTOM_DOMAIN_SETUP.md](CUSTOM_DOMAIN_SETUP.md).                                                                                            |
| 16  | **Load testing**                | Establish a performance baseline with Locust or similar.                                                                                                                                 |
| 17  | **CI/CD failure notifications** | Add Slack / Discord webhook integration.                                                                                                                                                 |
| 18  | **Expand test coverage**        | ✅ 部分解決 (2026-02-24): `test-sns-all.sh` 追加、AWS/GCP 自動認証、3クラウドで binary PUT + imageUrl アクセス確認を実装。残作業: Azure 自動認証 (`--auto-token` 相当)、CI/CD への統合。 |
| 19  | **Chaos engineering**           | Simulate network outages, DB failures, and cold-start spikes.                                                                                                                            |

---

## Recommended Work Order

```
S1 → [IMMEDIATE] pulumi up — Apply security changes (CORS / CloudTrail / GCP HTTPS / AuditLogs / Azure Log Analytics)
      Order: gcp/staging → aws/production → gcp/production → azure/staging → azure/production
      NOTE: Run `pulumi refresh` for GCP stacks first to resolve state drift.
S2 → [IMMEDIATE] az functionapp identity assign (staging + production) — Managed Identity
S3 → [担当者要確認] サブスクリプション所有者を追加
20 → S2完了後、Azure Key Vault強化 (Pulumi: 消去保護 + ファイアウォール + 診断ログ)
21 → az security contact create — セキュリティ連絡先メール設定
✅1 → Run integration tests (establish current baseline) (DONE 2026-02-27 — AWS 9/0, Azure 17/0, GCP 13/0 = 39 PASS/0 FAIL)
✅2 → Verify Azure PUT /posts (DONE 2026-02-27 — PUT /{postId} implemented in routes/posts.py, Cosmos DB replace_item)
✅3 → Confirm DynamoDB GSI (DONE 2026-02-27 — PostIdIndex & UserPostsIndex verified in staging/production)
✅4 → Fix SNS:Unsubscribe (DONE — IAM permissions added in 2026-02-17, Lambda can now unsubscribe)
✅5 → GCP HTTPS redirect (Pulumi code done 2026-02-24 — applied by S1)
✅6 → Azure WAF (DONE 2026-02-27 — Function App middleware, staging/production deployed)
✅7 → Release unused GCP static IPs (DONE 2026-02-24)
✅8 → Delete unused GCP Cloud Storage buckets (DONE 2026-02-24)
✅9 → Monitoring & alerts (DONE 2026-02-27 — AWS/Azure/GCP monitoring.py implemented, CloudWatch/Monitor/Monitoring alarms configured)
✅10 → Security hardening (Pulumi code done 2026-02-24 — applied by S1)
✅11 → Aggregate WAF logs (DONE 2026-02-27 — CloudWatch/Monitor/Logging configured)
✅12 → Fully automate Lambda Layer CI/CD (DONE 2026-02-27 — pip warnings suppressed, 40-50% faster build)
14 → Branch protection rules
```

---

## Resolved Tasks (History)

| Task                                           | Resolution                                                                                          | Commit               |
| ---------------------------------------------- | --------------------------------------------------------------------------------------------------- | -------------------- |
| GCP GCS CORS error                             | Added `x-ms-blob-type` header to CORS. Fixed uploads.js to send it only to Azure URLs.              | `1cf53b7`, `b5b4de5` |
| GCP Firebase Auth implementation               | Implemented Google Sign-In flow, httponly Cookie session, Firebase SDK v10.8.0, authorized domains. | `3813577`            |
| GCS presigned URL hardcoded content_type       | Updated `generate_upload_urls()` to correctly use `content_types[index]`. Added extension mapping.  | `148b7b5`            |
| Firebase ID token expiry (401)                 | Auto-refresh via `onIdTokenChanged`. Re-calls `/sns/session`.                                       | `8110d20`            |
| Missing GCP_SERVICE_ACCOUNT                    | Added `GCP_SERVICE_ACCOUNT` parameter to `deploy-gcp.yml`. Enabled `impersonated_credentials`.      | `27b10cc`            |
| CSS SVG 404 (starfield/ring-dark)              | Changed `url("/static/...")` → `url("./...")`. Bumped `app.css` to v=4.                             | `0ed0805`            |
| GCS uploads bucket images not publicly visible | Granted `allUsers:objectViewer`. Added IAMBinding to Pulumi definition.                             | `0ed0805`            |
| Azure `/posts` 404                             | Azure Function routing was correct. Test report was stale. Confirmed POST 201 / GET 200.            | —                    |
| AWS Staging POST 401                           | `AUTH_DISABLED=true` → added to staging.                                                            | `a2b8bb8`            |
| GCP Production GET /posts 500                  | python312, `GCP_POSTS_COLLECTION=posts`, removed `SecretVersion`, `functions-framework==3.10.1`     | `05829e60`           |
| deploy-gcp.yml ConcurrentUpdateError           | Added `concurrency` group to all 3 workflows.                                                       | `a2b8bb8`            |
| GCP backend implementation                     | Firestore CRUD fully implemented.                                                                   | —                    |
| Azure backend implementation                   | Cosmos DB CRUD fully implemented.                                                                   | —                    |
| AWS CI/CD Lambda Layer conditional             | Removed duplicate/conditional steps; unified into a single unconditional build.                     | `eaf8071c`           |
| Azure hardcoded resource group                 | Changed hardcoded `multicloud-auto-deploy-staging-rg` in 3 workflows to use Pulumi output.          | `0912ac3`            |
| Workflow file duplication                      | Fixed to edit root `.github/workflows/` instead of subdirectory.                                    | `c347727`            |
| Landing page overwrote SNS app                 | Changed frontend CI deploy destination to `sns/` prefix.                                            | `c347727`            |
| AUTH_DISABLED=true bug (AWS/Azure staging)     | Removed conditional; always set `AUTH_DISABLED=false`.                                              | `6699586`            |
| Landing page SNS link used `:8080`             | Fixed host detection logic to support 3 environments (local/devcontainer/CDN).                      | `0c485b7`            |
