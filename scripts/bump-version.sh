#!/usr/bin/env bash
# ============================================================
# bump-version.sh — バージョン管理スクリプト
#
# 使用方法:
#   ./scripts/bump-version.sh show                        # 現在のバージョン一覧を表示
#   ./scripts/bump-version.sh patch  all                  # 全コンポーネントのパッチ(Z)を+1
#   ./scripts/bump-version.sh patch  simple-sns           # 指定コンポーネントのみ
#   ./scripts/bump-version.sh minor  all                  # マイナー(Y)を+1 → Zはリセット
#   ./scripts/bump-version.sh major  all                  # メジャー(X)を+1 手動実行専用
#   ./scripts/bump-version.sh major  aws-static-site      # 指定コンポーネントのみ
#   ./scripts/bump-version.sh azure-afd-resolved          # Azure AFD 解消後: 0.9.x → 1.0.0
#
# コンポーネント名:
#   aws-static-site   azure-static-site   gcp-static-site   simple-sns
#
# バージョン規則:
#   X.Y.Z
#   X: 手動指示で+1
#   Y: プッシュ (GitHub Actions) で+1 → Zリセット
#   Z: コミット (pre-commit hook) で+1
#
# 初期バージョン:
#   aws-static-site   1.0.0
#   azure-static-site 0.9.0  ← AFD 502 未解消のため
#   gcp-static-site   1.0.0
#   simple-sns        1.0.0
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
major, minor, patch = int(parts[0]), int(parts[1]), int(parts[2])

if bump_type == "major":
    major += 1; minor = 0; patch = 0
elif bump_type == "minor":
    minor += 1; patch = 0
elif bump_type == "patch":
    patch += 1
else:
    print(f"ERROR: unknown bump type '{bump_type}'", file=sys.stderr)
    sys.exit(1)

new_version = f"{major}.{minor}.{patch}"
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

print("=" * 55)
print(f"{'Component':<22} {'Version':<10} {'Status':<8}")
print("-" * 55)
for name, info in data.items():
    print(f"  {name:<20} {info['version']:<10} {info.get('status','')}")
print("=" * 55)
PYEOF
}

# ===== メイン処理 =====

BUMP_TYPE="${1:-show}"
TARGET="${2:-}"

case "$BUMP_TYPE" in
  show|status)
    python_show
    ;;

  patch|minor|major)
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

  azure-afd-resolved)
    # Azure AFD 502 問題解消後に呼び出す特別コマンド
    # 現在の azure-static-site バージョンを 1.0.0 にリセット
    echo "🎉 Azure AFD 解消: azure-static-site を 1.0.0 へ昇格"
    python_set_version "azure-static-site" "1.0.0"
    python_show
    echo ""
    echo "⚠️  次の手順で反映してください:"
    echo "   git add versions.json"
    echo "   git commit -m 'chore: upgrade azure-static-site to 1.0.0 (AFD resolved) [skip-version-bump]'"
    echo "   git push"
    ;;

  *)
    cat <<EOF
使用方法: $0 <コマンド> [コンポーネント]

コマンド:
  show                          現在のバージョン一覧
  patch   <component|all>       Z を +1 (コミット時に自動実行)
  minor   <component|all>       Y を +1、Z リセット (push 時に GitHub Actions が実行)
  major   <component|all>       X を +1、Y/Z リセット (手動実行)
  azure-afd-resolved            Azure AFD 解消時: 0.9.x → 1.0.0

コンポーネント:
  aws-static-site   azure-static-site   gcp-static-site   simple-sns   all

例:
  $0 show
  $0 patch all
  $0 major aws-static-site
  $0 azure-afd-resolved
EOF
    exit 1
    ;;
esac
