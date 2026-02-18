#!/usr/bin/env bash
# =============================================================================
# デプロイパイプライン: local → staging → production
# Multi-Cloud Auto Deploy Platform
#
# 使用方法:
#   bash scripts/deploy-pipeline.sh [--skip-local] [--staging-only] [--dry-run]
#
# 流れ:
#   1. ローカルテスト (test-local-env.sh)
#   2. developブランチへコミット＆プッシュ (staging自動デプロイ)
#   3. GitHub Actions 完了待ち
#   4. staging環境テスト (test-cloud-env.sh staging)
#   5. mainブランチへマージ＆プッシュ (production自動デプロイ)
#   6. GitHub Actions 完了待ち
#   7. production環境テスト (test-cloud-env.sh production)
#   8. 結果ドキュメント出力
# =============================================================================

set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# -----------------------------------------------
# オプション解析
# -----------------------------------------------
SKIP_LOCAL=false
STAGING_ONLY=false
DRY_RUN=false

for arg in "$@"; do
    case "$arg" in
        --skip-local)   SKIP_LOCAL=true ;;
        --staging-only) STAGING_ONLY=true ;;
        --dry-run)      DRY_RUN=true ;;
    esac
done

# -----------------------------------------------
# 色付き出力
# -----------------------------------------------
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

PASS=0
FAIL=0
PIPELINE_LOG=()

log_result() {
    local status="$1" step="$2" detail="${3:-}"
    PIPELINE_LOG+=("[$status] $step${detail:+ — $detail}")
}

step_ok()   { echo -e "\n${GREEN}${BOLD}✅ $1${NC}"; log_result "OK" "$1"; ((PASS++)); }
step_fail() { echo -e "\n${RED}${BOLD}❌ $1${NC}"; log_result "FAIL" "$1" "$2"; ((FAIL++)); }
step_info() { echo -e "\n${CYAN}${BOLD}▶  $1${NC}"; }
step_warn() { echo -e "${YELLOW}⚠️  $1${NC}"; }
hr()        { echo -e "${BOLD}${CYAN}════════════════════════════════════════════════${NC}"; }

RUN_TIMESTAMP=$(date '+%Y%m%d_%H%M%S')
REPORT_FILE="$PROJECT_ROOT/docs/DEPLOY_PIPELINE_REPORT_${RUN_TIMESTAMP}.md"

hr
echo -e "${BOLD}${CYAN}  Multi-Cloud Auto Deploy — Pipeline Run${NC}"
echo -e "  $(date '+%Y-%m-%d %H:%M:%S %Z')${NC}"
echo -e "  dry-run=$DRY_RUN | skip-local=$SKIP_LOCAL | staging-only=$STAGING_ONLY"
hr

# ============================================================
# STEP 1: ローカルテスト
# ============================================================
step_info "STEP 1/7: ローカルテスト"

if [[ "$SKIP_LOCAL" == "true" ]]; then
    step_warn "--skip-local 指定のためスキップ"
    log_result "SKIP" "STEP1 ローカルテスト" "--skip-local"
else
    if bash "$SCRIPT_DIR/test-local-env.sh" > /tmp/pipeline-local.log 2>&1; then
        PASS_COUNT=$(grep -c "✅ PASS" /tmp/pipeline-local.log || echo 0)
        step_ok "STEP 1: ローカルテスト PASS ($PASS_COUNT 件)"
    else
        FAIL_COUNT=$(grep -c "❌ FAIL" /tmp/pipeline-local.log || echo 0)
        step_fail "STEP 1: ローカルテスト FAIL ($FAIL_COUNT 件失敗)" "詳細: /tmp/pipeline-local.log"
        echo -e "${RED}ローカルテストが失敗しました。パイプラインを停止します。${NC}"
        echo "--- ローカルテスト失敗ログ (最後の30行) ---"
        tail -30 /tmp/pipeline-local.log
        exit 1
    fi
fi

# ============================================================
# STEP 2: develop ブランチへコミット & プッシュ (staging)
# ============================================================
step_info "STEP 2/7: develop ブランチへコミット & プッシュ"

