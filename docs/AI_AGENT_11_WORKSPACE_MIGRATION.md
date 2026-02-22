# 11 — Workspace Migration & Repository Cleanup (2026-02-21)

> Parent: [AI_AGENT_GUIDE.md](AI_AGENT_GUIDE.md)

---

## Overview

A record of the repository cleanup performed on 2026-02-21.  
This is the reference for working with `multicloud-auto-deploy/` as the VS Code root folder going forward.

---

## Repository Structure (after migration)

```
ashnova/                              ← git repository root
│
├── .devcontainer/                    ← devcontainer config when opening ashnova/ as a whole
├── .github/
│   └── workflows/                   ← ★ The only location that GitHub Actions reads
│       ├── deploy-aws.yml
│       ├── deploy-azure.yml
│       ├── deploy-gcp.yml
│       ├── deploy-landing-aws.yml
│       ├── deploy-landing-azure.yml
│       ├── deploy-landing-gcp.yml
│       ├── deploy-frontend-web-aws.yml
│       ├── deploy-frontend-web-azure.yml
│       └── deploy-frontend-web-gcp.yml
├── .gitignore
├── .vscode/                          ← VS Code settings when opening ashnova/ (old, not in use)
├── LICENSE
├── README.md
│
└── multicloud-auto-deploy/           ← ★ Project root (open this folder in VS Code)
    ├── .devcontainer/                ← VS Code devcontainer config (when opening multicloud-auto-deploy/)
    ├── .gitignore
    ├── .vscode/
    │   └── settings.json            ← VS Code settings (Python venv, formatting, etc.)
    ├── infrastructure/
    ├── services/
    ├── static-site/                  ← ★ Landing pages (includes aws/azure/gcp subdirectories)
    ├── scripts/
    ├── docs/
    └── ...
```

---

## Notes When Opening `multicloud-auto-deploy/` in VS Code

### Location of `.github/workflows/`

**GitHub Actions workflows exist ONLY in `ashnova/.github/workflows/`.**  
When VS Code is opened with `multicloud-auto-deploy/` as the root, `.github/workflows/` is not visible in the file tree.  
However, since the git repository root is still `ashnova/`,  
**CI/CD works correctly (pushing to GitHub triggers workflows automatically).**

To edit workflows, from the terminal:

```bash
# From inside the devcontainer
cd /workspaces/ashnova    # navigate to git root
code .github/workflows/deploy-aws.yml
```

Alternatively, editing via the GitHub web interface is reliable.

### Path References Inside Workflows

Workflows reference files using **paths relative to the git repository root.**  
Since they are written relative to `multicloud-auto-deploy/`, paths like the following are common:

```yaml
# Example path inside a workflow
working-directory: multicloud-auto-deploy/services/api
aws s3 sync multicloud-auto-deploy/static-site/ s3://...
cd multicloud-auto-deploy/infrastructure/pulumi/aws
```

### Devcontainer Configuration

`multicloud-auto-deploy/.devcontainer/devcontainer.json` is used.  
The `postCreateCommand` runs `bash .devcontainer/setup.sh`, which automatically:

- Runs `pip install` for `infrastructure/pulumi/aws|azure|gcp/requirements.txt`
- Grants execute permission to `scripts/*.sh`

---

## Files Deleted and Cleaned Up on 2026-02-21

### Deleted Directories (old versions)

| Deleted Path                        | Reason                                                                              |
| ----------------------------------- | ----------------------------------------------------------------------------------- |
| `ashnova/ashnova.v1/`               | Old v1 code. Cloud resources already deleted.                                       |
| `ashnova/ashnova.v2/`               | Old v2 code. No cloud resources.                                                    |
| `ashnova/ashnova.v3/`               | Old v3 code. Cloud resources already deleted.                                       |
| `ashnova/infrastructure/`           | Old copy of `multicloud-auto-deploy/infrastructure/`                                |
| `ashnova/services/api/`             | Old copy of `multicloud-auto-deploy/services/api/`. CI/CD references the mcad version. |
| `ashnova/services/frontend_react/`  | No longer referenced after `deploy-frontend-*.yml` was deleted.                    |
| `ashnova/services/frontend_reflex/` | Not referenced by any workflow.                                                     |
| `ashnova/scripts/`                  | Old copy of `multicloud-auto-deploy/scripts/`. CI/CD references the mcad version.  |
| `ashnova/static-site/`              | Consolidated into `multicloud-auto-deploy/static-site/`                            |
| `multicloud-auto-deploy/.github/`   | Dead code not read by GitHub Actions.                                               |

### Deleted Workflows

