#!/usr/bin/env bash
# ==============================================================
# test-sns-all.sh — 3クラウド統合 E2E テストスイート
# ==============================================================
#
# AWS・Azure・GCP の simple-sns スタックをまとめてテストするラッパー。
# 各クラウドの test-sns-{aws,azure,gcp}.sh を順番に実行し、結果を集計する。
#
# Usage:
#   # 全クラウド read-only テスト (認証不要):
#   ./scripts/test-sns-all.sh
#
#   # 全クラウド read-only + 本番環境:
#   ./scripts/test-sns-all.sh --env production
#
#   # 全クラウド認証付き (ステージング):
#   ./scripts/test-sns-all.sh \
#     --aws-username user@example.com --aws-password 'P@ss123' \
#     --azure-token  <azure-ad-id-token> \
#     --gcp-auto-token
#
#   # 全クラウド認証付き (本番 write あり):
#   ./scripts/test-sns-all.sh --env production --write \
#     --aws-username user@example.com --aws-password 'P@ss123' \
#     --aws-client-id <prod-cognito-client-id> \
#     --azure-token  <azure-ad-id-token> \
#     --gcp-auto-token
#
#   # 特定クラウドのみ実行:
#   ./scripts/test-sns-all.sh --only aws --aws-username user@example.com --aws-password 'P@ss123'
#   ./scripts/test-sns-all.sh --only azure --azure-token <token>
#   ./scripts/test-sns-all.sh --only gcp --gcp-auto-token
#
# Exit codes:
#   0 — 全クラウドの全テスト通過
#   1 — 1つ以上のテストが失敗
#   2 — 依存ツール不足
#
# ==============================================================

set -u   # unbound variable check; -e/-pipefail なし(サブスクリプトのexit codeを手動管理)

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# ── colours ───────────────────────────────────────────────────
RED='\033[0;31m'; GREEN='\033[0;32m'
YELLOW='\033[1;33m'; BLUE='\033[0;34m'; CYAN='\033[0;36m'
BOLD='\033[1m'; NC='\033[0m'

die() { echo -e "${RED}ERROR: $*${NC}" >&2; exit 2; }

# ── defaults ──────────────────────────────────────────────────
ENV=staging
READ_ONLY_FLAG=""
WRITE_FLAG=""
VERBOSE_FLAG=""
SKIP_CLEANUP_FLAG=""
QUICK_FLAG=""
CLOUDS="aws,azure,gcp"

# AWS
AWS_TOKEN=""
AWS_USERNAME=""
AWS_PASSWORD=""
AWS_CLIENT_ID=""
AWS_COGNITO_REGION="ap-northeast-1"
AWS_CF_URL=""
AWS_API_URL=""

# Azure
AZURE_TOKEN=""
AZURE_FD_URL=""
AZURE_API_URL=""

# GCP
GCP_TOKEN=""
GCP_AUTO_TOKEN=false
GCP_CDN_URL=""
GCP_API_URL=""

# フィルタ
RUN_AWS=true
RUN_AZURE=true
RUN_GCP=true

usage() {
  cat <<EOF
Usage: $0 [OPTIONS]

Global options:
  -e, --env <env>           staging|production  (default: staging)
                            production implies --read-only
  -r, --read-only           全クラウドで write テストをスキップ
      --write               --env production でも write テストを許可
      --quick               ランディング + /sns + /health の疎通のみ実行
      --clouds <list>       実行クラウド指定 (aws,azure,gcp のカンマ区切り)
      --only <cloud>        aws|azure|gcp のいずれか1つのみ実行
  -v, --verbose             全レスポンスボディを表示
  -s, --skip-cleanup        テスト投稿を削除しない
  -h, --help                Show this help

AWS options:
      --aws-token <token>      Cognito access token (手動)
  -U, --aws-username <email>   Cognito ユーザー名 (自動取得)
  -P, --aws-password <pw>      Cognito パスワード (自動取得)
      --aws-client-id <id>     Cognito App Client ID (省略時: staging default)
      --aws-cognito-region <r> (default: ap-northeast-1)
      --aws-cf <url>           CloudFront URL override
      --aws-api <url>          API URL override

Azure options:
      --azure-token <token>    Azure AD access/id token
      --azure-fd <url>         Front Door URL override
      --azure-api <url>        API URL override

GCP options:
      --gcp-token <token>      Firebase ID token (手動)
      --gcp-auto-token         gcloud auth print-identity-token で自動取得
      --gcp-cdn <url>          CDN URL override
      --gcp-api <url>          API URL override

Examples:
  # read-only smoke test (all clouds, no token needed):
  $0 --env production

  # Full E2E with auto credentials (staging):
  $0 --aws-username me@example.com --aws-password 'P@ss' --azure-token \$AZURE_TOKEN --gcp-auto-token

  # AWSのみ:
  $0 --only aws --aws-username me@example.com --aws-password 'P@ss'
EOF
}

