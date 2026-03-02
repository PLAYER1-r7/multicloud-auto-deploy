# 10 — AI Agent Project Management (Backlog & Execution)

> Part III — Operations | Parent: [AI_AGENT_GUIDE.md](AI_AGENT_GUIDE.md)
> Purpose: Define how AI agents manage planning, execution, status updates, and prioritisation for this repository.

---

## Scope

This document standardises AI-driven project management for:

- Backlog intake and triage (Issues)
- Delivery execution and review (PRs)
- Deployment and environment safety checks (Actions + status docs)
- Operational reporting (generated dashboard artifacts)

It complements:

- [AI_AGENT_00_CRITICAL_RULES.md](AI_AGENT_00_CRITICAL_RULES.md)
- [AI_AGENT_06_STATUS.md](AI_AGENT_06_STATUS.md)
- [AI_AGENT_07_RUNBOOKS.md](AI_AGENT_07_RUNBOOKS.md)
- [AI_AGENT_09_GITHUB_INTEGRATION_JA.md](AI_AGENT_09_GITHUB_INTEGRATION_JA.md)

---

## Strategy

### S1. Single source of truth

- Use GitHub Issues as the canonical backlog.
- Use labels + milestones for priority and release intent.
- Keep environment facts in [AI_AGENT_06_STATUS.md](AI_AGENT_06_STATUS.md), not in issue comments.

### S2. Cadence-driven execution

- Daily: triage new issues, re-score priorities, unblock stalled items.
- Weekly: choose sprint candidates and freeze top priorities.
- Release gate: verify CI health + production risk before merge to `main`.

### S3. Risk-first prioritisation

Order work by impact to production and security:

1. security and auth regressions
2. production incidents
3. staging blockers affecting release confidence
4. feature and refactor work

### S4. Root-cause closure

- Follow Rule 0.5: solve root cause when feasible.
- If temporary mitigation is used, record expiry and permanent follow-up issue.

---

## Tooling

## Required tools

| Tool | Usage |
| --- | --- |
| GitHub Issues | backlog, triage, ownership |
| GitHub Pull Requests | implementation review and merge gating |
| GitHub Actions | CI/CD health and deployment status |
| GitHub Labels | priority, cloud scope, work type |
| GitHub Milestones | release grouping |
| `gh` CLI | automation access for issues/PR/workflows |
| `scripts/agent_pm_sync.py` | generate project management snapshot/dashboard |

## Optional tools

| Tool | Usage |
| --- | --- |
| GitHub Projects | board view (if team wants Kanban) |
| `scripts/monitor-cicd.sh` | CI failure deep monitoring |

---

## Authentication request policy

When an operation requires authentication (for example `gh`, `aws`, `az`, `gcloud`, registry login, or third-party APIs), AI agents must:

1. Detect missing auth early (before repeated retries).
2. Immediately request user authentication with an exact command or minimal steps.
3. Explain which task is blocked and what will continue automatically after authentication.
4. Resume execution once authentication is completed.

If authentication cannot be completed at that moment, AI agents must pause the blocked path and re-request authentication. Avoid switching to fallback or reduced-scope alternatives by default; only use alternatives when the user explicitly requests them.

For `gh`-based project management tasks, the default request command is:

```bash
gh auth login
```

---

## Labels and conventions

Use these labels consistently:

- Work type: `bug`, `feature`, `refactor`, `docs`
- Cloud scope: `aws`, `azure`, `gcp`, `all`
- Priority: `priority:critical`, `priority:high`, `priority:low`
- Workflow state: `blocked`

Branch naming:

- `feature/issue-{id}-{short-desc}`
- `bugfix/issue-{id}-{short-desc}`
- `refactor/issue-{id}-{short-desc}`
- `docs/issue-{id}-{short-desc}`

---

## Operating model

## Daily AI PM loop

0. Verify required authentication context (`gh`, and others needed by the current task).
1. Sync dashboard snapshot (`project-management: sync`).
2. Inspect top priority issues.
3. Update next-action comments on blocked or stale issues.
4. Propose or create implementation branch for highest unblocked issue.
5. Validate CI trend before requesting merge.

## Weekly AI PM loop

1. Re-check unresolved issues older than 14 days.
2. Promote/demote priorities based on production/staging risk.
3. Update milestone alignment.
4. Post summary in project tracking channel (or issue).

---

## Generated artifacts

The AI PM sync process writes:

- `docs/generated/project-management/snapshot.json`
- `docs/generated/project-management/dashboard.md`

Do not manually edit generated files. Re-run sync instead.

Automated refresh is also configured by GitHub Actions:

- Workflow: `.github/workflows/project-management-sync.yml`
- Schedule: daily 09:15 JST (00:15 UTC)
- Output commit: `docs/generated/project-management/snapshot.json`, `docs/generated/project-management/dashboard.md`

## Branch protection baseline (solo development)

Recommended `main` policy for solo development:

- Require pull request before merging: enabled
- Required approving review count: `0`
- Required status checks: enabled (`strict: true`)
  - `CodeQL — javascript-typescript`
  - `CodeQL — python`

Operational verification sequence:

1. Merge workflow update PR to `main`.
2. Trigger `Project Management Sync` manually.
3. Confirm latest run and `sync` job are `completed/success`.

---

## Definition of done (project management)

An issue is operationally done when all are true:

- PR merged with passing required checks
- deployment target verified according to branch rules (`develop`/`main`)
- relevant docs updated (`STATUS`, runbook, or feature reference)
- issue closed with root-cause summary

---

## Commands

```bash
# Generate/refresh AI PM dashboard
python3 scripts/agent_pm_sync.py

# VS Code task equivalent
# Task label: project-management: sync
```

```bash
# Manual GitHub Actions trigger
gh workflow run "Project Management Sync"
```
