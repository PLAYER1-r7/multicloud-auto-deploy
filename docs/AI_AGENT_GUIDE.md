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
   - `multicloud-auto-deploy/.github/` は **2026-02-21 に削除済み**
   - `multicloud-auto-deploy/` を VS Code で開いた場合、`.github/` は見えないが CI は正常動作する
     → **ワークフロー編集は `cd /workspaces/ashnova` してから行う。**

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