# ── arg parsing ───────────────────────────────────────────────
while [[ $# -gt 0 ]]; do
  case $1 in
    -e|--env)
      ENV="$2"
      [[ "$ENV" == "production" || "$ENV" == "prod" ]] && ENV=production || ENV=staging
      shift 2 ;;
    -r|--read-only)    READ_ONLY_FLAG="--read-only";   shift ;;
    --write)           WRITE_FLAG="--write";           shift ;;
    --quick)           QUICK_FLAG="--quick";           shift ;;
    --clouds)          CLOUDS="$2";                   shift 2 ;;
    -v|--verbose)      VERBOSE_FLAG="--verbose";       shift ;;
    -s|--skip-cleanup) SKIP_CLEANUP_FLAG="--skip-cleanup"; shift ;;
    --only)
      case "$2" in
        aws)   RUN_AWS=true;  RUN_AZURE=false; RUN_GCP=false ;;
        azure) RUN_AWS=false; RUN_AZURE=true;  RUN_GCP=false ;;
        gcp)   RUN_AWS=false; RUN_AZURE=false; RUN_GCP=true ;;
        *) die "--only requires aws|azure|gcp, got: $2" ;;
      esac
      shift 2 ;;
    --aws-token)         AWS_TOKEN="$2";        shift 2 ;;
    -U|--aws-username)   AWS_USERNAME="$2";     shift 2 ;;
    -P|--aws-password)   AWS_PASSWORD="$2";     shift 2 ;;
    --aws-client-id)     AWS_CLIENT_ID="$2";    shift 2 ;;
    --aws-cognito-region) AWS_COGNITO_REGION="$2"; shift 2 ;;
    --aws-cf)            AWS_CF_URL="$2";       shift 2 ;;
    --aws-api)           AWS_API_URL="$2";      shift 2 ;;
    --azure-token)       AZURE_TOKEN="$2";      shift 2 ;;
    --azure-fd)          AZURE_FD_URL="$2";     shift 2 ;;
    --azure-api)         AZURE_API_URL="$2";    shift 2 ;;
    --gcp-token)         GCP_TOKEN="$2";        shift 2 ;;
    --gcp-auto-token)    GCP_AUTO_TOKEN=true;   shift ;;
    --gcp-cdn)           GCP_CDN_URL="$2";      shift 2 ;;
    --gcp-api)           GCP_API_URL="$2";      shift 2 ;;
    -h|--help)           usage; exit 0 ;;
    *) echo -e "${RED}Unknown option: $1${NC}"; usage; exit 1 ;;
  esac
done

# ── production implies read-only (unless --write) ────────────
[[ "$ENV" == "production" && -z "$WRITE_FLAG" ]] && READ_ONLY_FLAG="--read-only"

# --clouds 指定の反映（--only 指定時は既に反映済み）
if [[ "$RUN_AWS" == true && "$RUN_AZURE" == true && "$RUN_GCP" == true ]]; then
  RUN_AWS=false; RUN_AZURE=false; RUN_GCP=false
  IFS=',' read -r -a _cloud_list <<< "$CLOUDS"
  for cloud in "${_cloud_list[@]}"; do
    case "$(echo "$cloud" | xargs)" in
      aws) RUN_AWS=true ;;
      azure) RUN_AZURE=true ;;
      gcp) RUN_GCP=true ;;
      "") ;;
      *) die "--clouds contains invalid value: $cloud" ;;
    esac
  done
  [[ "$RUN_AWS" == false && "$RUN_AZURE" == false && "$RUN_GCP" == false ]] && die "--clouds produced empty target set"
fi

# ── result tracking ───────────────────────────────────────────
TOTAL_PASS=0
TOTAL_FAIL=0
TOTAL_SKIP=0
declare -A CLOUD_EXIT   # exit code per cloud
declare -A CLOUD_PASS
declare -A CLOUD_FAIL
declare -A CLOUD_SKIP

