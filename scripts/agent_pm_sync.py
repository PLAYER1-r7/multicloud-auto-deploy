#!/usr/bin/env python3
"""Generate AI project-management snapshot and dashboard from GitHub data."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def run_gh_json(args: list[str]) -> Any:
    command = ["gh", *args]
    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or f"gh command failed: {' '.join(command)}")
    return json.loads(result.stdout or "null")


def repo_from_gh() -> tuple[str, str]:
    repo = subprocess.run(
        ["gh", "repo", "view", "--json", "nameWithOwner", "-q", ".nameWithOwner"],
        capture_output=True,
        text=True,
    )
    if repo.returncode == 0:
        value = repo.stdout.strip()
        if "/" in value:
            owner, name = value.split("/", 1)
            return owner, name

    remote = subprocess.run(
        ["git", "remote", "get-url", "origin"],
        capture_output=True,
        text=True,
    )
    if remote.returncode != 0:
        raise RuntimeError(
            "Cannot detect repository. Ensure this is a git repository with origin remote configured."
        )

    remote_url = remote.stdout.strip()
    match = re.search(r"github\.com[:/](?P<owner>[^/]+)/(?P<repo>[^/.]+)(?:\.git)?$", remote_url)
    if not match:
        raise RuntimeError(f"Cannot parse owner/repo from remote URL: {remote_url}")
    return match.group("owner"), match.group("repo")


def fetch_open_issues(owner: str, repo: str, max_pages: int = 3) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    for page in range(1, max_pages + 1):
        page_items = run_gh_json(
            [
                "api",
                f"repos/{owner}/{repo}/issues?state=open&per_page=100&page={page}",
            ]
        )
        if not page_items:
            break
        issue_items = [item for item in page_items if "pull_request" not in item]
        issues.extend(issue_items)
        if len(page_items) < 100:
            break
    return issues


def fetch_open_prs() -> list[dict[str, Any]]:
    return run_gh_json(
        [
            "pr",
            "list",
            "--state",
            "open",
            "--limit",
            "100",
            "--json",
            "number,title,isDraft,reviewDecision,mergeStateStatus,updatedAt,author",
        ]
    )


def fetch_workflow_runs() -> list[dict[str, Any]]:
    return run_gh_json(
        [
            "run",
            "list",
            "--limit",
            "30",
            "--json",
            "status,conclusion,workflowName,displayTitle,updatedAt",
        ]
    )


def parse_iso(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def labels_of(issue: dict[str, Any]) -> set[str]:
    return {label.get("name", "") for label in issue.get("labels", []) if isinstance(label, dict)}


def issue_score(issue: dict[str, Any], now: datetime) -> int:
    labels = labels_of(issue)
    score = 0
    if "priority:critical" in labels:
        score += 100
    elif "priority:high" in labels:
        score += 70
    elif "priority:low" in labels:
        score += 25
    else:
        score += 40

    if "bug" in labels:
        score += 20
    if "blocked" in labels:
        score += 15

    created = parse_iso(issue["created_at"])
    age_days = (now - created).days
    score += min(age_days, 30)
    return score


def summarise(
    owner: str,
    repo: str,
    issues: list[dict[str, Any]],
    prs: list[dict[str, Any]],
    runs: list[dict[str, Any]],
) -> dict[str, Any]:
    now = datetime.now(timezone.utc)
    count = {
        "issues_open": len(issues),
        "issues_blocked": 0,
        "issues_critical": 0,
        "issues_high": 0,
        "issues_older_7d": 0,
        "issues_older_14d": 0,
        "prs_open": len(prs),
        "prs_draft": 0,
        "prs_waiting_review": 0,
        "runs_success": 0,
        "runs_failure": 0,
        "runs_in_progress": 0,
    }
    by_label: dict[str, int] = {
        "bug": 0,
        "feature": 0,
        "refactor": 0,
        "docs": 0,
        "aws": 0,
        "azure": 0,
        "gcp": 0,
        "all": 0,
        "blocked": 0,
    }

    scored_issues: list[dict[str, Any]] = []
    for issue in issues:
        labels = labels_of(issue)
        created = parse_iso(issue["created_at"])
        age_days = (now - created).days

        if "blocked" in labels:
            count["issues_blocked"] += 1
            by_label["blocked"] += 1
        if "priority:critical" in labels:
            count["issues_critical"] += 1
        if "priority:high" in labels:
            count["issues_high"] += 1
        if age_days >= 7:
            count["issues_older_7d"] += 1
        if age_days >= 14:
            count["issues_older_14d"] += 1

        for name in ("bug", "feature", "refactor", "docs", "aws", "azure", "gcp", "all"):
            if name in labels:
                by_label[name] += 1

        scored_issues.append(
            {
                "number": issue["number"],
                "title": issue["title"],
                "url": issue["html_url"],
                "labels": sorted(labels),
                "created_at": issue["created_at"],
                "age_days": age_days,
                "score": issue_score(issue, now),
            }
        )

    for pr in prs:
        if pr.get("isDraft"):
            count["prs_draft"] += 1
        review_decision = (pr.get("reviewDecision") or "").upper()
        if review_decision in {"", "REVIEW_REQUIRED"} and not pr.get("isDraft"):
            count["prs_waiting_review"] += 1

    for run in runs:
        status = (run.get("status") or "").lower()
        conclusion = (run.get("conclusion") or "").lower()
        if status in {"queued", "in_progress", "requested", "waiting", "pending"}:
            count["runs_in_progress"] += 1
        elif conclusion == "success":
            count["runs_success"] += 1
        elif conclusion in {
            "failure",
            "cancelled",
            "timed_out",
            "startup_failure",
            "action_required",
        }:
            count["runs_failure"] += 1

    scored_issues.sort(key=lambda item: item["score"], reverse=True)
    top_priority = scored_issues[:10]

    return {
        "generated_at_utc": now.isoformat(),
        "summary": count,
        "labels": by_label,
        "top_priority": top_priority,
        "open_prs": [
            {
                "number": pr.get("number"),
                "title": pr.get("title"),
                "url": f"https://github.com/{owner}/{repo}/pull/{pr.get('number')}",
                "is_draft": pr.get("isDraft"),
                "review_decision": pr.get("reviewDecision"),
                "merge_state": pr.get("mergeStateStatus"),
                "updated_at": pr.get("updatedAt"),
            }
            for pr in prs
        ],
    }


def render_markdown(owner: str, repo: str, data: dict[str, Any]) -> str:
    s = data["summary"]
    labels = data["labels"]
    warning = data.get("warning")
    lines = [
        "# AI Project Management Dashboard",
        "",
        f"- Repository: `{owner}/{repo}`",
        f"- Generated (UTC): `{data['generated_at_utc']}`",
        "",
    ]

    if warning:
        lines.extend(
            [
                "## Warning",
                "",
                f"- {warning}",
                "",
            ]
        )

    lines.extend(
        [
            "## Headline Metrics",
            "",
            f"- Open issues: **{s['issues_open']}** (critical: {s['issues_critical']}, high: {s['issues_high']}, blocked: {s['issues_blocked']})",
            f"- Issue aging: **{s['issues_older_7d']}** (>=7d), **{s['issues_older_14d']}** (>=14d)",
            f"- Open PRs: **{s['prs_open']}** (draft: {s['prs_draft']}, waiting review: {s['prs_waiting_review']})",
            f"- CI runs (last 30): success **{s['runs_success']}**, failure **{s['runs_failure']}**, in progress **{s['runs_in_progress']}**",
            "",
            "## Backlog Distribution",
            "",
            f"- Work type: bug {labels['bug']}, feature {labels['feature']}, refactor {labels['refactor']}, docs {labels['docs']}",
            f"- Cloud scope: aws {labels['aws']}, azure {labels['azure']}, gcp {labels['gcp']}, all {labels['all']}",
            "",
            "## Top Priority Issues",
            "",
        ]
    )

    top_priority = data.get("top_priority", [])
    if not top_priority:
        lines.append("- No open issues.")
    else:
        for item in top_priority:
            lines.append(
                f"- #{item['number']} (score={item['score']}, age={item['age_days']}d) [{item['title']}]({item['url']})"
            )

    lines.extend(
        [
            "",
            "## Operational Next Actions",
            "",
            "1. Resolve blocked + critical issues before feature work.",
            "2. Keep PR waiting-review count close to zero.",
            "3. Investigate CI failures before merge-to-main windows.",
            "",
            "> This file is generated by `scripts/agent_pm_sync.py`. Do not edit manually.",
        ]
    )
    return "\n".join(lines) + "\n"


def write_outputs(output_dir: Path, owner: str, repo: str, data: dict[str, Any]) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    snapshot_path = output_dir / "snapshot.json"
    dashboard_path = output_dir / "dashboard.md"

    snapshot_path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    dashboard_path.write_text(render_markdown(owner, repo, data), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate AI PM snapshot/dashboard from GitHub.")
    parser.add_argument("--owner", help="GitHub owner (optional; auto-detected by default)")
    parser.add_argument(
        "--repo", help="GitHub repository name (optional; auto-detected by default)"
    )
    parser.add_argument(
        "--output-dir",
        default="docs/generated/project-management",
        help="Output directory for generated files",
    )
    args = parser.parse_args()

    try:
        if args.owner and args.repo:
            owner, repo = args.owner, args.repo
        else:
            owner, repo = repo_from_gh()

        warning: str | None = None
        try:
            issues = fetch_open_issues(owner, repo)
            prs = fetch_open_prs()
            runs = fetch_workflow_runs()
        except RuntimeError as fetch_error:
            warning = (
                "GitHub API data fetch failed (likely gh auth missing). "
                "Run `gh auth login` then re-run this command for live metrics. "
                f"Details: {fetch_error}"
            )
            issues = []
            prs = []
            runs = []

        data = summarise(owner, repo, issues, prs, runs)
        if warning:
            data["warning"] = warning
        write_outputs(Path(args.output_dir), owner, repo, data)
    except RuntimeError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    except json.JSONDecodeError:
        print("error: failed to decode JSON from gh command output", file=sys.stderr)
        return 1

    print("AI PM snapshot generated:")
    print("- docs/generated/project-management/snapshot.json")
    print("- docs/generated/project-management/dashboard.md")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