| Deleted File                                       | Reason                                                                                  |
| -------------------------------------------------- | --------------------------------------------------------------------------------------- |
| `deploy-multicloud.yml.disabled`                   | Explicitly disabled with `.disabled` extension                                          |
| `main_multicloud-auto-deplopy-staging-funcapp.yml` | Auto-generated by Azure Portal. Deploys to non-existent resources. Contains typo.      |
| `main_multicloud-auto-deploy-staging-func.yml`     | Same as above                                                                           |
| `deploy-frontend-aws.yml`                          | Deployed `ashnova/services/frontend_react/` (old) with hardcoded staging values         |
| `deploy-frontend-azure.yml`                        | Same as above. Hardcoded to deleted old API URL.                                        |
| `deploy-frontend-gcp.yml`                          | Same as above                                                                           |

### Files Moved or Created

| Action                                              | Content                                        |
| --------------------------------------------------- | ---------------------------------------------- |
| Created `multicloud-auto-deploy/.vscode/settings.json` | Python venv path and editor settings        |
| Copied `multicloud-auto-deploy/static-site/aws/`    | Migrated from `ashnova/static-site/aws/`       |
| Copied `multicloud-auto-deploy/static-site/azure/`  | Migrated from `ashnova/static-site/azure/`     |
| Copied `multicloud-auto-deploy/static-site/gcp/`    | Migrated from `ashnova/static-site/gcp/`       |

### Workflow Path Updates

Changed `static-site/` → `multicloud-auto-deploy/static-site/` in `deploy-landing-*.yml` and `deploy-aws.yml` / `deploy-gcp.yml`.

---

## Deleted Cloud Resources (Old Versions)

### v3 (Pulumi: ashnova-v3-aws/staging)

- 22 resources deleted with `pulumi destroy` (2026-02-21)
- Pulumi stack also removed with `pulumi stack rm`

### v1 (Terraform-managed, satoshi AWS profile)

Deleted directly via AWS CLI:

- API Gateway REST API: `utw7e2zuwc`
- Lambda Layer `simple-sns-nodejs-dependencies`: versions 5, 6, 10, 11
- DynamoDB table: `simple-sns-messages`

### v2

- No deployed resources (no action required)

### Orphaned Pulumi Stack

- `ashnova/simple-sns-aws/staging` (0 resources) removed with `pulumi stack rm`

---

## Active Production Environments (Verified After Deletion)

| Cloud | URL                           | Verified       |
| ----- | ----------------------------- | -------------- |
| AWS   | https://www.aws.ashnova.jp/   | 2026-02-21 ✅  |
| Azure | https://www.azure.ashnova.jp/ | 2026-02-21 ✅  |
| GCP   | https://www.gcp.ashnova.jp/   | 2026-02-21 ✅  |

All 12 tests (landing / SNS app / API health check / GET /posts) PASSED.  
API version: `3.0.0`

---

## Current Workflow List (9 workflows)

| File                            | Trigger Path                                      | Role                                                              |
| ------------------------------- | ------------------------------------------------- | ----------------------------------------------------------------- |
| `deploy-aws.yml`                | `multicloud-auto-deploy/**`                       | AWS full-stack deploy (Pulumi + API + frontend_react + landing)   |
| `deploy-azure.yml`              | `multicloud-auto-deploy/**`                       | Azure full-stack deploy                                           |
| `deploy-gcp.yml`                | `multicloud-auto-deploy/**`                       | GCP full-stack deploy                                             |
| `deploy-landing-aws.yml`        | `multicloud-auto-deploy/static-site/**`           | Update AWS landing page only                                      |
| `deploy-landing-azure.yml`      | `multicloud-auto-deploy/static-site/**`           | Update Azure landing page only                                    |
| `deploy-landing-gcp.yml`        | `multicloud-auto-deploy/static-site/**`           | Update GCP landing page only                                      |
| `deploy-frontend-web-aws.yml`   | `multicloud-auto-deploy/services/frontend_web/**` | Update frontend_web Lambda only (AWS)                             |
| `deploy-frontend-web-azure.yml` | `multicloud-auto-deploy/services/frontend_web/**` | Update frontend_web only (Azure)                                  |
| `deploy-frontend-web-gcp.yml`   | `multicloud-auto-deploy/services/frontend_web/**` | Update frontend_web only (GCP)                                    |

---

## Troubleshooting

### Workflows Not Visible on GitHub

When `multicloud-auto-deploy/` is opened in VS Code, `.github/` is not visible in that workspace,  
but workflows display correctly in the GitHub repository's Actions tab (`/actions`).  
To verify locally: `ls /workspaces/ashnova/.github/workflows/`

### static-site Changes Not Deployed by CI

