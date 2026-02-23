#!/usr/bin/env bash
# ================================================================
# test-staging-all.sh — Multicloud Staging Test Orchestrator
# ================================================================
#
# Runs the SNS end-to-end test suite against all three cloud
# staging environments (AWS, Azure, GCP) in sequence and produces
# a consolidated summary report.
#
# Usage:
#   # Public-only tests (no tokens required):
#   ./scripts/test-staging-all.sh
#
#   # Full authenticated tests (pass all three tokens):
#   ./scripts/test-staging-all.sh \
#     --aws-token  <cognito-access-token>   \
#     --azure-token <azure-ad-id-token>     \
#     --gcp-token  <firebase-id-token>
#
#   # Run only specific clouds:
#   ./scripts/test-staging-all.sh --clouds aws,gcp --aws-token eyJ...
#
#   # Quick landing-page + health check only (no auth required):
#   ./scripts/test-staging-all.sh --quick
#
#   # Keep test posts after run (for manual inspection):
#   ./scripts/test-staging-all.sh --skip-cleanup
#
# Environment variable overrides (optional):
#   AWS_CF_URL   AWS_API_URL
#   AZURE_FD_URL AZURE_API_URL
#   GCP_CDN_URL  GCP_API_URL
#
# Exit codes:
#   0 — All executed tests passed across all clouds
#   1 — One or more tests failed
#   2 — Missing required dependency
#
# ================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# ── colours ──────────────────────────────────────────────────
RED='\033[0;31m'; GREEN='\033[0;32m'
YELLOW='\033[1;33m'; BLUE='\033[0;34m'; CYAN='\033[0;36m'
BOLD='\033[1m'; NC='\033[0m'

die() { echo -e "${RED}ERROR: $*${NC}" >&2; exit 2; }

# ── dependency check ─────────────────────────────────────────
command -v curl >/dev/null 2>&1 || die "curl is required but not installed"
command -v jq   >/dev/null 2>&1 || die "jq is required but not installed"

# ── defaults ─────────────────────────────────────────────────
AWS_TOKEN=""
AZURE_TOKEN=""
GCP_TOKEN=""
CLOUDS="aws,azure,gcp"
VERBOSE=false
SKIP_CLEANUP=false
QUICK=false

# ── arg parsing ──────────────────────────────────────────────
usage() {
  cat <<EOF
Usage: $0 [OPTIONS]

Options:
  --aws-token   <token>   Cognito access token for AWS auth tests
  --azure-token <token>   Azure AD ID token for Azure auth tests
  --gcp-token   <token>   Firebase ID token for GCP auth tests
  --clouds      <list>    Comma-separated list: aws,azure,gcp  (default: all)
  --quick                 Run only landing page + health checks (no auth needed)
  --skip-cleanup          Do not delete test posts after the run
  -v, --verbose           Print full response bodies
  -h, --help              Show this help

Environment variables (URL overrides):
  AWS_CF_URL     CloudFront URL      (default: https://d1tf3uumcm4bo1.cloudfront.net)
  AWS_API_URL    API Gateway URL     (default: https://z42qmqdqac.execute-api.ap-northeast-1.amazonaws.com)
  AZURE_FD_URL   Front Door URL      (default: https://mcad-staging-d45ihd-dseygrc9c3a3htgj.z01.azurefd.net)
  AZURE_API_URL  Function App URL    (default: https://multicloud-auto-deploy-staging-func-d8a2guhfere0etcq.japaneast-01.azurewebsites.net)
  GCP_CDN_URL    Cloud CDN URL       (default: https://www.gcp.ashnova.jp)
  GCP_API_URL    Cloud Run URL       (default: https://multicloud-auto-deploy-staging-api-son5b3ml7a-an.a.run.app)

Examples:
  # Public-only (connectivity check):
  $0

  # Full authenticated run:
  $0 \\
    --aws-token   "\$(aws cognito-idp initiate-auth --auth-flow USER_PASSWORD_AUTH --client-id 1k41lqkds4oah55ns8iod30dv2 --auth-parameters USERNAME=user@example.com,PASSWORD=pw --region ap-northeast-1 --query 'AuthenticationResult.AccessToken' --output text)" \\
    --gcp-token   "\$(gcloud auth print-identity-token)" \\
    --azure-token "<paste azure id_token from browser DevTools>"

  # AWS + GCP only:
  $0 --clouds aws,gcp --aws-token eyJ... --gcp-token "\$(gcloud auth print-identity-token)"
EOF
}

while [[ $# -gt 0 ]]; do
  case $1 in
    --aws-token)   AWS_TOKEN="$2";   shift 2 ;;
    --azure-token) AZURE_TOKEN="$2"; shift 2 ;;
    --gcp-token)   GCP_TOKEN="$2";   shift 2 ;;
    --clouds)      CLOUDS="$2";      shift 2 ;;
    --quick)       QUICK=true;       shift ;;
    --skip-cleanup) SKIP_CLEANUP=true; shift ;;
    -v|--verbose)  VERBOSE=true;     shift ;;
    -h|--help)     usage; exit 0 ;;
    *) echo -e "${RED}Unknown option: $1${NC}"; usage; exit 1 ;;
  esac
