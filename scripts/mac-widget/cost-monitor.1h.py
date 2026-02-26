#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# <xbar.title>Multi-Cloud Cost Monitor</xbar.title>
# <xbar.version>1.2</xbar.version>
# <xbar.author>multicloud-auto-deploy</xbar.author>
# <xbar.author.github>PLAYER1-r7</xbar.author.github>
# <xbar.desc>AWS / Azure / GCP / GitHub Actions のコスト当月分をメニューバーに表示</xbar.desc>
# <xbar.dependencies>python3,boto3</xbar.dependencies>
# <xbar.abouturl>https://github.com/PLAYER1-r7/multicloud-auto-deploy</xbar.abouturl>
#
# ── セットアップ ──────────────────────────────────────────────
# 1. xbar をインストール: https://xbarapp.com
# 2. このファイルを xbar の plugins フォルダに置く:
#      install.sh を実行するか、手動でシンボリックリンクを作成
#      ln -s $(pwd)/scripts/mac-widget/cost-monitor.1h.py \
#            ~/Library/Application\ Support/xbar/plugins/cost-monitor.1h.py
# 3. 同じフォルダに .env を作成 (cost-monitor.env.sample を参考に)
# 4. xbar > Preferences > Refresh All
# ─────────────────────────────────────────────────────────────

from __future__ import annotations

# ── venv ブートストラップ (install.sh が作成した .venv を sys.path に追加) ──
import os as _os
import sys as _sys

_WIDGET_DIR = _os.path.dirname(_os.path.realpath(__file__))
_VENV_LIB = _os.path.join(_WIDGET_DIR, ".venv", "lib")
if _os.path.isdir(_VENV_LIB):
    for _d in _os.listdir(_VENV_LIB):
        _sp = _os.path.join(_VENV_LIB, _d, "site-packages")
        if _os.path.isdir(_sp) and _sp not in _sys.path:
            _sys.path.insert(0, _sp)
            break
# ─────────────────────────────────────────────────────────────

import json
import os
import subprocess
import urllib.request
from datetime import date, timedelta
from pathlib import Path
from typing import Any

# ── 設定ファイル読み込み (.env を同ディレクトリから探す) ─────
_HERE = Path(__file__).resolve().parent


def _load_dotenv() -> None:
    """簡易 .env ローダー (python-dotenv 不要)。"""
    env_path = _HERE / ".env"
    if not env_path.exists():
        return
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, val = line.partition("=")
        key = key.strip()
        val = val.strip().strip("\"'")
        os.environ.setdefault(key, val)


_load_dotenv()

# ── 月の範囲計算 ─────────────────────────────────────────────


def _this_month() -> tuple[str, str]:
    """当月の (start, end) を返す (YYYY-MM-DD)。"""
    today = date.today()
    start = today.replace(day=1)
    next_month = start.month + 1
    next_year = start.year
    if next_month > 12:
        next_month = 1
        next_year += 1
    end = date(next_year, next_month, 1) - timedelta(days=1)
    return start.strftime("%Y-%m-%d"), end.strftime("%Y-%m-%d")


# ── 各クラウドのコスト取得 ────────────────────────────────────


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


def _fetch_aws() -> dict[str, Any]:
    try:
        import boto3

        ce = boto3.client("ce", region_name="us-east-1")
        start, end = _this_month()
        resp = ce.get_cost_and_usage(
            TimePeriod={"Start": start, "End": end},
            Granularity="MONTHLY",
            Metrics=["UnblendedCost"],
        )
        usd_total = sum(
            float(r["Total"]["UnblendedCost"]["Amount"]) for r in resp["ResultsByTime"]
        )
        rate = _get_usd_jpy_rate()
        jpy_total = round(usd_total * rate)
        return {
            "cost": jpy_total,
            "currency": "JPY",
            "usd": round(usd_total, 2),
            "rate": round(rate, 2),
            "period": start[:7],
        }
    except ImportError:
        return {"error": "boto3 not installed"}
    except Exception as e:
        return {"error": str(e)[:80]}


