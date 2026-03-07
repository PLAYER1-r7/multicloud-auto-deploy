# AI Agent Guide — multicloud-auto-deploy

> # 🤖 AI AGENTS: START HERE
> 
> **Purpose**: Single entry point for AI agents working on this repository.
> 
> ### ⚠️ BEFORE YOU DO ANYTHING ELSE ⚠️
> 
> 1. **READ FIRST**: [AI_AGENT_00_CRITICAL_RULES.md](AI_AGENT_00_CRITICAL_RULES.md) ⭐ **MANDATORY** ⭐
>    - 18 critical rules learned from past production incidents
>    - Prevents data loss, production outages, and hours of debugging
>    - **DO NOT skip this document**
> 
> 2. **Then come back here** for navigation to all other documents
> 
> ### 📖 Reading Order
> 
> After reading the critical rules above, follow this sequence:
> 
> ```
> Part I  (Orientation)    → Read first to understand the project
> Part II (Technical Ref)  → Look up when working on specific areas
> Part III (Operations)    → Check during ongoing work
> ```
> 
> **Total time for Part I: ~15 minutes | Saves you: hours of confusion**

---

## Part I — Orientation

> Read these first. Together they give you enough context to start working.

| No.                 | Document                                                       | Contents                                                  |
| ------------------- | -------------------------------------------------------------- | --------------------------------------------------------- |
| 00 ★ **read first** | [AI_AGENT_00_CRITICAL_RULES.md](AI_AGENT_00_CRITICAL_RULES.md) | 14 rules distilled from past incidents                    |
| 01                  | [AI_AGENT_01_CONTEXT.md](AI_AGENT_01_CONTEXT.md)               | Project overview, live endpoints, directory tree, dev env |
| 02                  | [AI_AGENT_02_ARCHITECTURE.md](AI_AGENT_02_ARCHITECTURE.md)     | System topology, per-cloud architecture, storage paths    |

### Mandatory Working Policy (AI Agents)

- Implement root-cause fixes by default; do not stop at symptomatic workarounds when a permanent fix is feasible.
- Keep backend/runtime compatibility aligned with Python 3.13 (project target), not legacy 3.11.
- Use the most appropriate official CLI, project script, or existing workflow before manual detours.
- If authentication is required (`gh` or any other CLI/service), request user authentication immediately with explicit commands and resume after completion; if authentication fails, do not switch to fallback alternatives unless the user explicitly asks.
- If a temporary mitigation is unavoidable, record expiry, scope, blocker, and the exact permanent follow-up task.

---

## Part II — Technical Reference

> Look up when you need to understand or change a specific area.

| No. | Document                                     | Contents                                                       |
| --- | -------------------------------------------- | -------------------------------------------------------------- |
| 03  | [AI_AGENT_03_API.md](AI_AGENT_03_API.md)     | API endpoints, request/response schema, data model             |
| 04  | [AI_AGENT_04_INFRA.md](AI_AGENT_04_INFRA.md) | Pulumi stacks, resource names, config keys, outputs            |
| 05  | [AI_AGENT_05_CICD.md](AI_AGENT_05_CICD.md)   | GitHub Actions workflows, required secrets, trigger conditions |

---

## Part III — Operations

> Check these during ongoing work, debugging, and task planning.

