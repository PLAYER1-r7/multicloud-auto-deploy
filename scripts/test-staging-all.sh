#!/usr/bin/env bash
# ================================================================
# test-staging-all.sh — Compatibility wrapper (deprecated)
# ================================================================
#
# 旧オーケストレーター。実装重複を避けるため、現在は
# scripts/test-sns-all.sh へ処理を委譲する。
#
# 互換オプション:
#   --clouds aws,azure,gcp  (そのまま委譲)
#   --quick                 (そのまま委譲)
#   --aws-token/--azure-token/--gcp-token
#   --env/--read-only/--write/--verbose/--skip-cleanup
#
# 例:
#   ./scripts/test-staging-all.sh --quick
#   ./scripts/test-staging-all.sh --clouds aws,gcp --aws-token ... --gcp-token ...
# ================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TARGET_SCRIPT="$SCRIPT_DIR/test-sns-all.sh"

if [[ ! -f "$TARGET_SCRIPT" ]]; then
  echo "ERROR: target script not found: $TARGET_SCRIPT" >&2
  exit 2
fi

args=()

while [[ $# -gt 0 ]]; do
  case "$1" in
    --clouds)
      args+=(--clouds "$2")
      shift 2
      ;;
    --quick|--aws-token|--azure-token|--gcp-token|--env|-e|--read-only|-r|--write|--verbose|-v|--skip-cleanup|-s)
      if [[ "$1" == "--aws-token" || "$1" == "--azure-token" || "$1" == "--gcp-token" || "$1" == "--env" || "$1" == "-e" ]]; then
        args+=("$1" "$2")
        shift 2
      else
        args+=("$1")
        shift
      fi
      ;;
    -h|--help)
      echo "[DEPRECATED] test-staging-all.sh は test-sns-all.sh に統合されました。"
      echo
      "$TARGET_SCRIPT" --help
      exit 0
      ;;
    *)
      echo "Unknown option: $1" >&2
      echo "Run: $TARGET_SCRIPT --help" >&2
      exit 1
      ;;
  esac
done

echo "[DEPRECATED] test-staging-all.sh は互換ラッパーです。test-sns-all.sh を直接利用してください。" >&2
exec "$TARGET_SCRIPT" "${args[@]}"
