# AI Agent Guide — multicloud-auto-deploy

> **Purpose**: This document is the single entry point for AI agents working on this repository.
> It supersedes the fragmented per-topic docs by providing machine-readable, structured knowledge.
> Human-readable originals are preserved in their original locations and under `docs/archive/`.

---

## Document Map

| Section                              | File                                                                     | Status |
| ------------------------------------ | ------------------------------------------------------------------------ | ------ |
| **00 — Critical Rules (read first)** | [AI_AGENT_00_CRITICAL_RULES.md](AI_AGENT_00_CRITICAL_RULES.md)           | ✅     |
| 01 — Project Overview                | [AI_AGENT_01_OVERVIEW.md](AI_AGENT_01_OVERVIEW.md)                       | ✅     |
| 02 — Repository Layout               | [AI_AGENT_02_LAYOUT.md](AI_AGENT_02_LAYOUT.md)                           | ✅     |
| 03 — Architecture                    | [AI_AGENT_03_ARCHITECTURE.md](AI_AGENT_03_ARCHITECTURE.md)               | ✅     |
| 04 — API & Data Model                | [AI_AGENT_04_API.md](AI_AGENT_04_API.md)                                 | ✅     |
| 05 — Infrastructure (Pulumi)         | [AI_AGENT_05_INFRA.md](AI_AGENT_05_INFRA.md)                             | ✅     |
| 06 — CI/CD Pipelines                 | [AI_AGENT_06_CICD.md](AI_AGENT_06_CICD.md)                               | ✅     |
| 07 — Environment Status              | [AI_AGENT_07_STATUS.md](AI_AGENT_07_STATUS.md)                           | ✅     |
| 08 — Runbooks                        | [AI_AGENT_08_RUNBOOKS.md](AI_AGENT_08_RUNBOOKS.md)                       | ✅     |
| 09 — Security                        | [AI_AGENT_09_SECURITY.md](AI_AGENT_09_SECURITY.md)                       | ✅     |
| 10 — Remaining Tasks                 | [AI_AGENT_10_TASKS.md](AI_AGENT_10_TASKS.md)                             | ✅     |
| 11 — Workspace Migration [archive]   | [AI_AGENT_11_WORKSPACE_MIGRATION.md](AI_AGENT_11_WORKSPACE_MIGRATION.md) | 📁     |

### Fix Reports

| Report                                | File                                                                 | Summary                                                                                              |
| ------------------------------------- | -------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------- |
| AWS Simple-SNS Fix (2026-02-20)       | [AWS_SNS_FIX_REPORT.md](AWS_SNS_FIX_REPORT.md)                       | Fixed Lambda env vars / CI/CD race condition / logout 404                                            |
| AWS Production SNS Fix (2026-02-21)   | [AWS_PRODUCTION_SNS_FIX_REPORT.md](AWS_PRODUCTION_SNS_FIX_REPORT.md) | Fixed `localhost:8000` fallback — empty API_BASE_URL caused by unset GitHub Secret in prod           |
| Azure Simple-SNS Fix (2026-02-21)     | [AZURE_SNS_FIX_REPORT.md](AZURE_SNS_FIX_REPORT.md)                   | Investigation and fix for intermittent AFD /sns/\* 502 errors                                        |
| AWS Production HTTPS Fix (2026-02-21) | [AWS_HTTPS_FIX_REPORT.md](AWS_HTTPS_FIX_REPORT.md)                   | Fixed ERR_CERT_COMMON_NAME_INVALID caused by missing CloudFront alias / ACM certificate              |
| AWS Simple-SNS Fix (2026-02-22)       | [AWS_SNS_FIX_REPORT_20260222.md](AWS_SNS_FIX_REPORT_20260222.md)     | Fixed 12 bugs: auth/JWT, profile, images, nickname, presigned URLs, MIME, VITE_BASE_PATH             |
| GCP Simple-SNS Fix (2026-02-23)       | [GCP_SNS_FIX_REPORT_20260223.md](GCP_SNS_FIX_REPORT_20260223.md)     | Fixed 6 bugs: CORS origins, Firebase domain, /limits 404, COOP header, signed URLs, IndentationError |

---

## Recommended Reading Order

If this is your first session in this repository, read in this order:

