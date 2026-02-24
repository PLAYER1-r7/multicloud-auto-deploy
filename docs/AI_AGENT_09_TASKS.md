# 09 — Remaining Tasks

> Part III — Operations | Parent: [AI_AGENT_GUIDE.md](AI_AGENT_GUIDE.md)
> Last updated: 2026-02-24 (Defender for Cloud セキュアスコア分析・新規タスク追加: S2/S3/#20/#21)
> **AI Agent Note**: Update this file when a task is resolved.

---

## Status Summary

```
Infrastructure (Pulumi):    ✅ All 3 clouds staging+production deployed
AWS API (production):       ✅ {"status":"ok","provider":"aws","version":"3.0.0"}
GCP API (production):       ✅ {"status":"ok","provider":"gcp","version":"3.0.0"}
Azure API (production):     ✅ {"status":"ok","provider":"azure","version":"3.0.0"} (修復 2026-02-24)
E2E test-sns-all.sh:        ✅ AWS 9/0/4, Azure 17/0/2, GCP 13/0/4 (PASS/FAIL/SKIP) — production read-only (2026-02-24 commit 73af560)
Version scheme:             ✅ X.Y.Z → A.B.C.D に変更。現在値 1.0.84.204 (C=push数, D=commit数) (2026-02-24 commit c2f6870)
AWS API (staging):          ✅ {"status":"ok","provider":"aws","version":"3.0.0"} (2026-02-24 #246)
GCP API (staging):          ✅ {"status":"ok","provider":"gcp","version":"3.0.0"} (2026-02-24 #214)
Azure API (staging):        ✅ {"status":"ok","provider":"azure","version":"3.0.0"} (2026-02-24 #273)
Security hardening (Pulumi code): ✅ CORS *→実ドメイン / CloudTrail / GCP HTTPS redirect / GCP AuditLogs / Azure Log Analytics — コード実装完了 (2026-02-24)
  ⚠️  未適用: 各クラウドで `pulumi up` 実行が必要
Defender for Cloud (Azure): ⚠️  新規タスク 4件追加 (2026-02-24) — S2 (Managed Identity) / S3 (所有者複数) / #20 (Key Vault強化) / #21 (セキュリティ連絡先)
```

---

## 🔴 High Priority Tasks (2026-02-24 update)

### ⚠️ 残存問題・要 pulumi up

| #   | Task                                             | Description                                                                                                                                                                                  | Reference                                                |
| --- | ------------------------------------------------ | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------- |
| S1  | **pulumi up — セキュリティ変更を本番反映**       | Pulumi コードへの実装は完了。各クラウドで `pulumi up` を実行してインフラに適用する。対象: CORS 絞り込み / CloudTrail / GCP HTTPS redirect / GCP AuditLogs / Azure Log Analytics。            | [08_SECURITY](AI_AGENT_08_SECURITY.md)                   |
| S2  | **Function App Managed Identity 有効化**         | Defender for Cloud 指摘 (Medium)。staging / production 両 Function App に Managed Identity が未設定。Azure CLI で即時対応可能。Key Vault ファイアウォール強化 (#20) の前提条件。`az functionapp identity assign` を実行。 | [08_SECURITY](AI_AGENT_08_SECURITY.md#8-function-app-managed-identity) |
| S3  | **サブスクリプション所有者の複数設定**           | Defender for Cloud 指摘 (High)。現在の所有者 (`sat0sh1kawada`) のみ。2人目の Owner を Azure Portal / CLI で追加。担当者の運用判断が必要。                                                  | [08_SECURITY](AI_AGENT_08_SECURITY.md#12-サブスクリプション所有者の複数設定) |
| 0b  | **GCP Pulumi state drift 修正 (非ブロッキング)** | `ManagedSslCertificate` 400 + `URLMap` 412 で `pulumi up` 失敗。`pulumi refresh` で解消予定。S1 と合わせて実施。                                                                             | [STATUS](AI_AGENT_06_STATUS.md)                          |
| 0d  | **deploy-azure.yml Python 3.11→3.12 ビルド修正** | `Build and Package` ステップが `python:3.11-slim` でビルドしているが `functionAppConfig.runtime.version = "3.12"` → 次回 CI 再発リスク。`python:3.12-slim --platform linux/amd64` に変更要。 | [STATUS](AI_AGENT_06_STATUS.md)                          |
| 1   | **Run integration tests (≥80% pass)**            | All backend blockers resolved. Run full suite on AWS/GCP/Azure and confirm.                                                                                                                  | [INTEGRATION_TESTS_GUIDE.md](INTEGRATION_TESTS_GUIDE.md) |
| 2   | **Verify Azure `PUT /posts` endpoint**           | End-to-end PUT routing on Azure has not been confirmed. Test and fix.                                                                                                                        | —                                                        |
| 4   | **Fix `SNS:Unsubscribe` permission error**       | `DELETE /posts` fails on SNS Unsubscribe call. Add `sns:Unsubscribe` to IAM or redesign the flow.                                                                                            | —                                                        |
| 5   | ✅ **GCP HTTPS redirect (Pulumi コード済み)**    | HTTP → HTTPS は `redirect_url_map` で実装済み。`pulumi up` (S1) で反映される。                                                                                                               | [08_SECURITY](AI_AGENT_08_SECURITY.md)                   |
| 6   | **Enable Azure WAF**                             | WAF policy not applied to Front Door Standard SKU. Premium SKU へのアップグレード、または Standard SKU 向け WAF Policy の作成が必要。                                                        | [08_SECURITY](AI_AGENT_08_SECURITY.md)                   |

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

---

## 🟡 Medium Priority Tasks

| #   | Task                                               | Description                                                                                                                                                                 |
| --- | -------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 7   | ✅ ~~**Release unused GCP static IPs**~~           | **DONE 2026-02-24** — 3座のRESERVED IP削除済み。                                                                                                                            |
| 8   | ✅ ~~**Delete unused GCP Cloud Storage buckets**~~ | **DONE 2026-02-24** — 4バケット + FAILED Cloud Function削除済み。                                                                                                           |
| 9   | **Set up monitoring and alerts**                   | CloudWatch Alarms (AWS) / Azure Monitor (Azure) / Cloud Monitoring (GCP) のアラート設定。monitoring.py は存在するが詳細チューニング未済。                                   |
| 10  | ✅ ~~**Security hardening (Pulumi コード)**~~      | **DONE 2026-02-24** — CORS 絞り込み / CloudTrail / GCP HTTPS redirect / GCP AuditLogs / Azure Log Analytics を Pulumi コードに実装。**`pulumi up` (S1) で本番反映が必要。** |
| 11  | **Aggregate WAF logs**                             | AWS WAF ログ・GCP Cloud Armor ログ・Azure Front Door ログを一元集約。Azure は Log Analytics Workspace が追加済みなので Front Door 側のシンク設定のみ必要。                  |
| 12  | **Fully automate Lambda Layer CI/CD**              | Eliminate non-fatal warnings during layer build and publish steps.                                                                                                          |
| 13  | **Update README**                                  | Reflect current endpoints, auth behavior, and CI/CD status in the README.                                                                                                   |
| 14  | **Branch protection rules**                        | `main` / `develop` への直接 push を禁止。PR + CI pass を必須化。                                                                                                            |
| 20  | **Azure Key Vault 強化 (Pulumi)** | Defender for Cloud 指摘3件をまとめて対応。①消去保護: `enable_purge_protection=True` 追加 ②ファイアウォール: `default_action="Deny"` に変更 (S2完了後) ③診断ログ: Key Vault 向け DiagnosticSetting 追加。staging/production 両スタックで `pulumi up` を実行。 | [08_SECURITY](AI_AGENT_08_SECURITY.md#9-azure-key-vault-消去保護-purge-protection) |
| 21  | **Azure セキュリティ連絡先 / アラート通知設定**   | Defender for Cloud 指摘3件 (Low/Medium)。`az security contact create` で連絡先メールと重要度高アラートを設定。サブスクリプション所有者へのアラート通知も同時に有効化。      | [08_SECURITY](AI_AGENT_08_SECURITY.md#11-azure-セキュリティ連絡先--重要度高アラート通知) |

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
1 → Run integration tests (establish current baseline)
2 → Verify Azure PUT /posts
3 → Confirm DynamoDB GSI
4 → Fix SNS:Unsubscribe (restore DELETE flow)
✅5 → GCP HTTPS redirect (Pulumi code done 2026-02-24 — applied by S1)
6 → Azure WAF (production quality)
✅7 → Release unused GCP static IPs (DONE 2026-02-24)
✅8 → Delete unused GCP Cloud Storage buckets (DONE 2026-02-24)
9 → Monitoring & alerts
✅10 → Security hardening (Pulumi code done 2026-02-24 — applied by S1)
11-14 → Operational polish
15-19 → Low priority
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
