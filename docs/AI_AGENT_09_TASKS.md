# 09 — Remaining Tasks

> Part III — Operations | Parent: [AI_AGENT_GUIDE.md](AI_AGENT_GUIDE.md)  
> Last updated: 2026-02-24  
> **AI Agent Note**: Update this file when a task is resolved.

---

## Status Summary

```
Infrastructure (Pulumi):    ✅ All 3 clouds staging+production deployed
AWS API (production):       ✅ {"status":"ok","provider":"aws","version":"3.0.0"}
GCP API (production):       ✅ {"status":"ok","provider":"gcp","version":"3.0.0"}
Azure API (production):     ✅ {"status":"ok","provider":"azure","version":"3.0.0"} (修復 2026-02-24)
AWS SNS Network Error:      ✅ RESOLVED 2026-02-24 (CI/CD customDomain 上書きバグ修正 / CORS_ORIGINS 修正)
Azure CORS エラー (Profile): ✅ RESOLVED 2026-02-24 (platform CORS + CORS_ORIGINS に www.azure.ashnova.jp 追加 / CI/CD 安全ネット追加)
Azure ログイン staging リダイレクト: ✅ RESOLVED 2026-02-24 (AD redirect URI追加 / フロント再ビルド / deploy-azure.yml 全4箇所 AZURE_CUSTOM_DOMAIN 修正)
Landing Pages (production): ✅ 37/37 PASS — AWS/Azure/GCP全クラウド 4400-4450 bytes 正常コンテンツ
Custom Domains (all):       ✅ www.aws/azure/gcp.ashnova.jp HTTPS 200
CI/CD pipelines:
  deploy-aws.yml:           ✅ YAML修正済み / Sync Pulumi Config を YAML ファイルから読み込むよう修正
  deploy-azure.yml:         ✅ YAML修正済み / "Ensure Azure CORS Origins" 安全ネット追加 / customDomain を YAML から読み取り → deploy 4箇所すべて stack 名マッピングに統一
  deploy-gcp.yml:           ✅ YAML修正済み (python heredoc→jq) / ⚠️ Pulumi state drift
  deploy-landing-azure.yml: ✅ 修正済み — staging hardcoded → environment-aware
  その他:                   ✅ 全10ワークフロー YAML valid
develop branch sync:        ⚠️ main v1.17.16 に未同期 (要実施)
```

---

## 🔴 High Priority Tasks (2026-02-24 update)

### ⚠️ 残存: Azure Function App — CI/CD 再発リスク