```
1. AI_AGENT_00_CRITICAL_RULES.md  ← mandatory: rules that prevent outages and wasted time
2. AI_AGENT_01_OVERVIEW.md        ← what the project is, live endpoints, tech stack
3. AI_AGENT_02_LAYOUT.md          ← directory tree, file purposes
4. AI_AGENT_03_ARCHITECTURE.md    ← system topology, storage paths
5. AI_AGENT_07_STATUS.md          ← current health of all 3 cloud environments
6. AI_AGENT_10_TASKS.md           ← what to work on next (prioritised backlog)
```

Read these on demand:

```
AI_AGENT_04_API.md      ← endpoint spec, request/response schema, data model
AI_AGENT_05_INFRA.md    ← Pulumi stacks, resource names, config keys, outputs
AI_AGENT_06_CICD.md     ← GitHub Actions workflows, secrets, branch→env mapping
AI_AGENT_08_RUNBOOKS.md ← step-by-step procedures: deploy, rollback, check logs
AI_AGENT_09_SECURITY.md ← auth config per cloud, current security gaps
```

---

## Quick Decision Tree

```
Q: How do I set up for the first time?
  → Read 00_CRITICAL_RULES, then 01_OVERVIEW, then 02_LAYOUT

Q: I want to modify code
  → services/api/**        : see 04_API + 08_RUNBOOKS (RB-01 for Lambda, RB-07 for GCP)
  → infrastructure/**      : see 05_INFRA
  → .github/workflows/     : see 06_CICD  ⚠️ edit at /workspaces/ashnova/.github/workflows/
  → static-site/**         : see 03_ARCHITECTURE (Static Site section)
  → services/frontend_react: see 03_ARCHITECTURE + Rule 7 (VITE_BASE_PATH)

Q: I want to check whether the live environments are healthy
  → see 07_STATUS

Q: Something is broken / I need to fix an error
  → see 08_RUNBOOKS first, then the relevant Fix Report in the table above

Q: I want to deploy something manually
  → see 08_RUNBOOKS (RB-01 Lambda / RB-03 React frontend / RB-07 GCP Cloud Run)

Q: I don't know what to work on next
  → see 10_TASKS (prioritised backlog)

Q: CI/CD is failing
  → check 06_CICD for required secrets, then run deploy workflow manually with workflow_dispatch
```

---

## Rules Summary

Full details are in [AI_AGENT_00_CRITICAL_RULES.md](AI_AGENT_00_CRITICAL_RULES.md).
This table is a one-line reminder for each rule.

| Rule | Topic            | Summary                                                                                  |
| ---- | ---------------- | ---------------------------------------------------------------------------------------- |
| 0    | Language         | All docs, code, and commits must be written in English                                   |
| 1    | File operations  | Edit a few files at a time — large batches risk network timeout / silent corruption      |
| 2    | ARM vs x86       | Dev container is aarch64; always use `--platform linux/amd64` Docker for deploy builds   |
| 3    | .github location | Workflows live at `/workspaces/ashnova/.github/workflows/` — not visible here            |
| 4    | main branch      | Push to `main` = immediate production deployment                                         |
| 5    | AUTH_DISABLED    | Must always be `false` — was accidentally `true` in a past incident                      |
| 6    | Env vars source  | Lambda/Cloud Run env vars from `pulumi stack output`, never from GitHub Secrets          |
| 7    | Vite base path   | AWS frontend must be built with `VITE_BASE_PATH=/sns/`                                   |
| 8    | S3 images        | Images bucket is private — always return presigned GET URLs, never raw S3 keys           |
| 9    | CloudFront cert  | Set `customDomain` + `acmCertificateArn` in Pulumi config before `pulumi up` on prod-AWS |
| 10   | Cognito JWT      | Call `jwt_verifier.py` with `verify_at_hash=False` when only `id_token` is sent          |
| 11   | GCP main.py      | Always include `main.py` (copy of `function.py`) in the GCP deployment ZIP               |
| 12   | GCP signed URLs  | Pass `service_account_email` + `access_token` to `generate_signed_url()`                 |
| 13   | Firebase domains | Register new domains via Identity Toolkit API with `x-goog-user-project` header          |
| 14   | GCP COOP header  | CDN must send `Cross-Origin-Opener-Policy: same-origin-allow-popups`                     |

### Project Quick-Facts

```
Branch strategy : develop → staging,  main → production (immediate)
All 3 stagings  : ✅ AWS / Azure / GCP are operational (as of 2026-02-23)
Storage path    : /       → landing (static-site/)
                  /sns/   → React SNS app (services/frontend_react/dist/, built with base="/sns/")
Auth provider   : AWS=Cognito  Azure=Azure AD  GCP=Firebase Auth
```
