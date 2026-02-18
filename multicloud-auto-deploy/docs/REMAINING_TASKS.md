# Remaining Tasks

> **Last Updated**: 2026-02-18
> **AI Agent Note**: Authoritative backlog of work items that remain incomplete. Update this document when tasks are resolved or new issues are discovered.

---

## Status Summary

```
Infrastructure (Pulumi):   COMPLETE ✅  (staging + production deployed on all 3 clouds)
AWS API:                   ✅ Operational
GCP API (staging):         ✅ CRUD working
GCP API (production):      ✅ CRUD working (python312, GCP_POSTS_COLLECTION fixed)
Azure API:                 ✅ Operational (POST 201 / GET 200 confirmed)
GCP Backend code:          ✅ Implemented (Firestore CRUD complete)
Azure Backend code:        ✅ Implemented (Cosmos DB CRUD complete)
All CI/CD pipelines:       ✅ Green (AWS eaf8071c / GCP 05829e60 / Azure 0912ac37)
Azure WAF:                 ❌ Not enabled
Integration tests:         ⚠️  Not run end-to-end (blockers now cleared)
```

---

## 🟠 High Priority

| #  | Task                                         | Detail                                                                                                                                                       | Reference |
| -- | -------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------ | --------- |
| 1  | **Run integration tests (≥ 80% pass rate)**  | All backend blockers are now resolved. Run the full suite across AWS / GCP / Azure and confirm ≥ 80% success rate.                                           | [INTEGRATION_TESTS_GUIDE.md](INTEGRATION_TESTS_GUIDE.md) |
| 2  | **Verify Azure `PUT /posts` endpoint**       | Azure routing for PUT has not been confirmed end-to-end. Test and fix if needed.                                                                             | — |
| 3  | **Confirm DynamoDB `PostIdIndex` GSI**       | Left as "unconfirmed" in the AWS backend fix report. Verify the GSI exists and filter-query behavior is correct.                                             | [AWS_BACKEND_COMPLETE_FIX_REPORT.md](AWS_BACKEND_COMPLETE_FIX_REPORT.md) |
| 4  | **Resolve SNS:Unsubscribe permission issue** | `DELETE /posts` triggers an SNS unsubscribe call that fails due to missing IAM permission. Either add `sns:Unsubscribe` to the Lambda role or redesign flow. | [ENVIRONMENT_STATUS.md](ENVIRONMENT_STATUS.md) |
| 5  | **Enable GCP HTTPS**                         | GCP frontend is HTTP-only (IP-based). Needs `TargetHttpsProxy` + Managed SSL certificate.                                                                    | [ARCHITECTURE.md](ARCHITECTURE.md) |
| 6  | **Enable Azure WAF**                         | Azure Front Door is Standard tier with no WAF policy attached.                                                                                               | [ARCHITECTURE.md](ARCHITECTURE.md) |

---

## 🟡 Medium Priority

| #  | Task                                        | Detail |
| -- | ------------------------------------------- | ------ |
| 7  | **Monitoring & alerting setup**             | CloudWatch Alarms (AWS), Azure Monitor Front Door WAF alerts, GCP Cloud Monitoring — none fully configured. |
| 8  | **Security hardening**                      | Update CORS `allowedOrigins` to real domain names; replace `example.com` placeholder in GCP SSL cert config; tighten Azure Key Vault network ACLs. |
| 9  | **Centralize WAF logs**                     | Aggregate WAF logs from all three clouds into a single location for unified visibility. |
| 10 | **Complete Lambda Layer CI/CD integration** | A non-fatal warning is still emitted during layer publish. Make layer build + publish fully automated with no warnings. |
| 11 | **Final README update**                     | Reflect all recent changes (endpoints, auth behavior, CI/CD pipeline status) in the top-level README and `multicloud-auto-deploy/README.md`. |
| 12 | **Branch protection rules**                 | Prevent direct pushes to `main`; require PR + passing CI before merge. |

---

## 🟢 Low Priority