done

# ── timing helper ────────────────────────────────────────────
_start_time=$(date +%s)
elapsed() { echo $(( $(date +%s) - _start_time )); }

# ── per-cloud result tracking ────────────────────────────────
declare -A CLOUD_EXIT_CODE
declare -A CLOUD_PASS
declare -A CLOUD_FAIL
declare -A CLOUD_SKIP
declare -A CLOUD_DURATION

# ── run_cloud: invoke individual test script ─────────────────
run_cloud() {
  local cloud="$1"
  local script="$2"
  local extra_args=("${@:3}")
  local t0
  t0=$(date +%s)

  if [[ ! -f "$script" ]]; then
    echo -e "${RED}[ERROR]${NC} Script not found: $script"
    CLOUD_EXIT_CODE[$cloud]=2
    CLOUD_PASS[$cloud]=0; CLOUD_FAIL[$cloud]=1; CLOUD_SKIP[$cloud]=0
    CLOUD_DURATION[$cloud]=0
    return
  fi
  chmod +x "$script"

  local outfile="/tmp/test_staging_${cloud}.log"
  local exit_code=0

  echo -e "${BOLD}${BLUE}▶ Starting ${cloud^^} tests...${NC}"
  echo ""

  # Run and tee to both terminal and log file
  bash "$script" "${extra_args[@]}" 2>&1 | tee "$outfile" || exit_code=${PIPESTATUS[0]}

  local t1
  t1=$(date +%s)
  CLOUD_EXIT_CODE[$cloud]=$exit_code
  CLOUD_DURATION[$cloud]=$(( t1 - t0 ))

  # Parse pass/fail/skip counts from output
  CLOUD_PASS[$cloud]=$(grep -c '^\[PASS\]\|[✅] \|^.*\[PASS\]' "$outfile" 2>/dev/null || echo 0)
  CLOUD_FAIL[$cloud]=$(grep -c '^\[FAIL\]\|[❌] \|^.*\[FAIL\]' "$outfile" 2>/dev/null || echo 0)
  CLOUD_SKIP[$cloud]=$(grep -c '^\[SKIP\]\|^.*\[SKIP\]' "$outfile" 2>/dev/null || echo 0)

  # Extract summary line counts from the "Results" section for accuracy
  local p f s
  p=$(grep -E '^\s+Passed\s*:' "$outfile" | grep -oE '[0-9]+' | tail -1 || true)
  f=$(grep -E '^\s+Failed\s*:' "$outfile" | grep -oE '[0-9]+' | tail -1 || true)
  s=$(grep -E '^\s+Skipped\s*:' "$outfile" | grep -oE '[0-9]+' | tail -1 || true)
  [[ -n "$p" ]] && CLOUD_PASS[$cloud]=$p
  [[ -n "$f" ]] && CLOUD_FAIL[$cloud]=$f
  [[ -n "$s" ]] && CLOUD_SKIP[$cloud]=$s

  if [[ $exit_code -eq 0 ]]; then
    echo -e "\n${GREEN}${BOLD}  ✅ ${cloud^^} — All tests passed${NC}"
  else
    echo -e "\n${RED}${BOLD}  ❌ ${cloud^^} — Tests failed (exit $exit_code)${NC}"
  fi
  echo ""
}