def _fetch_azure() -> dict[str, Any]:
    sub = os.getenv("AZURE_SUBSCRIPTION_ID")
    if not sub:
        return {"error": "AZURE_SUBSCRIPTION_ID not set"}
    try:
        r = subprocess.run(
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
            timeout=20,
        )
        if r.returncode != 0:
            return {"error": "az login required"}
        token = json.loads(r.stdout)["accessToken"]

        start, end = _this_month()
        url = (
            f"https://management.azure.com/subscriptions/{sub}"
            f"/providers/Microsoft.CostManagement/query?api-version=2023-11-01"
        )
        body = json.dumps(
            {
                "type": "ActualCost",
                "dataSet": {
                    "granularity": "Monthly",
                    "aggregation": {"totalCost": {"name": "Cost", "function": "Sum"}},
                },
                "timeframe": "Custom",
                "timePeriod": {"from": start + "T00:00:00Z", "to": end + "T23:59:59Z"},
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
        with urllib.request.urlopen(req, timeout=20) as resp:
            data = json.loads(resp.read())

        rows = data.get("properties", {}).get("rows", [])
        total = sum(float(row[0]) for row in rows if row)
        currency = rows[0][2] if rows and len(rows[0]) > 2 else "USD"
        return {"cost": round(total, 2), "currency": currency, "period": start[:7]}
    except Exception as e:
        return {"error": str(e)[:80]}


def _fetch_gcp() -> dict[str, Any]:
    """GCP Cloud Billing — BigQuery export なしでの概算取得。"""
    billing_account = os.getenv("GCP_BILLING_ACCOUNT")
    project_id = os.getenv("GCP_PROJECT_ID")
    if not billing_account and not project_id:
        return {"error": "GCP_BILLING_ACCOUNT or GCP_PROJECT_ID not set"}
    try:
        start, _end = _this_month()
        # Cloud Billing v1 で当月の SKU コストを集計
        token_r = subprocess.run(
            ["gcloud", "auth", "print-access-token"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if token_r.returncode != 0:
            return {"error": "gcloud auth login required"}
        token = token_r.stdout.strip()

        if billing_account:
            # Billing Account Budget API (コスト取得にはBigQuery exportが正式)
            # → budgets describe で threshold alerts から概算を拾う
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
                timeout=15,
            )
            if cmd.returncode == 0:
                info = json.loads(cmd.stdout)
                return {
                    "cost": None,
                    "period": start[:7],
                    "note": info.get("displayName", billing_account),
                    "url": f"https://console.cloud.google.com/billing/{billing_account}",
                }
        return {"error": "Use GCP Console for exact cost", "period": start[:7]}
    except Exception as e:
        return {"error": str(e)[:80]}


def _fetch_github() -> dict[str, Any]:
    token = os.getenv("GITHUB_TOKEN")
    org = os.getenv("GH_ORG")
    repo = os.getenv("GH_REPO")
    if not token:
        return {"error": "GITHUB_TOKEN not set"}
    try:
        headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }

        def _get(url: str) -> dict:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=15) as resp:
                return json.loads(resp.read())

        period = date.today().strftime("%Y-%m")
        today = date.today()

        # ── Organization: Enhanced Billing API → 旧 API フォールバック ───
        if org:
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
                return {"cost": round(actions_cost, 4), "period": period}
            except Exception:
                pass
            try:
                data = _get(
                    f"https://api.github.com/orgs/{org}/settings/billing/actions"
                )
                included = data.get("included_minutes", 0)
                used = data.get("total_minutes_used", 0)
                return {
                    "cost": round(max(0, used - included) * 0.008, 4),
                    "minutes_used": used,
                    "minutes_included": included,
                    "period": period,
                }
            except Exception:
                pass
            return {
                "error": f"GitHub billing unavailable for org: {org}",
                "period": period,
            }

        # ── リポジトリ / 個人: 旧 Billing API 廃止 → キャッシュ + ラン数で代替 ───
        if repo and "/" in repo:
            owner, repo_name = repo.split("/", 1)
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
            return {
                "cost": None,
                "period": period,
                "cache_gb": cache_gb,
                "run_count": run_count,
            }

        return {"error": "Set GH_ORG or GH_REPO env var"}
    except Exception as e:
        return {"error": str(e)[:80]}


# ── xbar 出力フォーマット ─────────────────────────────────────

ICONS = {
    "AWS": "🟠",
    "Azure": "🔵",
    "GCP": "🟡",
    "GitHub": "⚫",
}

CONSOLES = {
    "AWS": "https://console.aws.amazon.com/cost-management/home#/dashboard",
    "Azure": "https://portal.azure.com/#view/Microsoft_Azure_CostManagement/Menu/~/overview",
    "GCP": "https://console.cloud.google.com/billing",
    "GitHub": "https://github.com/settings/billing",
}


def _color(cost: float | None) -> str:
    if cost is None:
        return "gray"
    if cost < 5:
        return "green"
    if cost < 30:
        return "#f5a623"  # orange
    return "red"


def _fmt_cost(cost: float | None, currency: str = "USD") -> str:
    if cost is None:
        return "N/A"
    if currency == "JPY":
        return f"¥{int(cost):,}"
    return f"${cost:.2f}"


def main() -> None:
    aws = _fetch_aws()
    azure = _fetch_azure()
    gcp = _fetch_gcp()
    github = _fetch_github()

    results = {"AWS": aws, "Azure": azure, "GCP": gcp, "GitHub": github}

    # メニューバータイトル — USD のみ合計、JPY は別途表示
    usd_total = sum(
        r["cost"]
        for r in results.values()
        if isinstance(r.get("cost"), (int, float)) and r.get("currency", "USD") == "USD"
    )
    jpy_total = sum(
        r["cost"]
        for r in results.values()
        if isinstance(r.get("cost"), (int, float)) and r.get("currency") == "JPY"
    )
    has_error = any("error" in r for r in results.values())
    bar_icon = "☁" if not has_error else "☁⚠"
    bar_parts = []
    if usd_total:
        bar_parts.append(f"${usd_total:.2f}")
    if jpy_total:
        bar_parts.append(f"¥{int(jpy_total):,}")
    bar_label = " + ".join(bar_parts) if bar_parts else "$0.00"
    bar_color = _color(usd_total + jpy_total / 150)  # JPY→USD 概算で色判定
    print(f"{bar_icon} {bar_label} | color={bar_color} font=Menlo size=13")
    print("---")

    # 当月
    period = date.today().strftime("%Y-%m")
    print(f"📅 {period} コスト内訳 | size=12 color=gray")
    print("---")

    for name, r in results.items():
        icon = ICONS[name]
        console_url = CONSOLES[name]
        if "error" in r:
            print(f"{icon} {name}  ⚠ {r['error']} | color=red size=12")
            print(f"  → コンソールを開く | href={console_url} color=gray size=11")
        else:
            cost = r.get("cost")
            currency = r.get("currency", "USD")
            cost_str = _fmt_cost(cost, currency)
            color = _color(cost)
            extra = ""
            if name == "AWS" and "usd" in r:
                extra = f"  (${r['usd']:.2f} × ¥{r['rate']:.0f})"
            elif name == "GitHub" and "minutes_used" in r:
                extra = f"  ({r['minutes_used']} min / {r['minutes_included']} free)"
            elif name == "GitHub" and "run_count" in r:
                # 旧 Billing API 廃止のため代替情報を表示
                cache_gb = r.get("cache_gb", 0)
                run_count = r.get("run_count", 0)
                extra = f"  {run_count} runs / cache {cache_gb} GB"
                cost_str = "  N/A"
                color = "gray"
            if name == "GCP" and r.get("note"):
                extra = f"  [{r['note']}]"
            print(
                f"{icon} {name}  {cost_str}{extra} | color={color} size=13 font=Menlo href={console_url}"
            )

    print("---")
    gcp_url = gcp.get("url", CONSOLES["GCP"])
    # 通貨別に合計を計算
    usd_sum = sum(
        r["cost"]
        for r in results.values()
        if isinstance(r.get("cost"), (int, float)) and r.get("currency", "USD") == "USD"
    )
    jpy_sum = sum(
        r["cost"]
        for r in results.values()
        if isinstance(r.get("cost"), (int, float)) and r.get("currency") == "JPY"
    )
    total_parts = []
    if usd_sum:
        total_parts.append(f"${usd_sum:.2f}")
    if jpy_sum:
        total_parts.append(f"¥{int(jpy_sum):,}")
    total_label = "  +  ".join(total_parts) if total_parts else "$0.00"
    print(f"TOTAL  {total_label} | color=white font=Menlo size=14")
    print("---")

    # クイックリンク
    print("🔗 コンソールリンク | size=11 color=gray")
    print(f"  AWS Cost Explorer | href={CONSOLES['AWS']} size=12")
    print(f"  Azure Cost Management | href={CONSOLES['Azure']} size=12")
    print(f"  GCP Billing | href={gcp_url} size=12")
    print(f"  GitHub Billing | href={CONSOLES['GitHub']} size=12")
    print("---")

    # アクション
    script = str(_HERE / "cost-monitor.1h.py")
    print("🔄 今すぐ更新 | refresh=true size=12")
    print(
        f"💻 ターミナルでフルレポート | bash=python3 param1={script} terminal=true size=12"
    )
    print(
        f"⚙️ .env を編集 | bash=open param1=-e param2={str(_HERE / '.env')} terminal=false size=12"
    )

    now = date.today().strftime("%Y-%m-%d")
    print("---")
    print(f"最終更新: {now} | size=10 color=gray")


if __name__ == "__main__":
    main()
