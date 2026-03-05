#!/usr/bin/env bash
set -euo pipefail

# ワークフローをトリガーして承認待ち状態を自動検知するスクリプト
# Usage: ./deploy-with-approval-check.sh <workflow-file> <ref> <environment>
# Example: ./deploy-with-approval-check.sh deploy-sns-azure.yml develop production

WORKFLOW="${1:-}"
REF="${2:-develop}"
ENVIRONMENT="${3:-production}"

if [[ -z "$WORKFLOW" ]]; then
  echo "Usage: $0 <workflow-file> [ref] [environment]" >&2
  echo "Example: $0 deploy-sns-azure.yml develop production" >&2
  exit 1
fi

if ! command -v gh >/dev/null 2>&1; then
  echo "Error: gh CLI is required" >&2
  exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "=== Triggering Workflow ===" 
echo "Workflow: $WORKFLOW"
echo "Ref: $REF"
echo "Environment: $ENVIRONMENT"
echo ""

# ワークフローをトリガー
gh workflow run "$WORKFLOW" --ref "$REF" --field environment="$ENVIRONMENT"

echo "✓ Workflow triggered"
echo ""
echo "Waiting for workflow to appear in run list..."
sleep 5

# 最新のワークフロー実行IDを取得
RUN_ID=$(gh run list --workflow="$WORKFLOW" --branch="$REF" --limit=1 --json databaseId --jq '.[0].databaseId')

if [[ -z "$RUN_ID" ]]; then
  echo "Error: Could not find workflow run" >&2
  exit 1
fi

echo "✓ Workflow Run ID: $RUN_ID"
echo "  URL: https://github.com/$(gh repo view --json nameWithOwner -q .nameWithOwner)/actions/runs/$RUN_ID"
echo ""

# 承認待ち状態をチェック
if [[ -f "$SCRIPT_DIR/check-workflow-approval.sh" ]]; then
  exec "$SCRIPT_DIR/check-workflow-approval.sh" "$RUN_ID"
else
  echo "Warning: check-workflow-approval.sh not found, skipping approval check" >&2
  echo "Monitor manually: https://github.com/$(gh repo view --json nameWithOwner -q .nameWithOwner)/actions/runs/$RUN_ID"
  exit 0
fi
