# AI Agent Guide — multicloud-auto-deploy

> **Purpose**: Single entry point for AI agents working on this repository.  
> Start here every session. All numbered documents are cross-linked from this guide.

---

## Part I — Orientation

> Read these first. Together they give you enough context to start working.

| No. | Document | Contents |
| --- | -------- | -------- |
| 00 ★ **read first** | [AI_AGENT_00_CRITICAL_RULES.md](AI_AGENT_00_CRITICAL_RULES.md) | 14 rules distilled from past incidents |
| 01 | [AI_AGENT_01_CONTEXT.md](AI_AGENT_01_CONTEXT.md) | Project overview, live endpoints, directory tree, dev env |
| 02 | [AI_AGENT_02_ARCHITECTURE.md](AI_AGENT_02_ARCHITECTURE.md) | System topology, per-cloud architecture, storage paths |

---

## Part II — Technical Reference

> Look up when you need to understand or change a specific area.

| No. | Document | Contents |
| --- | -------- | -------- |
| 03 | [AI_AGENT_03_API.md](AI_AGENT_03_API.md) | API endpoints, request/response schema, data model |
| 04 | [AI_AGENT_04_INFRA.md](AI_AGENT_04_INFRA.md) | Pulumi stacks, resource names, config keys, outputs |
| 05 | [AI_AGENT_05_CICD.md](AI_AGENT_05_CICD.md) | GitHub Actions workflows, required secrets, trigger conditions |

---

## Part III — Operations

> Check these during ongoing work, debugging, and task planning.

| No. | Document | Contents |
| --- | -------- | -------- |
| 06 | [AI_AGENT_06_STATUS.md](AI_AGENT_06_STATUS.md) | Current health of all 3 cloud environments |
| 07 | [AI_AGENT_07_RUNBOOKS.md](AI_AGENT_07_RUNBOOKS.md) | Step-by-step: deploy, rollback, check logs |
| 08 | [AI_AGENT_08_SECURITY.md](AI_AGENT_08_SECURITY.md) | Auth config per cloud, known security gaps |
| 09 | [AI_AGENT_09_TASKS.md](AI_AGENT_09_TASKS.md) | Prioritised backlog — what to work on next |

---

## Archive

| Document | Contents |
| -------- | -------- |
| [archive/AI_AGENT_11_WORKSPACE_MIGRATION.md](archive/AI_AGENT_11_WORKSPACE_MIGRATION.md) | 2026-02-21 repository cleanup record |

---

## Fix Reports

| Report | File | Summary |
| ------ | ---- | ------- |
| AWS Simple-SNS Fix (2026-02-20)       | [AWS_SNS_FIX_REPORT.md](AWS_SNS_FIX_REPORT.md)                       | Fixed Lambda env vars / CI/CD race condition / logout 404 |
| AWS Production SNS Fix (2026-02-21)   | [AWS_PRODUCTION_SNS_FIX_REPORT.md](AWS_PRODUCTION_SNS_FIX_REPORT.md) | Fixed `localhost:8000` fallback — empty `API_BASE_URL` caused by unset GitHub Secret in prod |
| Azure Simple-SNS Fix (2026-02-21)     | [AZURE_SNS_FIX_REPORT.md](AZURE_SNS_FIX_REPORT.md)                   | Investigation and fix for intermittent AFD `/sns/*` 502 errors |
| AWS Production HTTPS Fix (2026-02-21) | [AWS_HTTPS_FIX_REPORT.md](AWS_HTTPS_FIX_REPORT.md)                   | Fixed `ERR_CERT_COMMON_NAME_INVALID` caused by missing CloudFront alias / ACM certificate |
| AWS Simple-SNS Fix (2026-02-22)       | [AWS_SNS_FIX_REPORT_20260222.md](AWS_SNS_FIX_REPORT_20260222.md)     | Fixed 12 bugs: auth/JWT, profile, images, nickname, presigned URLs, MIME, VITE_BASE_PATH |
| GCP Simple-SNS Fix (2026-02-23)       | [GCP_SNS_FIX_REPORT_20260223.md](GCP_SNS_FIX_REPORT_20260223.md)     | Fixed 6 bugs: CORS origins, Firebase domain, /limits 404, COOP header, signed URLs, IndentationError |

---

## Recommended Reading Order

First session in this repo:

```
1. AI_AGENT_00_CRITICAL_RULES.md  ← mandatory: rules that prevent outages and wasted time
2. AI_AGENT_01_CONTEXT.md         ← what the project is, live endpoints, tech stack, directory tree
3. AI_AGENT_02_ARCHITECTURE.md    ← system topology, storage paths
4. AI_AGENT_06_STATUS.md          ← current health of all 3 cloud environments
5. AI_AGENT_09_TASKS.md           ← what to work on next (prioritised backlog)
```

On demand:

```
AI_AGENT_03_API.md      ← endpoint spec, request/response schema, data model
AI_AGENT_04_INFRA.md    ← Pulumi stacks, resource names, config keys, outputs
AI_AGENT_05_CICD.md     ← GitHub Actions workflows, secrets, branch→env mapping
AI_AGENT_07_RUNBOOKS.md ← step-by-step procedures: deploy, rollback, check logs
AI_AGENT_08_SECURITY.md ← auth config per cloud, current security gaps
```

---

## Quick Decision Tree

```
Q: First time in this repo?
  → 00_CRITICAL_RULES → 01_CONTEXT → 02_ARCHITECTURE → 06_STATUS → 09_TASKS

Q: Modify backend API code
  → services/api/app/routes/*.py or backends/*.py  (see 03_API for schema)
  → deploy: see 07_RUNBOOKS (RB-01 Lambda, RB-05 Azure Functions, RB-06 GCP Cloud Run)

Q: Change infrastructure (Pulumi)
  → infrastructure/pulumi/{aws,azure,gcp}/__main__.py  (see 04_INFRA)

Q: Edit a CI/CD workflow
  → .github/workflows/*.yml  (workspace root)  see 05_CICD for secrets/trigger conditions

Q: Modify React frontend (AWS)
  → services/frontend_react/src/  build with VITE_BASE_PATH=/sns/  (Rule 6)
  → deploy: 07_RUNBOOKS RB-03

Q: Check if environments are healthy
  → 06_STATUS

Q: Something is broken
  → 07_RUNBOOKS first, then relevant Fix Report above

Q: What should I work on next?
  → 09_TASKS
```

---

## Rules Summary

Full details: [AI_AGENT_00_CRITICAL_RULES.md](AI_AGENT_00_CRITICAL_RULES.md)

| Rule | Topic | One-line summary |
| ---- | ----- | ---------------- |
| 0  | Language        | All docs, code, and commits must be written in English |
| 1  | File operations | Edit a few files at a time — large batches risk network timeout / silent corruption |
| 2  | ARM vs x86      | Dev container is aarch64; always use `--platform linux/amd64` Docker for deploy builds |
| 3  | main branch     | Push to `main` = immediate production deployment |
| 4  | AUTH_DISABLED   | Must always be `false` — was accidentally `true` in a past incident |
| 5  | Env vars source | Lambda/Cloud Run env vars from `pulumi stack output`, never from GitHub Secrets |
| 6  | Vite base path  | AWS frontend must be built with `VITE_BASE_PATH=/sns/` |
| 7  | S3 images       | Images bucket is private — always return presigned GET URLs, never raw S3 keys |
| 8  | CloudFront cert | Set `customDomain` + `acmCertificateArn` in Pulumi config before `pulumi up` on prod-AWS |
| 9  | Cognito JWT     | Call `jwt_verifier.py` with `verify_at_hash=False` when only `id_token` is sent |
| 10 | GCP main.py     | Always include `main.py` (copy of `function.py`) in the GCP deployment ZIP |
| 11 | GCP signed URLs | Pass `service_account_email` + `access_token` to `generate_signed_url()` |
| 12 | Firebase domains| Register new domains via Identity Toolkit API with `x-goog-user-project` header |
| 13 | GCP COOP header | CDN must send `Cross-Origin-Opener-Policy: same-origin-allow-popups` |

---

## Project Quick-Facts

```
Branch strategy   : develop → staging,  main → production (push = immediate deploy)
All 3 stagings    : ✅ AWS / Azure / GCP operational (as of 2026-02-23)
Storage paths     : /      → landing page (static-site/)
                   /sns/   → React SNS app (built with VITE_BASE_PATH=/sns/)
Auth providers    : AWS = Cognito | Azure = Azure AD | GCP = Firebase Auth
Dev container     : linux/aarch64 (ARM)  →  cloud runtime: linux/amd64
```

<!-- gate check -->