| #   | Task                                             | Description                                                                                                                                                                                    | Reference                                                                 |
| --- | ------------------------------------------------ | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------- |
| 0b  | **GCP Pulumi state drift 修正 (非ブロッキング)** | `ManagedSslCertificate` 400 + `URLMap` 412 で `pulumi up` 失敗。`pulumi refresh` で解消予定。                                                                                                  | [STATUS#2](AI_AGENT_06_STATUS.md#2-gcp-pulumi-state-drift-非ブロッキング) |
| 0d  | **deploy-azure.yml Python 3.11→3.12 ビルド修正** | `Build and Package` ステップが `python:3.11-slim` でビルドしているが `functionAppConfig.runtime.version = "3.12"` → 次回CI再発リスク。`python:3.12-slim --platform linux/amd64` に変更が必要。 | [STATUS#1 Layer3](AI_AGENT_06_STATUS.md)                                  |

### ✅ 解決済み (2026-02-24)

| #   | Task                                     | 解決内容                                                                                                                  | コミット |
| --- | ---------------------------------------- | ------------------------------------------------------------------------------------------------------------------------- | -------- |
| 0a  | **Azure Function App 関数登録0件の修正** | Python 3.12 / linux/amd64 ビルド + `--build-remote false` デプロイで解決。`admin/functions = [{"name":"HttpTrigger"}]` ✅ | v1.17.9  |
| 0c  | **develop ブランチを main に同期**       | `git merge main --no-ff` 実行済み。`develop` v1.18.1 / `main` v1.17.10 ✅ (コミット `7efca78`)                            | —        |

### 既存タスク

| #   | Task                                       | Description                                                                                       | Reference                                                |
| --- | ------------------------------------------ | ------------------------------------------------------------------------------------------------- | -------------------------------------------------------- |
| 1   | **Run integration tests (≥80% pass)**      | All backend blockers resolved. Run full suite on AWS/GCP/Azure and confirm.                       | [INTEGRATION_TESTS_GUIDE.md](INTEGRATION_TESTS_GUIDE.md) |
| 2   | **Verify Azure `PUT /posts` endpoint**     | End-to-end PUT routing on Azure has not been confirmed. Test and fix.                             | —                                                        |
| 4   | **Fix `SNS:Unsubscribe` permission error** | `DELETE /posts` fails on SNS Unsubscribe call. Add `sns:Unsubscribe` to IAM or redesign the flow. | —                                                        |
| 5   | **GCP HTTPS**                              | GCP frontend is HTTP only. Requires `TargetHttpsProxy` + Managed SSL certificate.                 | [09_SECURITY](AI_AGENT_08_SECURITY.md)                   |
| 6   | **Enable Azure WAF**                       | WAF policy not applied to Front Door Standard SKU.                                                | [09_SECURITY](AI_AGENT_08_SECURITY.md)                   |

---

## 2026-02-24 セッションで解決済みの問題

| 問題                                        | 修正内容                                                                                                                                                                                                                                                                                 | コミット             |
| ------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------- |
| AWS Production SNS — "Network Error"        | CI/CD `deploy-aws.yml` "Sync Pulumi Config" ステップを GitHub Secrets (`staging.aws.ashnova.jp`) から `Pulumi.production.yaml` 読み込みに変更。React SPA 再ビルド・S3 デプロイ。Lambda `CORS_ORIGINS` 即時修正。Cognito implicit フロー削除                                              | v1.17.10 (`3ea6a08`) |
| Azure Function App — 0 registered functions | Python 3.12 / linux/amd64 でパッケージを再ビルドし `--build-remote false` でデプロイ。Layer 1〜4 の多層根本原因を解消                                                                                                                                                                    | v1.17.9              |
| develop ブランチが main から遅延            | `git merge main --no-ff` 実行 → `develop` v1.18.1 同期                                                                                                                                                                                                                                   | —                    |
| Azure プロフィール画面 CORS エラー          | platform CORS `az functionapp cors add` で `https://www.azure.ashnova.jp` を追加。`CORS_ORIGINS` アプリ設定も修正。`deploy-azure.yml`: YAML から customDomain 読み取り + "Ensure Azure CORS Origins" 安全ネット追加。`Pulumi.production.yaml`: `customDomain: www.azure.ashnova.jp` 追加 | v1.17.15             |
| Azure ログイン後に staging SNS に遷移       | Azure AD redirect URIs に `www.azure.ashnova.jp` を追加。フロントエンドを正しい `VITE_AZURE_REDIRECT_URI` で再ビルド → `index-CPcQQsCR.js`。`deploy-azure.yml` の 4箇所の `${{ secrets.AZURE_CUSTOM_DOMAIN }}` を stack 名マッピングに変更 | v1.17.16             |

## 2026-02-23 セッションで解決済みの問題

| 問題                                                                                          | 修正内容                                                                    | コミット |
| --------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------- | -------- |
| deploy-azure.yml: `run:` キー重複 (YAML error)                                                | `Build and Package Azure Function` ステップ追加                             | v1.16.2  |
| deploy-azure.yml: `$RG_NAME` 未定義 (`az functionapp config hostname list` 失敗)              | `RG_NAME=$(pulumi stack output ...)` に修正                                 | v1.17.3  |
| deploy-gcp.yml: Python heredoc が YAML block scalar を壊す                                    | Firebase domain更新を `jq` コマンドに置き換え                               | v1.17.2  |
| deploy-azure.yml: AFD route に custom domain が未リンク                                       | AFD route PATCH 後、ワークフローに "Link Custom Domain" ステップ追加        | v1.17.4  |
| deploy-azure.yml: `AzureWebJobsStorage` が存在しないSA `multicloudautodeploa148` を指していた | zip deploy前にストレージを `mcadfuncdiev0w` に修正するステップ追加          | v1.17.6  |
| deploy-landing-azure.yml: staging にハードコード（production デプロイ不可）                   | environment-aware に修正 (`main` → production SA `mcadwebdiev0w`)           | v1.17.5  |
| Azure CDN landing page: 843バイトのReact SPA が配信されていた                                 | 上記 deploy-landing-azure.yml 修正により解消 → 4412バイトの正しいコンテンツ | v1.17.5  |

---

## 🟡 Medium Priority Tasks

| #   | Task                                        | Description                                                                                                                                                                                                                                                                                                                                                |
| --- | ------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 7   | **Release unused GCP static IPs**           | Release 3 RESERVED static IPs (`ashnova-production-ip-c41311` / `multicloud-frontend-ip` / `simple-sns-frontend-ip`) to reduce cost. Details: [07_STATUS FinOps section](AI_AGENT_06_STATUS.md#finops--gcp-unused-static-ip-address-audit-2026-02-21).                                                                                                     |
| 8   | **Delete unused GCP Cloud Storage buckets** | Delete 4 Terraform-legacy buckets (`ashnova-staging-frontend` / `ashnova-staging-function-source` / `multicloud-auto-deploy-tfstate` / `multicloud-auto-deploy-tfstate-gcp`) and the FAILED Cloud Function `mcad-staging-api`. Details: [07_STATUS Cloud Storage section](AI_AGENT_06_STATUS.md#finops--gcp-unused-cloud-storage-bucket-audit-2026-02-21). |
| 9   | **Set up monitoring and alerts**            | Configure CloudWatch Alarms (AWS) / Azure Monitor (Azure) / Cloud Monitoring (GCP).                                                                                                                                                                                                                                                                        |
| 10  | **Security hardening**                      | Change CORS `allowedOrigins` to actual domain names. Update the `example.com` placeholder in GCP SSL certificate config. Strengthen Azure Key Vault network ACLs.                                                                                                                                                                                          |
| 11  | **Aggregate WAF logs**                      | Centralize WAF logs from all 3 clouds for a unified view.                                                                                                                                                                                                                                                                                                  |
| 12  | **Fully automate Lambda Layer CI/CD**       | Eliminate non-fatal warnings during layer build and publish steps.                                                                                                                                                                                                                                                                                         |
| 13  | **Update README**                           | Reflect current endpoints, auth behavior, and CI/CD status in the README.                                                                                                                                                                                                                                                                                  |
| 14  | **Branch protection rules**                 | Prevent direct pushes to `main`. Require PR + CI pass.                                                                                                                                                                                                                                                                                                     |

---

## 🟢 Low Priority Tasks

| #   | Task                            | Description                                                                                   |
| --- | ------------------------------- | --------------------------------------------------------------------------------------------- |
| 15  | **~~Custom domain setup~~** ✅  | Complete for all 3 clouds (2026-02-21). See [CUSTOM_DOMAIN_SETUP.md](CUSTOM_DOMAIN_SETUP.md). |
| 16  | **Load testing**                | Establish a performance baseline with Locust or similar.                                      |
| 17  | **CI/CD failure notifications** | Add Slack / Discord webhook integration.                                                      |
| 18  | **Expand test coverage**        | Currently minimal. Add E2E + auth tests.                                                      |
| 19  | **Chaos engineering**           | Simulate network outages, DB failures, and cold-start spikes.                                 |

---

## Recommended Work Order

```
1 → Run integration tests (establish current baseline)
2 → Verify Azure PUT /posts
3 → Confirm DynamoDB GSI
4 → Fix SNS:Unsubscribe (restore DELETE flow)
5 → GCP HTTPS (production quality)
6 → Azure WAF (production quality)
7 → Release unused GCP static IPs (cost reduction, can be done immediately)
8 → Delete unused GCP Cloud Storage buckets (cost reduction, can be done immediately)
9 → Monitoring & alerts
10 → Security hardening
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
