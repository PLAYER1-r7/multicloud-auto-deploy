#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON_BIN="$ROOT_DIR/.venv/bin/python"

if [[ ! -x "$PYTHON_BIN" ]]; then
  echo "Python venv not found at $PYTHON_BIN" >&2
  exit 1
fi

"$PYTHON_BIN" "$ROOT_DIR/scripts/cloud_architecture_mapper.py" all \
  --environment "${1:-staging}" \
  --snapshot-output "$ROOT_DIR/docs/generated/architecture/snapshot.json" \
  --diagram-output "$ROOT_DIR/docs/generated/architecture/architecture.mmd" \
  --validate

echo "Architecture snapshot and diagram refreshed."
