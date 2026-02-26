#!/usr/bin/env python3
"""
cost_report.py — AWS / Azure / GCP / GitHub のコスト月次レポート

使い方:
  python3 scripts/cost_report.py [--months 3] [--json]

必要な認証情報:
  AWS:    AWS_PROFILE または aws configure 済み環境 (Cost Explorer API)
  Azure:  az login 済み & AZURE_SUBSCRIPTION_ID 環境変数
  GCP:    gcloud auth login 済み & GCP_BILLING_ACCOUNT 環境変数
  GitHub: GITHUB_TOKEN 環境変数 & GH_ORG / GH_REPO 環境変数

オプション:
  --months N    過去 N ヶ月分を表示 (デフォルト: 3)
  --json        JSON 形式で出力
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.request
from datetime import date, timedelta
from pathlib import Path
from typing import Any

# ── .env ローダー ──────────────────────────────────────────────
def _load_dotenv() -> None:
    """scripts/mac-widget/.env または scripts/.env から認証情報を読み込む。"""
    _here = Path(__file__).resolve().parent
    candidates = [
        _here / "mac-widget" / ".env",
        _here / ".env",
        Path.home() / ".config" / "multicloud-cost" / ".env",
    ]
    for env_path in candidates:
        if env_path.exists():
            for line in env_path.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, _, val = line.partition("=")
                os.environ.setdefault(key.strip(), val.strip().strip("\"'"))
            break

_load_dotenv()


def _month_range(months_back: int) -> list[tuple[str, str]]:
    """過去 N ヶ月分の (start, end) 文字列リストを返す (YYYY-MM-DD)。"""
    ranges = []
    today = date.today()
    first_of_this_month = today.replace(day=1)
    for i in range(months_back, 0, -1):
        year = first_of_this_month.year
        month = first_of_this_month.month - i
        while month <= 0:
            month += 12
            year -= 1
        start = date(year, month, 1)
        next_month = month + 1
        next_year = year
        if next_month > 12:
            next_month = 1
            next_year += 1
        end = date(next_year, next_month, 1) - timedelta(days=1)
        ranges.append((start.strftime("%Y-%m-%d"), end.strftime("%Y-%m-%d")))
    return ranges


# ─────────────────────────────────────────────
# 為替レート
# ─────────────────────────────────────────────


def _get_usd_jpy_rate() -> float:
    """USD/JPY レートを open.er-api.com から取得。失敗時は 150.0 を返す。"""
    try:
        req = urllib.request.Request(
            "https://open.er-api.com/v6/latest/USD",
            headers={"User-Agent": "cost-monitor/1.0"},
        )
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read())
        return float(data["rates"]["JPY"])
    except Exception:
        return 150.0  # フォールバック


# ─────────────────────────────────────────────
# AWS (Cost Explorer)
# ─────────────────────────────────────────────


def _fetch_aws(months: int) -> list[dict[str, Any]]:
    results = []
    try:
        import boto3

        ce = boto3.client("ce", region_name="us-east-1")
        rate = _get_usd_jpy_rate()
        for start, end in _month_range(months):
            resp = ce.get_cost_and_usage(
                TimePeriod={"Start": start, "End": end},
                Granularity="MONTHLY",
                Metrics=["UnblendedCost"],
            )
            for item in resp["ResultsByTime"]:
                usd = float(item["Total"]["UnblendedCost"]["Amount"])
                results.append(
                    {
                        "provider": "AWS",
                        "period": item["TimePeriod"]["Start"][:7],
                        "cost_usd": round(usd, 4),
                        "cost_local": round(usd * rate),
                        "currency": "JPY",
                        "note": f"${usd:.4f} × ¥{rate:.0f}",
                    }
                )
    except ImportError:
        results.append({"provider": "AWS", "error": "boto3 not installed"})
    except Exception as exc:
        results.append({"provider": "AWS", "error": str(exc)})
    return results


# ─────────────────────────────────────────────
# Azure (Azure Cost Management REST API via CLI token)
# ─────────────────────────────────────────────


def _fetch_azure(months: int) -> list[dict[str, Any]]:
    results = []
    subscription_id = os.getenv("AZURE_SUBSCRIPTION_ID")
    if not subscription_id:
        return [{"provider": "Azure", "error": "AZURE_SUBSCRIPTION_ID not set"}]
    try:
        import json as _json
        import subprocess

        # az CLI でアクセストークンを取得
        token_result = subprocess.run(
            [
                "az",
                "account",
                "get-access-token",
                "--resource",
                "https://management.azure.com/",
                "--output",
                "json",
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if token_result.returncode != 0:
            return [
                {
                    "provider": "Azure",
                    "error": "az login required: " + token_result.stderr.strip(),
                }
            ]
        token = _json.loads(token_result.stdout)["accessToken"]

        import urllib.request

        for start, end in _month_range(months):
            url = (
                f"https://management.azure.com/subscriptions/{subscription_id}"
                f"/providers/Microsoft.CostManagement/query"
                f"?api-version=2023-11-01"
            )
            body = _json.dumps(
                {
                    "type": "ActualCost",
                    "dataSet": {
                        "granularity": "Monthly",
                        "aggregation": {
                            "totalCost": {"name": "Cost", "function": "Sum"}
                        },
                    },
                    "timeframe": "Custom",
                    "timePeriod": {
                        "from": start + "T00:00:00Z",
                        "to": end + "T23:59:59Z",
                    },
                }
            ).encode()
            req = urllib.request.Request(
                url,
                data=body,
                method="POST",
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json",
                },
            )
            with urllib.request.urlopen(req, timeout=30) as resp:
                data = _json.loads(resp.read())

            rows = data.get("properties", {}).get("rows", [])
            # rows: [[amount, '2026-02-01T00:00:00', 'JPY'], ...]
            for row in rows:
                amount = float(row[0]) if row else 0.0
                # BillingMonth は ISO datetime 文字列
                bm = str(row[1]) if len(row) > 1 else start
                period = bm[:7]  # '2026-02'
                currency = str(row[2]) if len(row) > 2 else "USD"
                results.append(
                    {
                        "provider": "Azure",
                        "period": period,
                        "cost_usd": round(amount, 4) if currency == "USD" else None,
                        "cost_local": round(amount, 4),
                        "currency": currency,
                    }
                )
    except Exception as exc:
        results.append({"provider": "Azure", "error": str(exc)})
    return results


# ─────────────────────────────────────────────
# GCP (Cloud Billing API via gcloud token)
# ─────────────────────────────────────────────


def _fetch_gcp(months: int) -> list[dict[str, Any]]:
    results = []
    billing_account = os.getenv("GCP_BILLING_ACCOUNT")
    if not billing_account:
        return [
            {
                "provider": "GCP",
                "error": "GCP_BILLING_ACCOUNT not set (e.g. 012345-ABCDEF-GHIJKL)",
            }
        ]
    try:
        import json as _json
        import subprocess

        token_result = subprocess.run(
            ["gcloud", "auth", "print-access-token"],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if token_result.returncode != 0:
            return [{"provider": "GCP", "error": "gcloud auth login required"}]
        token = token_result.stdout.strip()

        for start, end in _month_range(months):
            url = (
                f"https://cloudbilling.googleapis.com/v1/billingAccounts/{billing_account}/skus"
                f"?pageSize=1"
            )
            # Cloud Billing v1 に直接コスト照会がないため gcloud billing を利用
            # gcloud beta billing accounts describe で概算取得
            # 詳細は BigQuery billing export が必要 → ここは describe のみ
            cmd = subprocess.run(
                [
                    "gcloud",
                    "billing",
                    "accounts",
                    "describe",
                    billing_account,
                    "--format=json",
                ],
                capture_output=True,
                text=True,
                timeout=30,
            )
            if cmd.returncode == 0:
                info = _json.loads(cmd.stdout)
                results.append(
                    {
                        "provider": "GCP",
                        "period": start[:7],
                        "cost_usd": None,
                        "note": f"账単アカウント: {info.get('displayName', billing_account)} (詳細は BigQuery billing export を参照)",
                    }
                )
            else:
                results.append({"provider": "GCP", "error": cmd.stderr.strip()})
            break  # GCP Billing Account describe は月次内訳を返さないので1回のみ

        # gcloud projects list で各プロジェクトの概算を試みる
        projects_cmd = subprocess.run(
            ["gcloud", "projects", "list", "--format=value(projectId)"],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if projects_cmd.returncode == 0:
            project_ids = projects_cmd.stdout.strip().splitlines()
            results.append(
                {
                    "provider": "GCP",
                    "note": f"プロジェクト数: {len(project_ids)} (コスト詳細は https://console.cloud.google.com/billing を参照)",
                }
            )
    except Exception as exc:
        results.append({"provider": "GCP", "error": str(exc)})
    return results


# ─────────────────────────────────────────────
# GitHub Actions (Billing API)
# ─────────────────────────────────────────────


def _fetch_github(months: int) -> list[dict[str, Any]]:
    results = []
    token = os.getenv("GITHUB_TOKEN")
    org = os.getenv("GH_ORG")
    repo = os.getenv("GH_REPO")

    if not token:
        return [{"provider": "GitHub", "error": "GITHUB_TOKEN not set"}]

    try:
        import json as _json
        import urllib.request

        headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }

        def _get(url: str) -> dict:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=15) as resp:
                return _json.loads(resp.read())

        if org:
            # Organization: Enhanced Billing API → 旧 API フォールバック
            today = date.today()
            try:
                data = _get(
                    f"https://api.github.com/orgs/{org}/billing/usage"
                    f"?year={today.year}&month={today.month:02d}"
                )
                items = data.get("usageItems", [])
                actions_cost = sum(
                    float(i.get("totalCost", 0))
                    for i in items
                    if "Actions" in i.get("product", "")
                )
                results.append(
                    {
                        "provider": "GitHub Actions",
                        "period": today.strftime("%Y-%m"),
                        "cost_usd": round(actions_cost, 4),
                        "note": f"Enhanced Billing (org: {org})",
                    }
                )
            except Exception:
                try:
                    data = _get(
                        f"https://api.github.com/orgs/{org}/settings/billing/actions"
                    )
                    included = data.get("included_minutes", 0)
                    used = data.get("total_minutes_used", 0)
                    paid = data.get("total_paid_minutes_used", 0)
                    results.append(
                        {
                            "provider": "GitHub Actions",
                            "period": today.strftime("%Y-%m"),
                            "minutes_included": included,
                            "minutes_used": used,
                            "minutes_paid": paid,
                            "cost_usd": round(paid * 0.008, 4),
                            "note": "Linux rate ($0.008/min)",
                        }
                    )
                except Exception as exc2:
                    results.append(
                        {
                            "provider": "GitHub Actions",
                            "error": f"billing unavailable: {exc2}",
                        }
                    )
        elif repo and "/" in repo:
            # 個人リポジトリ: 旧 Billing API 廃止 → キャッシュ + ラン数
            today = date.today()
            owner, repo_name = repo.split("/", 1)
            try:
                cache_data = _get(
                    f"https://api.github.com/repos/{owner}/{repo_name}/actions/cache/usage"
                )
                cache_gb = round(
                    cache_data.get("active_caches_size_in_bytes", 0) / 1_073_741_824, 2
                )
                first_of_month = today.replace(day=1).isoformat()
                runs_data = _get(
                    f"https://api.github.com/repos/{owner}/{repo_name}/actions/runs"
                    f"?per_page=1&created=>={first_of_month}"
                )
                run_count = runs_data.get("total_count", 0)
                results.append(
                    {
                        "provider": "GitHub Actions",
                        "period": today.strftime("%Y-%m"),
                        "cost_usd": None,
                        "note": f"{run_count} runs, cache {cache_gb} GB "
                        "(billing API deprecated — check github.com/settings/billing)",
                    }
                )
            except Exception as exc2:
                results.append({"provider": "GitHub Actions", "error": str(exc2)})
        else:
            results.append(
                {
                    "provider": "GitHub",
                    "error": "Set GH_ORG or GH_REPO (owner/repo) env var",
                }
            )
    except Exception as exc:
        results.append({"provider": "GitHub", "error": str(exc)})
    return results


# ─────────────────────────────────────────────
# 表示
# ─────────────────────────────────────────────


def _table(all_results: list[dict]) -> None:
    """結果をターミナル向けテーブルで出力する。"""
    RESET = "\033[0m"
    BOLD = "\033[1m"
    CYAN = "\033[36m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    RED = "\033[31m"

    def colored(text: str, color: str) -> str:
        if sys.stdout.isatty():
            return f"{color}{text}{RESET}"
        return text

    # ヘッダー
    print()
    print(colored(" ★ Multi-Cloud Cost Report ", BOLD + CYAN))
    print(colored("─" * 60, CYAN))
    print(colored(f"{'Provider':<22} {'Period':<10} {'Cost':>14}  Note", BOLD))
    print(colored("─" * 60, CYAN))

    total = 0.0
    jpy_total = 0.0
    for row in all_results:
        provider = row.get("provider", "")
        error = row.get("error")
        if error:
            print(
                f"{'  ' + provider:<22} {'':10} {'':12}  {colored('ERROR: ' + error, RED)}"
            )
            continue
        period = row.get("period", "")
        cost = row.get("cost_usd")
        currency = row.get("currency", "USD")
        cost_local = row.get("cost_local")
        note = row.get("note", "")
        minutes = row.get("minutes_used")
        # 表示用コスト文字列
        if cost_local is not None and currency != "USD":
            sym = "¥" if currency == "JPY" else currency + " "
            fmt = f"{int(cost_local):,}" if currency == "JPY" else f"{cost_local:.2f}"
            cost_str = colored(f"{sym}{fmt} ({currency})", YELLOW)
            if currency == "JPY":
                jpy_total += cost_local
        elif cost is None and cost_local is None:
            cost_str = colored("     N/A", YELLOW)
        else:
            val = cost if cost is not None else 0.0
            cost_str = colored(f"{val:>12.4f}", GREEN if val < 10 else YELLOW)
            total += val
        extra = ""
        if minutes is not None:
            extra = f"  {minutes} min used"
        print(f"{'  ' + provider:<22} {period:<10} {cost_str}  {note}{extra}")

    print(colored("─" * 60, CYAN))
    print(colored(f"{'  TOTAL USD':<22} {'':10} {total:>14.4f}", BOLD + GREEN))
    if jpy_total > 0:
        print(colored(f"{'  TOTAL JPY':<22} {'':10} {f'¥{int(jpy_total):,}':>14}  (円建ての請求)", BOLD + YELLOW))
    print()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Multi-cloud cost report (AWS / Azure / GCP / GitHub)"
    )
    parser.add_argument(
        "--months", type=int, default=3, help="過去 N ヶ月分を表示 (デフォルト: 3)"
    )
    parser.add_argument(
        "--json", action="store_true", dest="output_json", help="JSON 形式で出力"
    )
    parser.add_argument("--aws-only", action="store_true", help="AWS のみ取得")
    parser.add_argument("--azure-only", action="store_true", help="Azure のみ取得")
    parser.add_argument("--gcp-only", action="store_true", help="GCP のみ取得")
    parser.add_argument("--github-only", action="store_true", help="GitHub のみ取得")
    args = parser.parse_args()

    only_flags = [args.aws_only, args.azure_only, args.gcp_only, args.github_only]
    fetch_all = not any(only_flags)

    all_results: list[dict] = []
    if fetch_all or args.aws_only:
        all_results.extend(_fetch_aws(args.months))
    if fetch_all or args.azure_only:
        all_results.extend(_fetch_azure(args.months))
    if fetch_all or args.gcp_only:
        all_results.extend(_fetch_gcp(args.months))
    if fetch_all or args.github_only:
        all_results.extend(_fetch_github(args.months))

    if args.output_json:
        print(json.dumps(all_results, ensure_ascii=False, indent=2))
    else:
        _table(all_results)


if __name__ == "__main__":
    main()