# ── quick_check: health + landing page only ──────────────────
run_quick_check() {
  echo ""
  echo -e "${BOLD}============================================================${NC}"
  echo -e "${BOLD}  Quick Connectivity Check — All 3 Clouds${NC}"
  echo -e "${BOLD}============================================================${NC}"
  echo ""

  local total=0 passed=0 failed=0

  # URLs
  local cfurl="${AWS_CF_URL:-https://d1tf3uumcm4bo1.cloudfront.net}"
  local awsapi="${AWS_API_URL:-https://z42qmqdqac.execute-api.ap-northeast-1.amazonaws.com}"
  local fdurl="${AZURE_FD_URL:-https://mcad-staging-d45ihd-dseygrc9c3a3htgj.z01.azurefd.net}"
  local azapi="${AZURE_API_URL:-https://multicloud-auto-deploy-staging-func-d8a2guhfere0etcq.japaneast-01.azurewebsites.net}"
  local gcpcdn="${GCP_CDN_URL:-https://www.gcp.ashnova.jp}"
  local gcpapi="${GCP_API_URL:-https://multicloud-auto-deploy-staging-api-son5b3ml7a-an.a.run.app}"

  check_url() {
    local label="$1" url="$2" expect="${3:-200}"
    total=$((total + 1))
    local status
    status=$(curl -s -o /dev/null -w "%{http_code}" --max-time 20 --compressed "$url" 2>/dev/null || echo "000")
    if [[ "$status" == "$expect" ]]; then
      echo -e "  ${GREEN}[PASS]${NC}  $label  [HTTP $status]"
      passed=$((passed + 1))
    else
      echo -e "  ${RED}[FAIL]${NC}  $label  [expected $expect, got $status]"
      failed=$((failed + 1))
    fi
  }

  echo -e "${BOLD}── AWS ──────────────────────────────────────────────────────${NC}"
  check_url "AWS CloudFront landing page   GET /"      "$cfurl/"          200
  check_url "AWS CloudFront SNS app        GET /sns/"  "$cfurl/sns/"      200
  check_url "AWS API Gateway health        GET /health" "$awsapi/health"  200

  echo ""
  echo -e "${BOLD}── Azure ────────────────────────────────────────────────────${NC}"
  check_url "Azure Front Door landing page   GET /"     "$fdurl/"         200
  check_url "Azure Front Door SNS app        GET /sns/" "$fdurl/sns/"     200
  check_url "Azure Function App health       GET /health" "$azapi/health" 200

  echo ""
  echo -e "${BOLD}── GCP ──────────────────────────────────────────────────────${NC}"
  check_url "GCP CDN landing page   GET /"      "$gcpcdn/"         200
  check_url "GCP CDN SNS app        GET /sns/"  "$gcpcdn/sns/"     200
  check_url "GCP Cloud Run health   GET /health" "$gcpapi/health"  200

  echo ""
  echo -e "${BOLD}============================================================${NC}"
  printf "  ${GREEN}Passed${NC}: %d / %d\n" "$passed" "$total"
  if [[ $failed -gt 0 ]]; then
    printf "  ${RED}Failed${NC}: %d / %d\n" "$failed" "$total"
    echo -e "${RED}${BOLD}  ❌ Quick check: $failed failure(s) detected.${NC}"
    return 1
  else
    echo -e "${GREEN}${BOLD}  ✅ Quick check: All $total endpoints reachable!${NC}"
    return 0
  fi
}