| No. | Document                                                         | Contents                                                                     |
| --- | ---------------------------------------------------------------- | ---------------------------------------------------------------------------- |
| 06  | [AI_AGENT_06_STATUS.md](AI_AGENT_06_STATUS.md)                   | Current health of all 3 cloud environments                                   |
| 07  | [AI_AGENT_07_RUNBOOKS.md](AI_AGENT_07_RUNBOOKS.md)               | Step-by-step: deploy, rollback, check logs                                   |
| 08  | [AI_AGENT_08_SECURITY.md](AI_AGENT_08_SECURITY.md)               | Auth config per cloud, known security gaps                                   |
| 09  | [AI_AGENT_09_GITHUB_INTEGRATION.md](AI_AGENT_09_GITHUB_INTEGRATION_JA.md) | GitHub Issues/PRs workflow, branch protection, AI Agent operations           |
| 10  | [AI_AGENT_10_TASKS.md](AI_AGENT_10_TASKS.md)                     | AI-driven backlog strategy, cadence, tools, generated PM dashboard           |
| 11  | [AI_AGENT_11_DOMAINS.md](AI_AGENT_11_DOMAINS.md)                 | Custom domain setup, DNS records, SSL certs                                  |
| 12  | [AI_AGENT_12_BUG_FIX_REPORTS.md](AI_AGENT_12_BUG_FIX_REPORTS.md) | Consolidated bug & fix reports (all clouds, 2026-02-20 →)                    |
| 13  | [AI_AGENT_13_OCR_MATH.md](AI_AGENT_13_OCR_MATH.md)               | `/v1/solve` OCR+math solving service — Azure DI, GCP Vision, Gemini, scoring |
| 14  | [AI_AGENT_14_TESTING.md](AI_AGENT_14_TESTING.md)                 | Test scripts, pytest suite, auth token acquisition, CI/CD integration        |
| 15  | [AI_AGENT_15_WORKSPACE_CLEANUP.md](AI_AGENT_15_WORKSPACE_CLEANUP.md) | Build artifacts, cache, temporary files cleanup procedures                   |

---

## Archive

| Document                                                                                 | Contents                             |
| ---------------------------------------------------------------------------------------- | ------------------------------------ |
| [archive/AI_AGENT_11_WORKSPACE_MIGRATION.md](archive/AI_AGENT_11_WORKSPACE_MIGRATION.md) | 2026-02-21 repository cleanup record |
| [archive/legacy-services/README.md](archive/legacy-services/README.md) | Deprecated services backup (frontend_web, frontend_reflex, etc.) |

## Consolidated Guide

| Document                           | Contents                                                   |
| ---------------------------------- | ---------------------------------------------------------- |
| [AI_AGENT_ALL.md](AI_AGENT_ALL.md) | Unified English entry point and mandatory execution policy |

---

## Fix Reports

> All bug and fix reports are consolidated in **[AI_AGENT_11_BUG_FIX_REPORTS.md](AI_AGENT_11_BUG_FIX_REPORTS.md)**.

