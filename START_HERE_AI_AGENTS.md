# 🤖 START HERE — AI Agents Required Reading

> **⚠️ CRITICAL**: This is the **mandatory first document** for all AI agents working on this project.
> Reading time: 10-15 minutes to save hours/days of debugging and prevent production incidents.

---

## Why This Matters

This project manages **production infrastructure across AWS, Azure, and GCP**. Skipping critical rules has caused:

- ❌ Production outages
- ❌ Cost overruns (Premium SKU violations)
- ❌ Security incidents
- ❌ Data loss from environment confusion

**Read these documents in order before making ANY changes.**

---

## 🧭 Documentation Boundary (Read Before Starting)

This repository separates knowledge by purpose to reduce misreads:

- `docs/` = product implementation knowledge
  - Answers: "How do we build, run, and maintain the product?"
- `.github/` = repository operation knowledge
  - Answers: "How do we manage work and collaboration on GitHub?"

Start from the right entry point:

- Product tasks (implementation, architecture, API, infra): [docs/00_START_HERE.md](docs/00_START_HERE.md)
- Repository operation tasks (Issue/PR, Projects, automation workflow): [.github/00_START_HERE.md](.github/00_START_HERE.md)

---

## 📚 Required Reading Order

### 1️⃣ **CRITICAL RULES** (Read First — 5 min)

**📄 [docs/AI_AGENT_00_CRITICAL_RULES_JA.md](docs/AI_AGENT_00_CRITICAL_RULES_JA.md)**

🚨 **STOP**: This contains **non-negotiable rules** including:

- Premium SKU prohibition (Rule 18)
- Environment isolation (Rule 3)
- Deployment safety checks (Rule 1, 5)
- Security requirements (Rule 8, 19)

**Do not skip this. Violations have caused production incidents.**

---

### 2️⃣ **Project Context** (5 min)

**📄 [docs/AI_AGENT_01_CONTEXT_JA.md](docs/AI_AGENT_01_CONTEXT_JA.md)**

Understand:

- Project purpose and scope
- Technology stack
- Development workflow
- Directory structure

**Prerequisites**: Must read CRITICAL_RULES first

---

### 3️⃣ **Architecture Overview** (10 min)

**📄 [docs/AI_AGENT_02_ARCHITECTURE_JA.md](docs/AI_AGENT_02_ARCHITECTURE_JA.md)**

Learn:

- Multi-cloud architecture patterns
- Service dependencies
- Infrastructure components
- Data flow

**Prerequisites**: Must read CRITICAL_RULES + CONTEXT first

---

### 4️⃣ **Current Status** (5 min)

**📄 [docs/AI_AGENT_06_STATUS_JA.md](docs/AI_AGENT_06_STATUS_JA.md)**

Check:

- What's deployed vs in-progress
- Known issues and blockers
- Recent changes
- Active incidents

**Prerequisites**: Must read CRITICAL_RULES + CONTEXT + ARCHITECTURE first

---

## 🔍 Additional Resources (As Needed)

After completing the required reading, reference these based on your task:

- **API Design**: [docs/AI_AGENT_03_API_JA.md](docs/AI_AGENT_03_API_JA.md)
- **Infrastructure**: [docs/AI_AGENT_04_INFRA_JA.md](docs/AI_AGENT_04_INFRA_JA.md)
- **CI/CD**: [docs/AI_AGENT_05_CICD_JA.md](docs/AI_AGENT_05_CICD_JA.md)
- **Runbooks**: [docs/AI_AGENT_07_RUNBOOKS_JA.md](docs/AI_AGENT_07_RUNBOOKS_JA.md)
- **Security**: [docs/AI_AGENT_08_SECURITY_JA.md](docs/AI_AGENT_08_SECURITY_JA.md)
- **Tasks**: [docs/AI_AGENT_10_TASKS_JA.md](docs/AI_AGENT_10_TASKS_JA.md)
- **Bug Reports**: [docs/AI_AGENT_11_BUG_FIX_REPORTS_JA.md](docs/AI_AGENT_11_BUG_FIX_REPORTS_JA.md)
- **OCR/Math**: [docs/AI_AGENT_12_OCR_MATH_JA.md](docs/AI_AGENT_12_OCR_MATH_JA.md)
- **Testing**: [docs/AI_AGENT_13_TESTING_JA.md](docs/AI_AGENT_13_TESTING_JA.md)
- **Error Management**: [docs/AI_AGENT_15_ERROR_MANAGEMENT_SYSTEM.md](docs/AI_AGENT_15_ERROR_MANAGEMENT_SYSTEM.md)

---

## ✅ Pre-Task Checklist

Before starting any work, confirm:

- [ ] Read all 4 required documents above
- [ ] Understand Rule 18 (Premium SKU prohibition)
- [ ] Understand Rule 3 (Environment isolation)
- [ ] Know current deployment status
- [ ] Identified correct environment (staging/production)

---

## 🆘 Quick Reference

| Situation                  | Action                                                          |
| -------------------------- | --------------------------------------------------------------- |
| Unsure about a rule        | Re-read [CRITICAL_RULES](docs/AI_AGENT_00_CRITICAL_RULES_JA.md) |
| Need architectural context | Check [ARCHITECTURE](docs/AI_AGENT_02_ARCHITECTURE_JA.md)       |
| Deployment issues          | Consult [RUNBOOKS](docs/AI_AGENT_07_RUNBOOKS_JA.md)             |
| Security question          | Review [SECURITY](docs/AI_AGENT_08_SECURITY_JA.md)              |
| Testing guidance           | See [TESTING](docs/AI_AGENT_13_TESTING_JA.md)                   |

---

## 📢 For Human Developers

Looking for the main README? See **[README.md](README.md)**

This document is optimized for AI agent onboarding and contains the same critical information in a structured learning path.

---

**Last Updated**: 2026-03-07
**Version**: 1.0.90.277
