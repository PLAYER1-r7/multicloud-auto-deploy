# Remaining Tasks

> **Last Updated**: 2026-02-18
> **AI Agent Note**: Authoritative backlog of work items that remain incomplete. Update this document when tasks are resolved or new issues are discovered.

---

## Status Summary

```
Infrastructure (Pulumi):   COMPLETE ✅  (staging + production deployed on all 3 clouds)
AWS API:                   ✅ Operational (AUTH_DISABLED=true added to staging CI/CD — deployed)
GCP API (staging):         ✅ CRUD working
GCP API (production):      ✅ DEPLOYED — New container image with correct env vars (2026-02-18)
Azure API:                 ✅ POST /posts → 201, GET /posts → 200 (working as of 2026-02-18)
GCP Backend code:          ✅ Implemented (Firestore CRUD complete)
Azure Backend code:        ✅ Implemented (Cosmos DB CRUD complete)
GCP CI/CD:                 ✅ Fixed: concurrency group + SecretVersion IAM workaround
Azure CI/CD:               ✅ Fixed: dynamic stack/resource group/function app name
AWS CI/CD:                 ✅ Fixed: AUTH_DISABLED + Lambda Layer build + concurrency
Azure WAF:                 ❌ Not enabled
```

---

## 🔴 Critical

| #   | Task                                   | Detail                                                                                                                                                                                                                      | Status                                                                                                                                         | Reference                                                           |
| --- | -------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------- |
| 1   | **Fix Azure `/posts` 404**             | ~~`POST /posts` and `GET /posts` both return 404 on Azure.~~                                                                                                                                                                | ✅ **RESOLVED** — POST returns 201, GET returns 200 as of 2026-02-18. Azure Function routing was already correct via `/api/HttpTrigger/posts`. | [DEPLOY_PIPELINE_REPORT](DEPLOY_PIPELINE_REPORT_20260218_150240.md) |
| 2   | **Fix AWS Staging POST 401**           | `POST /posts` was returning 401 because `AUTH_DISABLED=false`.                                                                                                                                                              | ✅ **RESOLVED** — `AUTH_DISABLED=true` added for staging in `deploy-aws.yml`. Redeploy triggered.                                              | [commit a2b8bb8]                                                    |
| 3   | **Fix GCP Production GET /posts 500**  | Production GCP returns 500 on `GET /posts`. Root cause: old container image with unimplemented GcpBackend (`NotImplementedError`). Also, env var `FIRESTORE_COLLECTION` was wrong — should be `GCP_POSTS_COLLECTION=posts`. | ✅ **RESOLVED** — CI/CD `[completed/success]` on commit `05829e60`. python312 runtime, `GCP_POSTS_COLLECTION=posts`, `SecretVersion` removed from Pulumi, `functions-framework==3.10.1`. | [commit 05829e60]                                                    |
| 4   | **Fix `deploy-gcp.yml` CI/CD failure** | `deploy-gcp.yml` was failing with Pulumi `ConcurrentUpdateError` (409 Conflict) when `workflow_dispatch` fired during an active push-triggered run.                                                                         | ✅ **RESOLVED** — `concurrency` group added to serialize Pulumi stack updates.                                                                 | [commit a2b8bb8]                                                    |

---

## 🟠 High Priority

| #   | Task                                           | Detail                                                                                                                                                                                                                                       | Reference                                                                 |
| --- | ---------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------- |
| 5   | **~~Implement GCP Backend~~** ✅ DONE          | ~~All methods in `GcpBackend` raise `NotImplementedError`~~. Firestore CRUD fully implemented: `list_posts`, `create_post`, `update_post`, `delete_post`, `get_profile`, `update_profile`, `generate_upload_urls`. CI/CD `[completed/success]` confirmed. | [BACKEND_FIX_IMPLEMENTATION_REPORT](BACKEND_FIX_IMPLEMENTATION_REPORT.md) |
| 6   | **~~Implement Azure Backend~~** ✅ DONE        | ~~Same situation as GCP~~. Cosmos DB CRUD fully implemented. CI/CD `[completed/success]` confirmed. POST /posts → 201, GET /posts → 200.                                                                                                     | Same                                                                      |
| 7   | **Enable GCP HTTPS**                           | GCP frontend is currently HTTP-only (IP-based access). Needs `TargetHttpsProxy` + Managed SSL certificate. Listed as Planned in ARCHITECTURE.md.                                                                                             | [ARCHITECTURE.md](ARCHITECTURE.md)                                        |
| 8   | **~~Fix AWS CI/CD Lambda Layer build condition~~** ✅ DONE | ~~Lambda Layer build step was gated by `use_klayers` condition, skipped on `push` triggers~~. Removed duplicate/conditional step — now single unconditional build. CI/CD `[completed/success]` confirmed. | [commit eaf8071c]                            |
| 9   | **Enable Azure WAF**                           | Azure Front Door is currently Standard tier with no WAF enabled.                                                                                                                                                                             | [ARCHITECTURE.md](ARCHITECTURE.md)                                        |