# ── helper: run one cloud script ─────────────────────────────
run_cloud() {
  local cloud="$1"; shift
  local script="$SCRIPT_DIR/test-sns-${cloud}.sh"

  if [[ ! -f "$script" ]]; then
    echo -e "${RED}[ERROR]${NC} Script not found: $script" >&2
    CLOUD_EXIT[$cloud]=2
    return 2
  fi

  # ── build args ───────────────────────────────────────────
  local args=(--env "$ENV")
  [[ -n "$READ_ONLY_FLAG"  ]] && args+=("$READ_ONLY_FLAG")
  [[ -n "$WRITE_FLAG"      ]] && args+=("$WRITE_FLAG")
  [[ -n "$VERBOSE_FLAG"    ]] && args+=("$VERBOSE_FLAG")
  [[ -n "$SKIP_CLEANUP_FLAG" ]] && args+=("$SKIP_CLEANUP_FLAG")

  case "$cloud" in
    aws)
      [[ -n "$AWS_TOKEN"     ]] && args+=(--token "$AWS_TOKEN")
      [[ -n "$AWS_USERNAME"  ]] && args+=(--username "$AWS_USERNAME")
      [[ -n "$AWS_PASSWORD"  ]] && args+=(--password "$AWS_PASSWORD")
      [[ -n "$AWS_CLIENT_ID" ]] && args+=(--client-id "$AWS_CLIENT_ID")
      [[ "$AWS_COGNITO_REGION" != "ap-northeast-1" ]] && args+=(--cognito-region "$AWS_COGNITO_REGION")
      [[ -n "$AWS_CF_URL"    ]] && args+=(--cf "$AWS_CF_URL")
      [[ -n "$AWS_API_URL"   ]] && args+=(--api "$AWS_API_URL")
      ;;
    azure)
      [[ -n "$AZURE_TOKEN"   ]] && args+=(--token "$AZURE_TOKEN")
      [[ -n "$AZURE_FD_URL"  ]] && args+=(--fd "$AZURE_FD_URL")
      [[ -n "$AZURE_API_URL" ]] && args+=(--api "$AZURE_API_URL")
      ;;
    gcp)
      [[ -n "$GCP_TOKEN"      ]] && args+=(--token "$GCP_TOKEN")
      [[ "$GCP_AUTO_TOKEN" == true ]] && args+=(--auto-token)
      [[ -n "$GCP_CDN_URL"    ]] && args+=(--cdn "$GCP_CDN_URL")
      [[ -n "$GCP_API_URL"    ]] && args+=(--api "$GCP_API_URL")
      ;;
  esac

  # ── per-cloud output file ────────────────────────────────
  local outfile="/tmp/test_sns_${cloud}_output.txt"
  local start_ts
  start_ts=$(date +%s)

  bash "$script" "${args[@]}" 2>&1 | tee "$outfile"
  local exit_code=${PIPESTATUS[0]}

  local end_ts
  end_ts=$(date +%s)
  local elapsed=$(( end_ts - start_ts ))

  # PASS/FAIL/SKIP カウント
  # grep -c はマッチ0件時も "0" を出力するが exit 1 を返すので "|| var=0" で吸収
  local pass=0 fail=0 skip=0
  if [[ -f "$outfile" ]]; then
    pass=$(grep -c '\[PASS\]' "$outfile") || pass=0
    fail=$(grep -c '\[FAIL\]' "$outfile") || fail=0
    skip=$(grep -c '\[SKIP\]' "$outfile") || skip=0
  fi
  pass=$(( pass + 0 )); fail=$(( fail + 0 )); skip=$(( skip + 0 ))

  CLOUD_EXIT[$cloud]=$exit_code
  CLOUD_PASS[$cloud]=$pass
  CLOUD_FAIL[$cloud]=$fail
  CLOUD_SKIP[$cloud]=$skip
  TOTAL_PASS=$(( TOTAL_PASS + pass ))
  TOTAL_FAIL=$(( TOTAL_FAIL + fail ))
  TOTAL_SKIP=$(( TOTAL_SKIP + skip ))

  return $exit_code
}