cd "$PROJECT_ROOT"

# 変更ファイルの確認
CHANGED=$(git status --porcelain | grep -v "^?" | wc -l || echo 0)
UNTRACKED_NEW=$(git ls-files --others --exclude-standard -- "scripts/test-local-env.sh" "scripts/test-cloud-env.sh" "scripts/deploy-pipeline.sh" "services/api/app/backends/local_backend.py" 2>/dev/null | wc -l || echo 0)

if [[ "$CHANGED" -eq 0 && "$UNTRACKED_NEW" -eq 0 ]]; then
    step_warn "コミット対象の変更なし。プッシュをスキップ。"
    log_result "SKIP" "STEP2 develop push" "変更なし"
else
    COMMIT_MSG="feat(local-env): Add local env test script and fix LocalBackend SQLite support

- scripts/test-local-env.sh: ローカル環境動作確認テストスクリプト追加
- scripts/test-cloud-env.sh: クラウド環境(staging/production)テストスクリプト追加
- scripts/deploy-pipeline.sh: デプロイパイプラインスクリプト追加
- services/api/app/backends/local_backend.py: LocalBackend バグ修正
  - get_post() / update_post() 抽象メソッド実装
  - SQLite対応: _create_tables(), _is_sqlite(), _decode_array()
  - JSON配列シリアライズ対応

Run date: $(date '+%Y-%m-%d %H:%M:%S')"

    if [[ "$DRY_RUN" == "true" ]]; then
        step_warn "[DRY-RUN] git add + commit + push origin develop をスキップ"
        log_result "DRY-RUN" "STEP2 develop push"
    else
        git add \
            scripts/test-local-env.sh \
            scripts/test-cloud-env.sh \
            scripts/deploy-pipeline.sh \
            services/api/app/backends/local_backend.py 2>/dev/null || true
        git add docs/ 2>/dev/null || true

        git commit -m "$COMMIT_MSG" > /tmp/pipeline-commit.log 2>&1 || {
            step_warn "コミット対象なし（already committed）"
        }

        if git push ashnova develop > /tmp/pipeline-push.log 2>&1; then
            step_ok "STEP 2: develop ブランチにプッシュ成功"
        else
            step_fail "STEP 2: develop プッシュ失敗" "$(cat /tmp/pipeline-push.log | tail -5)"
            exit 1
        fi
    fi
fi

# ============================================================
# STEP 3: GitHub Actions 完了待ち (staging)
# ============================================================
step_info "STEP 3/7: GitHub Actions 完了待ち (staging デプロイ)"

if [[ "$DRY_RUN" == "true" ]]; then
    step_warn "[DRY-RUN] GitHub Actions 待機をスキップ"
    log_result "DRY-RUN" "STEP3 GitHub Actions staging 待機"
else
    echo "  最新のワークフロー実行を確認中..."
    sleep 10  # Actions 起動までの待機

    # 最大15分待機
    MAX_WAIT=900
    ELAPSED=0
    INTERVAL=30

    while [[ "$ELAPSED" -lt "$MAX_WAIT" ]]; do
        # 最新の実行ステータスを取得
        RUN_STATUS=$(gh run list \
            --workflow=deploy-aws.yml \
            --branch=develop \
            --limit=1 \
            --json status,conclusion,databaseId,createdAt \
            --jq '.[0]' 2>/dev/null || echo "{}")

        STATUS=$(echo "$RUN_STATUS" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('status','unknown'))" 2>/dev/null || echo "unknown")
        CONCLUSION=$(echo "$RUN_STATUS" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('conclusion',''))" 2>/dev/null || echo "")
        RUN_ID=$(echo "$RUN_STATUS" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('databaseId',''))" 2>/dev/null || echo "")

        echo "  [${ELAPSED}s] status=$STATUS conclusion=$CONCLUSION run_id=$RUN_ID"

        if [[ "$STATUS" == "completed" ]]; then
            if [[ "$CONCLUSION" == "success" ]]; then
                step_ok "STEP 3: GitHub Actions (AWS staging) 成功 (run_id=$RUN_ID)"
                break
            elif [[ "$CONCLUSION" == "failure" || "$CONCLUSION" == "cancelled" ]]; then
                step_fail "STEP 3: GitHub Actions (AWS staging) 失敗 ($CONCLUSION)" "run_id=$RUN_ID"
                echo "  詳細: gh run view $RUN_ID"
                break
            fi
        fi

        sleep "$INTERVAL"
        ELAPSED=$((ELAPSED + INTERVAL))
    done

    if [[ "$ELAPSED" -ge "$MAX_WAIT" ]]; then
        step_warn "GitHub Actions 完了待ちタイムアウト (${MAX_WAIT}s). テストを続行します。"
        log_result "WARN" "STEP3 GitHub Actions タイムアウト"
    fi
