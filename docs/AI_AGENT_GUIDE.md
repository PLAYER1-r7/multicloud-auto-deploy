# AI Agent Guide — multicloud-auto-deploy

> **Purpose**: This document is the single entry point for AI agents working on this repository.
> It supersedes the fragmented per-topic docs by providing machine-readable, structured knowledge.
> Human-readable originals are preserved in their original locations and under `docs/archive/`.

---

## Document Map

| Section                      | File                                                                     | Status |
| ---------------------------- | ------------------------------------------------------------------------ | ------ |
| 01 — Project Overview        | [AI_AGENT_01_OVERVIEW.md](AI_AGENT_01_OVERVIEW.md)                       | ✅     |
| 02 — Repository Layout       | [AI_AGENT_02_LAYOUT.md](AI_AGENT_02_LAYOUT.md)                           | ✅     |
| 03 — Architecture            | [AI_AGENT_03_ARCHITECTURE.md](AI_AGENT_03_ARCHITECTURE.md)               | ✅     |
| 04 — API & Data Model        | [AI_AGENT_04_API.md](AI_AGENT_04_API.md)                                 | ✅     |
| 05 — Infrastructure (Pulumi) | [AI_AGENT_05_INFRA.md](AI_AGENT_05_INFRA.md)                             | ✅     |
| 06 — CI/CD Pipelines         | [AI_AGENT_06_CICD.md](AI_AGENT_06_CICD.md)                               | ✅     |
| 07 — Environment Status      | [AI_AGENT_07_STATUS.md](AI_AGENT_07_STATUS.md)                           | ✅     |
| 08 — Runbooks                | [AI_AGENT_08_RUNBOOKS.md](AI_AGENT_08_RUNBOOKS.md)                       | ✅     |
| 09 — Security                | [AI_AGENT_09_SECURITY.md](AI_AGENT_09_SECURITY.md)                       | ✅     |
| 10 — Remaining Tasks         | [AI_AGENT_10_TASKS.md](AI_AGENT_10_TASKS.md)                             | ✅     |
| 11 — Workspace Migration     | [AI_AGENT_11_WORKSPACE_MIGRATION.md](AI_AGENT_11_WORKSPACE_MIGRATION.md) | ✅     |

### Fix Reports

| Report                                | File                                                                 | Summary                                                                                    |
| ------------------------------------- | -------------------------------------------------------------------- | ------------------------------------------------------------------------------------------ |
| AWS Simple-SNS Fix (2026-02-20)       | [AWS_SNS_FIX_REPORT.md](AWS_SNS_FIX_REPORT.md)                       | Fixed Lambda env vars / CI/CD race condition / logout 404                                  |
| AWS Production SNS Fix (2026-02-21)   | [AWS_PRODUCTION_SNS_FIX_REPORT.md](AWS_PRODUCTION_SNS_FIX_REPORT.md) | Fixed `localhost:8000` fallback — empty API_BASE_URL caused by unset GitHub Secret in prod |
| Azure Simple-SNS Fix (2026-02-21)     | [AZURE_SNS_FIX_REPORT.md](AZURE_SNS_FIX_REPORT.md)                   | Investigation and fix for intermittent AFD /sns/\* 502 errors                              |
| AWS Production HTTPS Fix (2026-02-21) | [AWS_HTTPS_FIX_REPORT.md](AWS_HTTPS_FIX_REPORT.md)                   | Fixed ERR_CERT_COMMON_NAME_INVALID caused by missing CloudFront alias / ACM certificate    |

---

## Quick Decision Tree

```
Q: I want to modify code
  → services/api/**      : see 04_API
  → infrastructure/**   : see 05_INFRA
  → .github/workflows/  : see 06_CICD
  → static-site/**      : see 03_ARCHITECTURE (Static Site section)

Q: I want to check whether the live environments are healthy
  → see 07_STATUS

Q: Something is broken / I need to fix an error
  → see 08_RUNBOOKS

Q: I don't know what to work on next
  → see 10_TASKS (prioritised backlog)
```

---

## Critical Facts (always keep in mind)

1. **GitHub Actions workflows exist in ONE location only**
   - `ashnova/.github/workflows/` ← the real files that CI reads (git repo root)
   - `multicloud-auto-deploy/.github/` was **deleted on 2026-02-21**
   - When VS Code is opened with `multicloud-auto-deploy/` as the root, `.github/` is not visible in the file tree, but CI works correctly
     → **To edit workflows, run `cd /workspaces/ashnova` first.**

2. **Pushing to `main` = production deployment**
   develop → staging, main → production.

3. **All three cloud staging environments are operational (as of 2026-02-20)**
   AWS / Azure / GCP staging are all green.

4. **Storage path structure (all three clouds share this layout)**
   - `/` → landing page (`static-site/`)
   - `/sns/` → React SNS app (`services/frontend_react/dist/`)
     React is built with `base="/sns/"`.

5. **Authentication must NOT be disabled in staging**
   `AUTH_DISABLED=false` is the correct value. A past bug accidentally set it to `true`.
   In production, set `AUTH_PROVIDER` per cloud.

6. **AWS production CloudFront — Pulumi config is required (prevents regression on redeploy)**
   Without setting the following before `pulumi up --stack production`, CloudFront will revert to `CloudFrontDefaultCertificate:true` and `NET::ERR_CERT_COMMON_NAME_INVALID` will recur:

   ```bash
   cd infrastructure/pulumi/aws
   pulumi config set customDomain www.aws.ashnova.jp --stack production
   pulumi config set acmCertificateArn arn:aws:acm:us-east-1:278280499340:certificate/914b86b1-4c10-4354-91cf-19c4460dcde5 --stack production
   ```

   Details: [AWS_HTTPS_FIX_REPORT.md](AWS_HTTPS_FIX_REPORT.md)

7. **Lambda env vars must be sourced from Pulumi outputs — NOT from GitHub Secrets**
   Relying on secrets like `API_GATEWAY_ENDPOINT` leads to silently empty values when
   the secret is absent (e.g., production environment). The CI/CD workflows
   (`deploy-aws.yml`, `deploy-frontend-web-aws.yml`) now read all values directly from
   `pulumi stack output`. Do not revert this pattern.
   Details: [AWS_PRODUCTION_SNS_FIX_REPORT.md](AWS_PRODUCTION_SNS_FIX_REPORT.md)
