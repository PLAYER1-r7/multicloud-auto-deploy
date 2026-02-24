#!/usr/bin/env bash
# ============================================================
# bump-version.sh — バージョン管理スクリプト (4桁スキーム)
#
# 使用方法:
#   ./scripts/bump-version.sh show                        # 現在のバージョン一覧を表示
#   ./scripts/bump-version.sh commit all                  # D (+1) ← pre-commit hook が自動実行
#   ./scripts/bump-version.sh commit simple-sns           # 指定コンポーネントのみ
#   ./scripts/bump-version.sh push   all                  # C (+1) ← GitHub Actions が push 時に自動実行
#   ./scripts/bump-version.sh minor  all                  # B (+1) ← 手動指示で実行
#   ./scripts/bump-version.sh major  all                  # A (+1) ← 手動指示で実行
#   ./scripts/bump-version.sh set    all   1.0.84.203     # バージョンを直接設定
#
# コンポーネント名:
#   aws-static-site   azure-static-site   gcp-static-site   simple-sns
#
# バージョン規則: A.B.C.D
#   A: 手動指示で+1 (B/C/D は変化しない)
#   B: 手動指示で+1 (A/C/D は変化しない)
#   C: リモートプッシュのたびに+1 (GitHub Actions) (A/B/D は変化しない / リセットなし)
#   D: developへのコミットのたびに+1 (pre-commit hook) (A/B/C は変化しない / リセットなし)
#
# ※ すべての桁は他の桁が増えてもリセットしない
# ============================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VERSIONS_FILE="${SCRIPT_DIR}/../versions.json"

COMPONENTS=(aws-static-site azure-static-site gcp-static-site simple-sns)

# --- Python で JSON を操作 ---
python_bump() {
  python3 - "$VERSIONS_FILE" "$1" "$2" <<'PYEOF'
import sys
import json

versions_file = sys.argv[1]
component     = sys.argv[2]
bump_type     = sys.argv[3]

with open(versions_file, "r") as f:
    data = json.load(f)

if component not in data:
    print(f"ERROR: unknown component '{component}'", file=sys.stderr)
    sys.exit(1)

current = data[component]["version"]
parts   = current.split(".")
if len(parts) != 4:
    print(f"ERROR: version '{current}' is not 4-digit format (A.B.C.D)", file=sys.stderr)
    sys.exit(1)

a, b, c, d = int(parts[0]), int(parts[1]), int(parts[2]), int(parts[3])

# ※ どの桁を上げても他の桁はリセットしない
if   bump_type == "major":  a += 1
elif bump_type == "minor":  b += 1
elif bump_type == "push":   c += 1
elif bump_type == "commit": d += 1
else:
    print(f"ERROR: unknown bump type '{bump_type}'", file=sys.stderr)
    sys.exit(1)

new_version = f"{a}.{b}.{c}.{d}"
data[component]["version"] = new_version

with open(versions_file, "w") as f:
    json.dump(data, f, ensure_ascii=False, indent=2)
    f.write("\n")

print(f"  {component}: {current} → {new_version}")
PYEOF
}

python_set_version() {
  python3 - "$VERSIONS_FILE" "$1" "$2" <<'PYEOF'
import sys
import json

versions_file = sys.argv[1]
component     = sys.argv[2]
new_version   = sys.argv[3]

with open(versions_file, "r") as f:
    data = json.load(f)

old_version = data[component]["version"]
data[component]["version"] = new_version

# Azure AFD 解消時はメモを更新
if component == "azure-static-site":
    data[component]["status"] = "stable"
    data[component]["note"]   = "AFD 502 解消済み。1.0.0 へ昇格。"

with open(versions_file, "w") as f:
    json.dump(data, f, ensure_ascii=False, indent=2)
    f.write("\n")

print(f"  {component}: {old_version} → {new_version}")
PYEOF
}

python_show() {
  python3 - "$VERSIONS_FILE" <<'PYEOF'
import sys
import json

with open(sys.argv[1], "r") as f:
    data = json.load(f)

print("=" * 60)
print(f"{'Component':<22} {'Version (A.B.C.D)':<18} {'Status':<8}")
print("-" * 60)
for name, info in data.items():
    print(f"  {name:<20} {info['version']:<18} {info.get('status','')}")
print("=" * 60)
PYEOF
}

# ===== メイン処理 =====

BUMP_TYPE="${1:-show}"
TARGET="${2:-}"

case "$BUMP_TYPE" in
  show|status)
    python_show
    ;;

  commit|push|minor|major)
    if [[ -z "$TARGET" ]]; then
      echo "ERROR: コンポーネントを指定してください。例: $0 $BUMP_TYPE all"
      exit 1
    fi
    echo "🔖 bump $BUMP_TYPE: ${TARGET}"
    if [[ "$TARGET" == "all" ]]; then
      for comp in "${COMPONENTS[@]}"; do
        python_bump "$comp" "$BUMP_TYPE"
      done
    else
      python_bump "$TARGET" "$BUMP_TYPE"
    fi
    python_show
    ;;

  set)
    if [[ -z "$TARGET" || -z "${3:-}" ]]; then
      echo "ERROR: コンポーネントとバージョンを指定してください。例: $0 set all 1.0.84.203"
      exit 1
    fi
    NEW_VER="${3}"
    echo "🔖 set version: ${TARGET} → ${NEW_VER}"
    if [[ "$TARGET" == "all" ]]; then
      for comp in "${COMPONENTS[@]}"; do
        python_set_version "$comp" "$NEW_VER"
      done
    else
      python_set_version "$TARGET" "$NEW_VER"
    fi
    python_show
    ;;

  *)
    cat <<EOF
使用方法: $0 <コマンド> [コンポーネント]

コマンド:
  show                          現在のバージョン一覧
  commit  <component|all>       D (+1) ← pre-commit hook が自動実行
  push    <component|all>       C (+1) ← GitHub Actions が push 時に自動実行
  minor   <component|all>       B (+1) ← 手動指示で実行
  major   <component|all>       A (+1) ← 手動指示で実行
  set     <component|all> <ver> バージョンを直接設定 (A.B.C.D)

バージョン規則: A.B.C.D
  A: 手動指示で+1 (他はそのまま)
  B: 手動指示で+1 (他はそのまま)
  C: リモートプッシュのたびに+1 (他はそのまま / リセットなし)
  D: developコミットのたびに+1 (他はそのまま / リセットなし)

コンポーネント:
  aws-static-site   azure-static-site   gcp-static-site   simple-sns   all

例:
  $0 show
  $0 commit all
  $0 push all
  $0 minor all
  $0 major aws-static-site
  $0 set all 1.0.84.203
EOF
    exit 1
    ;;
esac