fi

# ============================================================
# STEP 4: staging 環境テスト
# ============================================================
step_info "STEP 4/7: staging 環境テスト"

if bash "$SCRIPT_DIR/test-cloud-env.sh" staging > /tmp/pipeline-staging.log 2>&1; then
    PASS_COUNT=$(grep -c "✅ PASS" /tmp/pipeline-staging.log || echo 0)
    step_ok "STEP 4: staging テスト PASS ($PASS_COUNT 件)"
else
    FAIL_COUNT=$(grep -c "❌ FAIL" /tmp/pipeline-staging.log || echo 0)
    step_fail "STEP 4: staging テスト FAIL ($FAIL_COUNT 件失敗)" "詳細: /tmp/pipeline-staging.log"
    echo "--- staging テスト失敗ログ ---"
    tail -30 /tmp/pipeline-staging.log
    if [[ "$STAGING_ONLY" == "false" ]]; then
        echo -e "${RED}staging テスト失敗のため production デプロイを停止します。${NC}"
        exit 1
    fi
fi

if [[ "$STAGING_ONLY" == "true" ]]; then
    echo -e "\n${YELLOW}--staging-only 指定のため production へは進みません。${NC}"
    log_result "SKIP" "STEP5-7 production" "--staging-only"
    # サマリーのみ出力して終了
    hr
    echo -e "${BOLD}  パイプライン完了 (staging only)${NC}"
    echo -e "  ✅ $PASS PASS / ❌ $FAIL FAIL"
    hr
    exit $([[ "$FAIL" -eq 0 ]] && echo 0 || echo 1)
fi

# ============================================================
# STEP 5: main ブランチへマージ & プッシュ (production)
# ============================================================
step_info "STEP 5/7: main ブランチへマージ & プッシュ (production)"

if [[ "$DRY_RUN" == "true" ]]; then
    step_warn "[DRY-RUN] main ブランチへのマージ & プッシュをスキップ"
    log_result "DRY-RUN" "STEP5 main push"
else
    CURRENT_BRANCH=$(git branch --show-current)

    # main にマージ
    git checkout main > /tmp/pipeline-main.log 2>&1 || {
        step_fail "STEP 5: main ブランチへのチェックアウト失敗" "$(cat /tmp/pipeline-main.log | tail -3)"
        exit 1
    }
    git pull ashnova main >> /tmp/pipeline-main.log 2>&1 || true
    git merge develop --no-ff -m "chore: Merge develop into main for production deploy $(date '+%Y-%m-%d')" >> /tmp/pipeline-main.log 2>&1 || {
        step_fail "STEP 5: main へのマージ失敗" "$(cat /tmp/pipeline-main.log | tail -3)"
        exit 1
    }

    if git push ashnova main >> /tmp/pipeline-main.log 2>&1; then
        step_ok "STEP 5: main ブランチにプッシュ成功（production デプロイ開始）"
        git checkout develop > /dev/null 2>&1 || true
    else
        step_fail "STEP 5: main プッシュ失敗" "$(cat /tmp/pipeline-main.log | tail -5)"
        git checkout develop > /dev/null 2>&1 || true
        exit 1
    fi