run_quick_check() {
  local _env="$1"

  local aws_cf="${AWS_CF_URL:-$([[ "$_env" == "production" ]] && echo "https://www.aws.ashnova.jp" || echo "http://multicloud-auto-deploy-staging-frontend.s3-website-ap-northeast-1.amazonaws.com") }"
  local aws_api="${AWS_API_URL:-$([[ "$_env" == "production" ]] && echo "https://qkzypr32af.execute-api.ap-northeast-1.amazonaws.com" || echo "https://z42qmqdqac.execute-api.ap-northeast-1.amazonaws.com") }"
  local azure_fd="${AZURE_FD_URL:-$([[ "$_env" == "production" ]] && echo "https://www.azure.ashnova.jp" || echo "https://mcadwebd45ihd.z11.web.core.windows.net") }"
  local azure_api="${AZURE_API_URL:-$([[ "$_env" == "production" ]] && echo "https://multicloud-auto-deploy-production-func-cfdne7ecbngnh0d0.japaneast-01.azurewebsites.net/api" || echo "https://multicloud-auto-deploy-staging-func-d8a2guhfere0etcq.japaneast-01.azurewebsites.net") }"
  local gcp_cdn="${GCP_CDN_URL:-$([[ "$_env" == "production" ]] && echo "https://www.gcp.ashnova.jp" || echo "https://multicloud-auto-deploy-staging-api-son5b3ml7a-an.a.run.app") }"
  local gcp_api="${GCP_API_URL:-$([[ "$_env" == "production" ]] && echo "https://multicloud-auto-deploy-production-api-son5b3ml7a-an.a.run.app" || echo "https://multicloud-auto-deploy-staging-api-son5b3ml7a-an.a.run.app") }"

  local total=0 passed=0 failed=0

  check_url() {
    local label="$1" url="$2" expect="${3:-200}"
    total=$((total + 1))
    local status
    status=$(curl -s -o /dev/null -w "%{http_code}" --max-time 20 --compressed "$url" 2>/dev/null || true)
    if [[ "$status" == "$expect" ]]; then
      echo -e "  ${GREEN}[PASS]${NC}  $label  [HTTP $status]"
      passed=$((passed + 1))
    else
      echo -e "  ${RED}[FAIL]${NC}  $label  [expected $expect, got $status]"
      failed=$((failed + 1))
    fi
  }

  echo ""
  echo -e "${BOLD}══ Quick Connectivity Check ═══════════════════════════════${NC}"

  if [[ $RUN_AWS == true ]]; then
    echo -e "${BOLD}── AWS ─────────────────────────────────────────────────────${NC}"
    check_url "AWS landing page   GET /" "$aws_cf/" 200
    check_url "AWS SNS app        GET /sns/" "$aws_cf/sns/" 200
    check_url "AWS API health     GET /health" "${aws_api%/}/health" 200
  fi

  if [[ $RUN_AZURE == true ]]; then
    echo -e "${BOLD}── Azure ───────────────────────────────────────────────────${NC}"
    check_url "Azure landing page GET /" "$azure_fd/" 200
    check_url "Azure SNS app      GET /sns/" "$azure_fd/sns/" 200
    check_url "Azure API health   GET /health" "${azure_api%/}/health" 200
  fi

  if [[ $RUN_GCP == true ]]; then
    echo -e "${BOLD}── GCP ─────────────────────────────────────────────────────${NC}"
    check_url "GCP landing page   GET /" "$gcp_cdn/" 200
    check_url "GCP SNS app        GET /sns/" "$gcp_cdn/sns/" 200
    check_url "GCP API health     GET /health" "${gcp_api%/}/health" 200
  fi

  echo ""
  echo -e "  ${GREEN}Passed${NC}: $passed / $total"
  if [[ $failed -gt 0 ]]; then
    echo -e "  ${RED}Failed${NC}: $failed / $total"
    return 1
  fi
  return 0
}

# ── banner ────────────────────────────────────────────────────
echo ""
echo -e "${BOLD}╔══════════════════════════════════════════════════════════╗${NC}"
echo -e "${BOLD}║   simple-sns — 3クラウド統合 E2E テストスイート          ║${NC}"
echo -e "${BOLD}╚══════════════════════════════════════════════════════════╝${NC}"
echo -e "  環境       : ${CYAN}$ENV${NC}"
echo -e "  モード     : $(  [[ -n "$READ_ONLY_FLAG" ]] && echo "${YELLOW}read-only${NC}" || echo "${GREEN}read-write${NC}" )"
echo -e "  AWS 認証   : $(  [[ -n "$AWS_TOKEN" ]]    && echo "${CYAN}token provided${NC}" || \
                             [[ -n "$AWS_USERNAME" ]] && echo "${CYAN}auto (username/password)${NC}" || \
                             echo "${YELLOW}none (public tests only)${NC}" )"