| #  | Task                             | Detail |
| -- | -------------------------------- | ------ |
| 13 | **Custom domain setup**          | Configure custom subdomains (`aws.yourdomain.com`, `azure.yourdomain.com`, `gcp.yourdomain.com`) for all three clouds. See [CUSTOM_DOMAIN_SETUP.md](CUSTOM_DOMAIN_SETUP.md). |
| 14 | **Load / performance testing**   | Run load tests with Locust or a similar tool. No performance baseline has been established. |
| 15 | **CI/CD failure notifications**  | Add Slack or Discord webhook notifications for workflow failures. |
| 16 | **Increase CI/CD test coverage** | Current automated test suite is minimal. Add E2E tests and auth/authz coverage. |
| 17 | **Chaos engineering tests**      | Simulate failures (network loss, DB unavailable, cold-start spikes) to verify resilience. |

---

## Recommended Order of Attack

1. **#1** — Run integration tests (all blockers cleared; validate the current state now)
2. **#2** — Verify Azure PUT /posts (quick smoke test)
3. **#3** — Confirm DynamoDB GSI (needed before load testing)
4. **#4** — Fix SNS:Unsubscribe permission (DELETE flow is broken)
5. **#5** — Enable GCP HTTPS (security & production readiness)
6. **#6** — Enable Azure WAF (security & production readiness)
7. **#7** — Monitoring & alerting
8. **#8** — Security hardening (CORS, SSL cert placeholder, Key Vault ACLs)
9. **#9–#12** — Ops polish (WAF logs, Lambda Layer, README, branch protection)
10. **#13–#17** — Low priority: custom domains, load tests, notifications, coverage, chaos

---

## ✅ Resolved (History)

| Task                                       | Resolution                                                                                              | Commit       |
| ------------------------------------------ | ------------------------------------------------------------------------------------------------------- | ------------ |
| Fix Azure `/posts` 404                     | Azure Function routing was correct; stale test report. POST 201 / GET 200 confirmed.                   | —            |
| Fix AWS Staging POST 401                   | `AUTH_DISABLED=true` added for staging in `deploy-aws.yml`.                                            | a2b8bb8      |
| Fix GCP Production GET /posts 500          | python312, `GCP_POSTS_COLLECTION=posts`, SecretVersion removed, `functions-framework==3.10.1`          | 05829e60     |
| Fix deploy-gcp.yml ConcurrentUpdateError   | `concurrency` group added to all 3 workflows.                                                           | a2b8bb8      |
| Implement GCP Backend                      | Firestore CRUD fully implemented.                                                                       | (backend PR) |
| Implement Azure Backend                    | Cosmos DB CRUD fully implemented.                                                                       | (backend PR) |
| Fix AWS CI/CD Lambda Layer condition       | Removed duplicate/conditional step; now single unconditional build.                                     | eaf8071c     |
| Fix Azure hardcoded staging resource group | Replaced hardcoded `multicloud-auto-deploy-staging-rg` with dynamic Pulumi output in 3 workflow steps. | 0912ac3      |

---

## Related Documents

| Document | Contents |
| -------- | -------- |
| [ENVIRONMENT_STATUS.md](ENVIRONMENT_STATUS.md) | Per-environment live status and known error details |
| [BACKEND_IMPLEMENTATION_INVESTIGATION.md](BACKEND_IMPLEMENTATION_INVESTIGATION.md) | Root-cause analysis of GCP/Azure `NotImplementedError` |
| [BACKEND_FIX_IMPLEMENTATION_REPORT.md](BACKEND_FIX_IMPLEMENTATION_REPORT.md) | AWS backend fix implementation details |
| [AWS_BACKEND_COMPLETE_FIX_REPORT.md](AWS_BACKEND_COMPLETE_FIX_REPORT.md) | AWS fix completion report (includes next steps for GCP/Azure) |
| [DEPLOY_PIPELINE_REPORT_20260218_150240.md](DEPLOY_PIPELINE_REPORT_20260218_150240.md) | Latest full pipeline run results (2026-02-18) |
| [CICD_SETUP.md](CICD_SETUP.md) | GitHub Actions workflow configuration details |
| [ARCHITECTURE.md](ARCHITECTURE.md) | Infrastructure roadmap (Completed / Planned sections) |