# ================================================================
# MAIN
# ================================================================

echo ""
echo -e "${BOLD}╔══════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BOLD}║       Multicloud Staging — Full Test Suite                  ║${NC}"
echo -e "${BOLD}║       $(date '+%Y-%m-%d %H:%M:%S %Z')                            ║${NC}"
echo -e "${BOLD}╚══════════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "  Clouds   : ${CYAN}$CLOUDS${NC}"
echo -e "  Quick    : ${CYAN}$QUICK${NC}"
echo -e "  Verbose  : ${CYAN}$VERBOSE${NC}"
echo -e "  Cleanup  : ${CYAN}$([ "$SKIP_CLEANUP" == true ] && echo skipped || echo enabled)${NC}"
echo ""

# ── quick mode ──────────────────────────────────────────────
if [[ "$QUICK" == true ]]; then
  run_quick_check
  exit $?
fi

# ── cloud-specific runs ──────────────────────────────────────
OVERALL_FAIL=0

# ── AWS ─────────────────────────────────────────────────────
if [[ "$CLOUDS" == *aws* ]]; then
  echo -e "${YELLOW}════════════════════════════════════════════════════════════════${NC}"
  echo -e "${YELLOW}  Cloud: AWS (ap-northeast-1)${NC}"
  echo -e "${YELLOW}════════════════════════════════════════════════════════════════${NC}"

  aws_args=()
  [[ -n "${AWS_CF_URL:-}"  ]] && aws_args+=(--cf  "$AWS_CF_URL")
  [[ -n "${AWS_API_URL:-}" ]] && aws_args+=(--api "$AWS_API_URL")
  [[ -n "$AWS_TOKEN"       ]] && aws_args+=(--token "$AWS_TOKEN")
  [[ "$VERBOSE" == true    ]] && aws_args+=(--verbose)
  [[ "$SKIP_CLEANUP" == true ]] && aws_args+=(--skip-cleanup)

  run_cloud aws "$SCRIPT_DIR/test-sns-aws.sh" "${aws_args[@]}"
  [[ ${CLOUD_EXIT_CODE[aws]} -ne 0 ]] && OVERALL_FAIL=$((OVERALL_FAIL + 1))
fi

# ── Azure ────────────────────────────────────────────────────
if [[ "$CLOUDS" == *azure* ]]; then
  echo -e "${YELLOW}════════════════════════════════════════════════════════════════${NC}"
  echo -e "${YELLOW}  Cloud: Azure (japaneast)${NC}"
  echo -e "${YELLOW}════════════════════════════════════════════════════════════════${NC}"

  azure_args=()
  [[ -n "${AZURE_FD_URL:-}"  ]] && azure_args+=(--fd  "$AZURE_FD_URL")
  [[ -n "${AZURE_API_URL:-}" ]] && azure_args+=(--api "$AZURE_API_URL")
  [[ -n "$AZURE_TOKEN"       ]] && azure_args+=(--token "$AZURE_TOKEN")
  [[ "$VERBOSE" == true      ]] && azure_args+=(--verbose)
  [[ "$SKIP_CLEANUP" == true ]] && azure_args+=(--skip-cleanup)

  run_cloud azure "$SCRIPT_DIR/test-sns-azure.sh" "${azure_args[@]}"
  [[ ${CLOUD_EXIT_CODE[azure]} -ne 0 ]] && OVERALL_FAIL=$((OVERALL_FAIL + 1))
fi