| #   | Date       | Summary                                                                                                                                                                          |
| --- | ---------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| §1  | 2026-02-20 | [AWS SNS Fix](AI_AGENT_12_BUG_FIX_REPORTS.md#1-aws-sns-fix-report-2026-02-20) — Lambda env vars, CI/CD race condition, logout 404, image upload 502                              |
| §2  | 2026-02-21 | [AWS HTTPS Fix](AI_AGENT_12_BUG_FIX_REPORTS.md#2-aws-production-https-fix-2026-02-21) — `ERR_CERT_COMMON_NAME_INVALID` (missing CloudFront alias + ACM cert)                     |
| §3  | 2026-02-21 | [AWS Production SNS Fix](AI_AGENT_12_BUG_FIX_REPORTS.md#3-aws-production-sns-fix-2026-02-21) — empty `API_BASE_URL` from unset GitHub Secret; Cognito redirect URI wrong domain  |
| §4  | 2026-02-21 | [React SPA & CDN Fix](AI_AGENT_12_BUG_FIX_REPORTS.md#4-react-spa-migration--cdn-routing-fix-2026-02-21) — all 3 CDNs still routing `/sns*` to old SSR origin after SPA migration |
| §5  | 2026-02-21 | [Azure SNS Fix](AI_AGENT_12_BUG_FIX_REPORTS.md#5-azure-sns-fix-2026-02-21) — 503/404 initial setup + AFD 502 stale TCP (Dynamic Y1 → FlexConsumption)                            |
| §6  | 2026-02-22 | [AWS SNS 12-bug Fix](AI_AGENT_12_BUG_FIX_REPORTS.md#6-aws-sns-fix-report-2026-02-22) — 12 bugs: auth, profile, images, nickname, presigned URLs, MIME, VITE_BASE_PATH            |
| §7  | 2026-02-22 | [AWS+Azure Combined Fix](AI_AGENT_12_BUG_FIX_REPORTS.md#7-aws--azure-combined-sns-fix-2026-02-22) — Cognito unauthorized_client, Azure CORS, routePrefix, AD redirect_uris       |
| §8  | 2026-02-22 | [Refactoring & Infra Fix](AI_AGENT_12_BUG_FIX_REPORTS.md#8-refactoring--infrastructure-fix-2026-02-22) — AFD SPA rewrite rule, CI/CD cleanup, Pulumi dead code, staging bugs     |
| §9  | 2026-02-23 | [GCP SNS Fix](AI_AGENT_12_BUG_FIX_REPORTS.md#9-gcp-sns-fix-report-2026-02-23) — CORS, Firebase domain, /limits 404, COOP header, signed URLs, IndentationError                   |
| §10 | 2026-02-27 | [OCR Formula Merge Bugs](AI_AGENT_12_BUG_FIX_REPORTS.md#10-ocr-formula-merge-bugs-2026-02-27) — display formula discarded, bytes serialization, polygon=None fallback            |
| §11 | 2026-03-02 | [Workspace Cleanup & GitHub Integration](AI_AGENT_09_GITHUB_INTEGRATION_JA.md) — legacy services removed, AI Agent GitHub workflow documented                                  |

---

## Recommended Reading Order

First session in this repo:

```
1. AI_AGENT_00_CRITICAL_RULES.md  ← mandatory: rules that prevent outages and wasted time
2. AI_AGENT_01_CONTEXT.md         ← what the project is, live endpoints, tech stack, directory tree
3. AI_AGENT_02_ARCHITECTURE.md    ← system topology, storage paths
4. AI_AGENT_06_STATUS.md          ← current health of all 3 cloud environments
5. AI_AGENT_09_GITHUB_INTEGRATION.md ← GitHub Issues/PRs workflow & AI Agent operations
```

On demand:

```
AI_AGENT_03_API.md      ← endpoint spec, request/response schema, data model
AI_AGENT_04_INFRA.md    ← Pulumi stacks, resource names, config keys, outputs
AI_AGENT_05_CICD.md     ← GitHub Actions workflows, secrets, branch→env mapping
AI_AGENT_07_RUNBOOKS.md     ← step-by-step procedures: deploy, rollback, check logs
AI_AGENT_08_SECURITY.md     ← auth config per cloud, current security gaps
AI_AGENT_09_GITHUB_INTEGRATION.md ← GitHub workflow, branch protection, AI operations
```

---

## Quick Decision Tree

```
Q: First time in this repo?
  → 00_CRITICAL_RULES → 01_CONTEXT → 02_ARCHITECTURE → 06_STATUS → 09_GITHUB_INTEGRATION

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
  → Consult GitHub Issues + AI PM dashboard (10_TASKS)
```

---

## Rules Summary

Full details: [AI_AGENT_00_CRITICAL_RULES.md](AI_AGENT_00_CRITICAL_RULES.md)

| Rule | Topic            | One-line summary                                                                         |
| ---- | ---------------- | ---------------------------------------------------------------------------------------- |
| 0    | Language         | All docs, code, and commits must be written in English                                   |
| 1    | File operations  | Edit a few files at a time — large batches risk network timeout / silent corruption      |
| 2    | ARM vs x86       | Dev container is aarch64; always use `--platform linux/amd64` Docker for deploy builds   |
| 3    | main branch      | Push to `main` = immediate production deployment                                         |
| 4    | AUTH_DISABLED    | Must always be `false` — was accidentally `true` in a past incident                      |
| 5    | Env vars source  | Lambda/Cloud Run env vars from `pulumi stack output`, never from GitHub Secrets          |
| 6    | Vite base path   | AWS frontend must be built with `VITE_BASE_PATH=/sns/`                                   |
| 7    | S3 images        | Images bucket is private — always return presigned GET URLs, never raw S3 keys           |
| 8    | CloudFront cert  | Set `customDomain` + `acmCertificateArn` in Pulumi config before `pulumi up` on prod-AWS |
| 9    | Cognito JWT      | Call `jwt_verifier.py` with `verify_at_hash=False` when only `id_token` is sent          |
| 10   | GCP main.py      | Always include `main.py` (copy of `function.py`) in the GCP deployment ZIP               |
| 11   | GCP signed URLs  | Pass `service_account_email` + `access_token` to `generate_signed_url()`                 |
| 12   | Firebase domains | Register new domains via Identity Toolkit API with `x-goog-user-project` header          |
| 13   | GCP COOP header  | CDN must send `Cross-Origin-Opener-Policy: same-origin-allow-popups`                     |

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