---

## 🟡 Medium Priority

| #   | Task                                         | Detail                                                                                                                                                    |
| --- | -------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 10  | **Integration test coverage**                | Target ≥ 80% success rate across all three providers. Current blockers: AWS POST 401, Azure 404, GCP production 500.                                      |
| 11  | **Verify Azure `PUT /posts` endpoint**       | Azure routing needs to be confirmed for the PUT method.                                                                                                   |
| 12  | **Confirm DynamoDB `PostIdIndex` GSI**       | Left as "unconfirmed" in the AWS backend fix report. Verify the GSI exists and is correctly configured.                                                   |
| 13  | **Resolve SNS:Unsubscribe permission issue** | Either redesign to avoid delete operations that trigger SNS unsubscribe, or add the required IAM permission.                                              |
| 14  | **Monitoring & alerting setup**              | CloudWatch Alarms (AWS), Azure Monitor Front Door WAF alerts, GCP Cloud Monitoring — none fully configured.                                               |
| 15  | **Security hardening**                       | Update CORS `allowedOrigins` to real domain names; replace placeholder `example.com` in GCP SSL certificate config; tighten Azure Key Vault network ACLs. |
| 16  | **Centralize WAF logs**                      | Aggregate WAF logs from all three clouds into a single location.                                                                                          |
| 17  | **Complete Lambda Layer CI/CD integration**  | Currently a warning is emitted but deployment still succeeds. The layer build and publish should be fully automated with no warnings.                     |

---

## 🟢 Low Priority

| #   | Task                             | Detail                                                                                                                                                                             |
| --- | -------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 18  | **Custom domain setup**          | Configure custom subdomains (e.g., `aws.yourdomain.com`, `azure.yourdomain.com`, `gcp.yourdomain.com`) for all three clouds. See [CUSTOM_DOMAIN_SETUP.md](CUSTOM_DOMAIN_SETUP.md). |
| 19  | **Final README update**          | Reflect all recent changes (new endpoints, auth behavior, pipeline status) in the top-level README.                                                                                |
| 20  | **Load / performance testing**   | Run load tests with Locust or a similar tool. No performance baseline exists yet.                                                                                                  |
| 21  | **Branch protection rules**      | Prevent direct pushes to `main`; require PR + passing CI.                                                                                                                          |
| 22  | **CI/CD failure notifications**  | Add Slack or Discord webhook notifications for workflow failures.                                                                                                                  |
| 23  | **Chaos engineering tests**      | Simulate failures (network loss, DB unavailable, cold-start spikes) to verify resilience.                                                                                          |
| 24  | **Increase CI/CD test coverage** | Current automated test suite is minimal; add E2E and auth/authz tests.                                                                                                             |

---

## Recommended Order of Attack

The following sequence unblocks the most downstream work in the fewest steps:

1. **#8** — Fix the Lambda Layer CI/CD condition (5 min, unblocks reliable AWS deploys)
2. **#5** — Implement GCP Backend (unblocks GCP CRUD end-to-end)
3. **#3** — Debug GCP production 500 (may be resolved by #5 re-deploy)
4. **#6** — Implement Azure Backend
5. **#1** — Fix Azure 404 (likely resolved by #6 + Functions routing fix)
6. **#4** — Fix `deploy-gcp.yml` CI/CD failure (unblocks automated GCP deploys)
7. **#7** — Enable GCP HTTPS
8. **#2** — Decide staging auth policy (disable for staging or add test credentials flow)
9. **#9** — Enable Azure WAF
10. Items #10–24 in order of business priority

---

## Related Documents

| Document                                                                               | Contents                                                      |
| -------------------------------------------------------------------------------------- | ------------------------------------------------------------- |
| [ENVIRONMENT_STATUS.md](ENVIRONMENT_STATUS.md)                                         | Per-environment live status and known error details           |
| [BACKEND_IMPLEMENTATION_INVESTIGATION.md](BACKEND_IMPLEMENTATION_INVESTIGATION.md)     | Root-cause analysis of GCP/Azure `NotImplementedError`        |
| [BACKEND_FIX_IMPLEMENTATION_REPORT.md](BACKEND_FIX_IMPLEMENTATION_REPORT.md)           | AWS backend fix implementation details                        |
| [AWS_BACKEND_COMPLETE_FIX_REPORT.md](AWS_BACKEND_COMPLETE_FIX_REPORT.md)               | AWS fix completion report (includes next steps for GCP/Azure) |
| [DEPLOY_PIPELINE_REPORT_20260218_150240.md](DEPLOY_PIPELINE_REPORT_20260218_150240.md) | Latest full pipeline run results (2026-02-18)                 |
| [CICD_SETUP.md](CICD_SETUP.md)                                                         | GitHub Actions workflow configuration details                 |
| [ARCHITECTURE.md](ARCHITECTURE.md)                                                     | Infrastructure roadmap (Completed / Planned sections)         |
