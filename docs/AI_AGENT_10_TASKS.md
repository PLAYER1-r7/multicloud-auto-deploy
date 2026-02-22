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
All CI/CD pipelines:        ✅ Green (2026-02-22 — deploy-frontend-*.yml 廃止・統合)
Custom Domains:             ✅ All 3 clouds live (2026-02-21)
  www.aws.ashnova.jp:       ✅ HTTPS OK
  www.gcp.ashnova.jp:       ✅ HTTPS OK
  www.azure.ashnova.jp:     ✅ HTTPS OK (⚠️ /sns/* intermittent 502 under investigation)
Production React SPA:       ✅ All 3 clouds (2026-02-21, REACT_SPA_MIGRATION_REPORT.md)
Staging React SPA:          ❌ CDN ルーティング未修正 → 旧 Python frontend-web が表示中
Azure WAF:                  ❌ Not configured
Integration tests:          ⚠️ Not yet run (blockers resolved)
```

---

## 🔴 High Priority Tasks

| #   | Task                                          | Description                                                                                                                     | Reference                                                                                                       |
| --- | --------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------- |
| 0   | **Staging CDN ルーティング修正**              | Staging の `/sns/*` が旧 Python frontend-web を向いている。`scripts/fix-staging-routing.sh` を実行して React SPA に切り替える。 | [REACT_SPA_MIGRATION_REPORT.md](REACT_SPA_MIGRATION_REPORT.md) / [AI_AGENT_07_STATUS.md](AI_AGENT_07_STATUS.md) |
| 1   | **Resolve Azure AFD intermittent 502 errors** | AFD returns 502 immediately on ~50% of `/sns/*` requests. Likely caused by stale TCP connections on Dynamic Consumption plan.   | [AZURE_SNS_FIX_REPORT.md](AZURE_SNS_FIX_REPORT.md#issue-2)                                                      |
| 2   | **Run integration tests (≥80% pass)**         | All backend blockers resolved. Run full suite on AWS/GCP/Azure and confirm.                                                     | [INTEGRATION_TESTS_GUIDE.md](INTEGRATION_TESTS_GUIDE.md)                                                        |
| 3   | **Verify Azure `PUT /posts` endpoint**        | End-to-end PUT routing on Azure has not been confirmed. Test and fix.                                                           | —                                                                                                               |
| 4   | **Confirm DynamoDB `PostIdIndex` GSI**        | GSI presence not confirmed. `GET /posts/{id}` may return 500.                                                                   | [RB-09](AI_AGENT_08_RUNBOOKS.md#rb-09-verify--create-the-dynamodb-postidindex-gsi)                              |
| 5   | **Fix `SNS:Unsubscribe` permission error**    | `DELETE /posts` fails on SNS Unsubscribe call. Add `sns:Unsubscribe` to IAM or redesign the flow.                               | —                                                                                                               |
| 6   | **GCP HTTPS**                                 | GCP frontend is HTTP only. Requires `TargetHttpsProxy` + Managed SSL certificate.                                               | [09_SECURITY](AI_AGENT_09_SECURITY.md)                                                                          |
| 7   | **Enable Azure WAF**                          | WAF policy not applied to Front Door Standard SKU.                                                                              | [09_SECURITY](AI_AGENT_09_SECURITY.md)                                                                          |

---

## 🟡 Medium Priority Tasks

| #   | Task                                        | Description                                                                                                                                                                                                                                                                                                                                                |
| --- | ------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 7   | **Release unused GCP static IPs**           | Release 3 RESERVED static IPs (`ashnova-production-ip-c41311` / `multicloud-frontend-ip` / `simple-sns-frontend-ip`) to reduce cost. Details: [07_STATUS FinOps section](AI_AGENT_07_STATUS.md#finops--gcp-unused-static-ip-address-audit-2026-02-21).                                                                                                     |
| 8   | **Delete unused GCP Cloud Storage buckets** | Delete 4 Terraform-legacy buckets (`ashnova-staging-frontend` / `ashnova-staging-function-source` / `multicloud-auto-deploy-tfstate` / `multicloud-auto-deploy-tfstate-gcp`) and the FAILED Cloud Function `mcad-staging-api`. Details: [07_STATUS Cloud Storage section](AI_AGENT_07_STATUS.md#finops--gcp-unused-cloud-storage-bucket-audit-2026-02-21). |
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