echo -e "  Azure 認証 : $(  [[ -n "$AZURE_TOKEN" ]]  && echo "${CYAN}token provided${NC}" || \
                             echo "${YELLOW}none (public tests only)${NC}" )"
echo -e "  GCP 認証   : $(  [[ -n "$GCP_TOKEN" ]]    && echo "${CYAN}token provided${NC}" || \
                             [[ "$GCP_AUTO_TOKEN" == true ]] && echo "${CYAN}auto (gcloud)${NC}" || \
                             echo "${YELLOW}none (public tests only)${NC}" )"
echo -e "  クイック   : $( [[ -n "$QUICK_FLAG" ]] && echo "${CYAN}enabled${NC}" || echo "${YELLOW}disabled${NC}" )"
echo ""
echo -e "$(   [[ $RUN_AWS   == true ]] && echo "  ▶ AWS"   || echo "  ─ AWS   (skip)")"
echo -e "$(   [[ $RUN_AZURE == true ]] && echo "  ▶ Azure" || echo "  ─ Azure (skip)")"
echo -e "$(   [[ $RUN_GCP   == true ]] && echo "  ▶ GCP"   || echo "  ─ GCP   (skip)")"
echo ""

if [[ -n "$QUICK_FLAG" ]]; then
  run_quick_check "$ENV"
  exit $?
fi

# ════════════════════════════════════════════════════════════
OVERALL_EXIT=0

if [[ $RUN_AWS == true ]]; then
  echo -e "${BOLD}══════════════════════════════════════════════════════════${NC}"
  echo -e "${BOLD}  ☁  AWS${NC}"
  echo -e "${BOLD}══════════════════════════════════════════════════════════${NC}"
  run_cloud aws || OVERALL_EXIT=1
  echo ""
fi

if [[ $RUN_AZURE == true ]]; then
  echo -e "${BOLD}══════════════════════════════════════════════════════════${NC}"
  echo -e "${BOLD}  ☁  Azure${NC}"
  echo -e "${BOLD}══════════════════════════════════════════════════════════${NC}"
  run_cloud azure || OVERALL_EXIT=1
  echo ""
fi

if [[ $RUN_GCP == true ]]; then
  echo -e "${BOLD}══════════════════════════════════════════════════════════${NC}"
  echo -e "${BOLD}  ☁  GCP${NC}"
  echo -e "${BOLD}══════════════════════════════════════════════════════════${NC}"
  run_cloud gcp || OVERALL_EXIT=1
  echo ""
fi

# ── aggregate summary ─────────────────────────────────────────
echo ""
echo -e "${BOLD}╔══════════════════════════════════════════════════════════╗${NC}"
echo -e "${BOLD}║   統合テスト結果サマリー                                  ║${NC}"
echo -e "${BOLD}╚══════════════════════════════════════════════════════════╝${NC}"
printf "  %-8s  %6s  %6s  %6s  %s\n" "Cloud" "PASS" "FAIL" "SKIP" "Status"
echo  "  ────────  ──────  ──────  ──────  ──────────"
for cloud in aws azure gcp; do
  # skip clouds that were not run
  [[ "$cloud" == "aws"   && $RUN_AWS   == false ]] && continue
  [[ "$cloud" == "azure" && $RUN_AZURE == false ]] && continue
  [[ "$cloud" == "gcp"   && $RUN_GCP   == false ]] && continue

  p="${CLOUD_PASS[$cloud]:-0}"
  f="${CLOUD_FAIL[$cloud]:-0}"
  s="${CLOUD_SKIP[$cloud]:-0}"
  ex="${CLOUD_EXIT[$cloud]:-?}"
  if [[ "$ex" == "0" ]]; then
    status="${GREEN}✅ PASS${NC}"
  else
    status="${RED}❌ FAIL (exit $ex)${NC}"
  fi
  printf "  %-8s  %6d  %6d  %6d  " "${cloud}" "$p" "$f" "$s"
  echo -e "$status"
done
echo  "  ────────  ──────  ──────  ──────  ──────────"
printf "  %-8s  %6d  %6d  %6d\n" "TOTAL" "$TOTAL_PASS" "$TOTAL_FAIL" "$TOTAL_SKIP"
echo ""

if [[ $OVERALL_EXIT -eq 0 ]]; then
  echo -e "${GREEN}${BOLD}  ✅ 全クラウドのテストが通過しました！${NC}"
else
  echo -e "${RED}${BOLD}  ❌ 一部のテストが失敗しました。上記ログを確認してください。${NC}"
fi
echo ""
exit $OVERALL_EXIT
