#!/usr/bin/env bash
set -euo pipefail

# ワークフローの承認待ち状態を検知して通知するスクリプト
# Usage: ./check-workflow-approval.sh <run-id>
# Example: ./check-workflow-approval.sh 22717403730

RUN_ID="${1:-}"
POLL_INTERVAL=30  # 秒
MAX_WAIT=600      # 最大待機時間（秒）

if [[ -z "$RUN_ID" ]]; then
  echo "Usage: $0 <run-id>" >&2
  echo "Example: $0 22717403730" >&2
  exit 1
fi

if ! command -v gh >/dev/null 2>&1; then
  echo "Error: gh CLI is required" >&2
  exit 1
fi

echo "=== Workflow Approval Monitor ===" 
echo "Run ID: $RUN_ID"
echo ""

check_approval_status() {
  local run_id="$1"
  
  # ワークフローのステータスを取得
  local status_json
  status_json=$(gh run view "$run_id" --json status,conclusion,displayTitle,url,createdAt 2>&1)
  
  local status
  status=$(echo "$status_json" | jq -r '.status // empty')
  
  local conclusion
  conclusion=$(echo "$status_json" | jq -r '.conclusion // empty')
  
  local url
  url=$(echo "$status_json" | jq -r '.url // empty')
  
  local title
  title=$(echo "$status_json" | jq -r '.displayTitle // empty')
  
  echo "[$(date '+%H:%M:%S')] Workflow: $title"
  echo "  Status: $status"
  
  # 承認待ち状態の検知
  if [[ "$status" == "waiting" || "$status" == "queued" ]]; then
    echo ""
    echo "⏳ このワークフローは承認待ちの可能性があります"
    echo ""
    echo "📋 承認が必要な場合は以下のURLから承認してください:"
    echo "   $url"
    echo ""
    echo "🔑 承認方法:"
    echo "   1. 上記のURLをブラウザで開く"
    echo "   2. 'Review deployments' ボタンをクリック"
    echo "   3. 環境を選択して 'Approve and deploy' をクリック"
    echo ""
    return 2  # 承認待ち
  elif [[ "$status" == "in_progress" ]]; then
    echo "  ✓ ワークフローは実行中です"
    return 0  # 実行中
  elif [[ "$status" == "completed" ]]; then
    if [[ "$conclusion" == "success" ]]; then
      echo "  ✓ ワークフローが正常に完了しました"
      return 0
    else
      echo "  ✗ ワークフローが失敗しました (conclusion: $conclusion)"
      echo "  詳細: $url"
      return 1
    fi
  else
    echo "  Unknown status: $status"
    return 3
  fi
}

# 初回チェック
check_approval_status "$RUN_ID"
result=$?

if [[ $result -eq 2 ]]; then
  echo "=== 承認待機モード ===" 
  echo "承認されるまで ${MAX_WAIT} 秒間待機します..."
  echo "(Ctrl+C で中断)"
  echo ""
  
  elapsed=0
  while [[ $elapsed -lt $MAX_WAIT ]]; do
    sleep "$POLL_INTERVAL"
    elapsed=$((elapsed + POLL_INTERVAL))
    
    echo ""
    check_approval_status "$RUN_ID"
    result=$?
    
    if [[ $result -ne 2 ]]; then
      echo ""
      echo "✓ 承認待ち状態が解消されました"
      break
    fi
    
    echo "  経過時間: ${elapsed}秒 / ${MAX_WAIT}秒"
  done
  
  if [[ $elapsed -ge $MAX_WAIT ]]; then
    echo ""
    echo "⚠ タイムアウト: ${MAX_WAIT}秒経過しました"
    echo "  手動で承認を確認してください: $(gh run view "$RUN_ID" --json url -q '.url')"
    exit 1
  fi
fi

exit $result