fi

# ============================================================
# STEP 6: GitHub Actions 完了待ち (production)
# ============================================================
step_info "STEP 6/7: GitHub Actions 完了待ち (production デプロイ)"

if [[ "$DRY_RUN" == "true" ]]; then
    step_warn "[DRY-RUN] GitHub Actions 待機をスキップ"
    log_result "DRY-RUN" "STEP6 GitHub Actions production 待機"
else
    echo "  最新ワークフロー実行を確認中..."
    sleep 10

    MAX_WAIT=900
    ELAPSED=0
    INTERVAL=30

    while [[ "$ELAPSED" -lt "$MAX_WAIT" ]]; do
        RUN_STATUS=$(gh run list \
            --workflow=deploy-aws.yml \
            --branch=main \
            --limit=1 \
            --json status,conclusion,databaseId \
            --jq '.[0]' 2>/dev/null || echo "{}")

        STATUS=$(echo "$RUN_STATUS" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('status','unknown'))" 2>/dev/null || echo "unknown")
        CONCLUSION=$(echo "$RUN_STATUS" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('conclusion',''))" 2>/dev/null || echo "")
        RUN_ID=$(echo "$RUN_STATUS" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('databaseId',''))" 2>/dev/null || echo "")

        echo "  [${ELAPSED}s] status=$STATUS conclusion=$CONCLUSION run_id=$RUN_ID"

        if [[ "$STATUS" == "completed" ]]; then
            if [[ "$CONCLUSION" == "success" ]]; then
                step_ok "STEP 6: GitHub Actions (AWS production) 成功 (run_id=$RUN_ID)"
                break
            elif [[ "$CONCLUSION" == "failure" || "$CONCLUSION" == "cancelled" ]]; then
                step_fail "STEP 6: GitHub Actions (AWS production) 失敗 ($CONCLUSION)" "run_id=$RUN_ID"
                step_warn "production デプロイ失敗。テストは続行します。"
                break
            fi
        fi

        sleep "$INTERVAL"
        ELAPSED=$((ELAPSED + INTERVAL))
    done

    if [[ "$ELAPSED" -ge "$MAX_WAIT" ]]; then
        step_warn "GitHub Actions 完了待ちタイムアウト (${MAX_WAIT}s). テストを続行します。"
    fi
fi

# ============================================================
# STEP 7: production 環境テスト
# ============================================================
step_info "STEP 7/7: production 環境テスト"

if bash "$SCRIPT_DIR/test-cloud-env.sh" production > /tmp/pipeline-production.log 2>&1; then
    PASS_COUNT=$(grep -c "✅ PASS" /tmp/pipeline-production.log || echo 0)
    step_ok "STEP 7: production テスト PASS ($PASS_COUNT 件)"
else
    FAIL_COUNT=$(grep -c "❌ FAIL" /tmp/pipeline-production.log || echo 0)
    step_fail "STEP 7: production テスト FAIL ($FAIL_COUNT 件失敗)" "詳細: /tmp/pipeline-production.log"
    echo "--- production テスト失敗ログ ---"
    tail -20 /tmp/pipeline-production.log
fi

# ============================================================
# サマリー & レポート生成
# ============================================================
hr
echo -e "\n${BOLD}  パイプライン完了サマリー${NC}"
echo -e "  ✅ $PASS PASS / ❌ $FAIL FAIL"
echo ""
for line in "${PIPELINE_LOG[@]}"; do
    echo "  $line"
done
hr

# Markdownレポートは generate-pipeline-report.sh に委譲
if [[ "$DRY_RUN" != "true" ]]; then
    bash "$SCRIPT_DIR/generate-pipeline-report.sh" \
        "$RUN_TIMESTAMP" \
        "/tmp/pipeline-local.log" \
        "/tmp/pipeline-staging.log" \
        "/tmp/pipeline-production.log" \
        2>/dev/null || true
fi

exit $([[ "$FAIL" -eq 0 ]] && echo 0 || echo 1)