# ── GCP ─────────────────────────────────────────────────────
if [[ "$CLOUDS" == *gcp* ]]; then
  echo -e "${YELLOW}════════════════════════════════════════════════════════════════${NC}"
  echo -e "${YELLOW}  Cloud: GCP (asia-northeast1)${NC}"
  echo -e "${YELLOW}════════════════════════════════════════════════════════════════${NC}"

  gcp_args=()
  [[ -n "${GCP_CDN_URL:-}"  ]] && gcp_args+=(--cdn "$GCP_CDN_URL")
  [[ -n "${GCP_API_URL:-}"  ]] && gcp_args+=(--api "$GCP_API_URL")
  [[ -n "$GCP_TOKEN"        ]] && gcp_args+=(--token "$GCP_TOKEN")
  [[ "$VERBOSE" == true     ]] && gcp_args+=(--verbose)
  [[ "$SKIP_CLEANUP" == true ]] && gcp_args+=(--skip-cleanup)

  run_cloud gcp "$SCRIPT_DIR/test-sns-gcp.sh" "${gcp_args[@]}"
  [[ ${CLOUD_EXIT_CODE[gcp]} -ne 0 ]] && OVERALL_FAIL=$((OVERALL_FAIL + 1))
fi

# ── Consolidated Summary ─────────────────────────────────────
TOTAL_ELAPSED=$(elapsed)
echo ""
echo -e "${BOLD}╔══════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BOLD}║           Consolidated Results Summary                      ║${NC}"
echo -e "${BOLD}╚══════════════════════════════════════════════════════════════╝${NC}"
echo ""
printf "  %-10s  %-8s  %-8s  %-8s  %-5s  %s\n" \
  "Cloud" "Passed" "Failed" "Skipped" "Time" "Status"
echo "  ──────────────────────────────────────────────────────────"

TOTAL_PASS=0
TOTAL_FAIL=0
TOTAL_SKIP=0

for cloud in aws azure gcp; do
  [[ "$CLOUDS" != *$cloud* ]] && continue
  p=${CLOUD_PASS[$cloud]:-0}
  f=${CLOUD_FAIL[$cloud]:-0}
  s=${CLOUD_SKIP[$cloud]:-0}
  d=${CLOUD_DURATION[$cloud]:-0}
  code=${CLOUD_EXIT_CODE[$cloud]:-0}
  TOTAL_PASS=$((TOTAL_PASS + p))
  TOTAL_FAIL=$((TOTAL_FAIL + f))
  TOTAL_SKIP=$((TOTAL_SKIP + s))

  if [[ $code -eq 0 ]]; then
    status="${GREEN}✅ PASS${NC}"
  else
    status="${RED}❌ FAIL${NC}"
  fi

  printf "  %-10s  ${GREEN}%-8s${NC}  ${RED}%-8s${NC}  ${CYAN}%-8s${NC}  %-5s  " \
    "${cloud^^}" "$p" "$f" "$s" "${d}s"
  echo -e "$status"
done

echo "  ──────────────────────────────────────────────────────────"
printf "  %-10s  ${GREEN}%-8s${NC}  ${RED}%-8s${NC}  ${CYAN}%-8s${NC}  %-5s\n" \
  "TOTAL" "$TOTAL_PASS" "$TOTAL_FAIL" "$TOTAL_SKIP" "${TOTAL_ELAPSED}s"
echo ""

TOTAL_TESTS=$((TOTAL_PASS + TOTAL_FAIL))
if [[ $TOTAL_TESTS -gt 0 ]]; then
  RATE=$(awk "BEGIN {printf \"%.0f\", ($TOTAL_PASS/$TOTAL_TESTS)*100}")
  echo -e "  Overall pass rate: ${BOLD}${RATE}%%${NC}  (${TOTAL_PASS}/${TOTAL_TESTS})"
fi
echo ""

# Log file locations
echo "  Detailed logs:"
for cloud in aws azure gcp; do
  [[ "$CLOUDS" != *$cloud* ]] && continue
  echo -e "    ${cloud^^}: /tmp/test_staging_${cloud}.log"
done
echo ""

if [[ $OVERALL_FAIL -eq 0 ]]; then
  echo -e "${GREEN}${BOLD}  ✅ ALL CLOUDS PASSED!${NC}"
  exit 0
else
  echo -e "${RED}${BOLD}  ❌ $OVERALL_FAIL cloud(s) had test failures.${NC}"
  echo "  See docs/STAGING_TEST_GUIDE.md for troubleshooting."
  exit 1
fi