Changes must be made under `multicloud-auto-deploy/static-site/**` (old path: `ashnova/static-site/`).  
The trigger path in `deploy-landing-*.yml` has been updated to `multicloud-auto-deploy/static-site/**`.

### Pulumi Stack Not Found

Navigate to `cd /workspaces/ashnova/multicloud-auto-deploy/infrastructure/pulumi/aws` and run `pulumi stack ls`.  
Inside the dev container, AWS / Azure / GCP credentials are mounted at `/home/vscode/.aws` etc.

### Python Interpreter Not Found

`multicloud-auto-deploy/.vscode/settings.json` contains the venv path, but `.venv` does not exist initially.  
Create a Python virtual environment in each `infrastructure/pulumi/*/` directory:

```bash
cd infrastructure/pulumi/aws
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

---

---

## Git Root Migration (Making `multicloud-auto-deploy/` the New Root)

### Readiness Status (Completed 2026-02-21)

| Item | Status |
| ---- | ------ |
| `multicloud-auto-deploy/.github/workflows/` (9 files) | ✅ Created and paths corrected |
| All 9 files must NOT contain the `multicloud-auto-deploy/` prefix | ✅ Verified via `grep -rc "multicloud-auto-deploy/" ...` → all files show `:0` |
| `multicloud-auto-deploy/.devcontainer/` (setup.sh relative paths) | ✅ Verified |
| `multicloud-auto-deploy/.gitignore` | ✅ Present |
| `multicloud-auto-deploy/LICENSE` | ✅ Present |
| `multicloud-auto-deploy/README.md` | ✅ Present |
| `multicloud-auto-deploy/.vscode/settings.json` | ✅ Created |
| `multicloud-auto-deploy/static-site/` (including aws/azure/gcp subdirectories) | ✅ Consolidated |

### Workflow Path Comparison

| File | Current (`ashnova/.github/workflows/`) | After Migration (`multicloud-auto-deploy/.github/workflows/`) |
| ---- | --------------------------------------- | ------------------------------------------------------------- |
| `deploy-aws.yml` | `cd multicloud-auto-deploy/services/api` | `cd services/api` |
| `deploy-aws.yml` | `cd multicloud-auto-deploy/infrastructure/pulumi/aws` | `cd infrastructure/pulumi/aws` |
| `deploy-landing-aws.yml` | `multicloud-auto-deploy/static-site/` | `static-site/` |
| trigger `paths:` | `"multicloud-auto-deploy/services/**"` | `"services/**"` |

### Git Migration Commands (Run Manually by User)

> **Note**: Choose exactly ONE of the options below and execute it. Verify on GitHub after completion.

#### Option A — Preserve History (Recommended)

```bash
cd /workspaces/ashnova

# Extract only the multicloud-auto-deploy/ history into a new branch
git subtree split --prefix=multicloud-auto-deploy -b git-root

# Verify
git log git-root --oneline | head -10

# Create a new repository and push
mkdir /tmp/ashnova-mcad
cd /tmp/ashnova-mcad
git init
git pull /workspaces/ashnova git-root
git remote add origin <new GitHub repo URL>
git push -u origin main
```

#### Option B — No History, Simple (For a Brand-New Repo)

```bash
cd /workspaces/ashnova/multicloud-auto-deploy
git init
git add .
git commit -m "chore: initialize repository root at multicloud-auto-deploy"
git remote add origin <new GitHub repo URL>
git branch -M main
git push -u origin main
```

#### Option C — `git filter-repo` (High Precision, Requires Installation)

```bash
pip install git-filter-repo

cd /workspaces/ashnova
git filter-repo --subdirectory-filter multicloud-auto-deploy --force
# → The ashnova/ repository itself is overwritten with the contents of multicloud-auto-deploy/
git remote set-url origin <new GitHub repo URL>
git push --force
```

### Post-Migration Steps

1. **Verify GitHub Actions**: The old `ashnova/.github/workflows/` will no longer be read by GitHub. The new repository's `.github/workflows/` will be automatically discovered.
2. **Re-register GitHub Secrets**: Re-add secrets (AWS/Azure/GCP credentials) registered in the old repository to the new repository.
3. **Verify Pulumi stack names with `pulumi config`**: Pulumi stacks are stored in Pulumi Cloud and are independent of the git root, but confirm that `name:` and `backend:` in `Pulumi.yaml` are correct.
4. **Open new root in VS Code**: Use `code /path/to/multicloud-auto-deploy` or open via devcontainer. `.devcontainer/` already uses correct relative paths.
5. **Archive old `ashnova/` repository**: After migration is complete, set the old repository to `Archived` on GitHub.

---

## Previous / Next Section

← [10 — Remaining Tasks](AI_AGENT_10_TASKS.md)

