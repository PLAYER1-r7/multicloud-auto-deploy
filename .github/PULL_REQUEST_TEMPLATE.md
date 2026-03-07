## Summary

<!-- Describe the change in 1-3 sentences. -->

## Type of Change

- [ ] Bug fix
- [ ] New feature
- [ ] Refactoring (no functional change)
- [ ] Infrastructure / CI-CD change
- [ ] Documentation update
- [ ] Dependency upgrade

## Affected Cloud(s)

- [ ] AWS
- [ ] Azure
- [ ] GCP
- [ ] All clouds
- [ ] N/A (local / CI only)

## Testing

- [ ] Ran `ruff check` and `ruff format` on changed Python files
- [ ] Ran `tsc --noEmit` in `services/frontend_react`
- [ ] Triggered relevant workflow manually (`workflow_dispatch`) and verified staging
- [ ] Verified `/health` endpoints on affected cloud(s)

## Checklist

- [ ] All source code comments and commit messages are in **English** (Rule 0)
- [ ] No secrets, `.env` files, or build artifacts committed
- [ ] If infrastructure changed: `pulumi preview --stack staging` was reviewed before merge
- [ ] If CORS / domain changed: updated `.github/config/<cloud>.<env>.env`
- [ ] Docs updated if behavior changed (`docs/AI_AGENT_0*.md`)

## Related Issues / Tasks

<!-- Closes #XX or references ../.github/docs/AI_AGENT_BACKLOG_TASKS.md task # -->
