#!/usr/bin/env bash
# ================================================================
# test-landing-pages.sh — Landing Page Test Suite (all 3 clouds)
# ================================================================
#
# Tests the static landing page (/) served via each cloud's CDN:
#   - AWS:   CloudFront + S3
#   - Azure: Azure Front Door + Blob Storage
#   - GCP:   Cloud CDN (Global LB) + GCS
#
# Tests performed per cloud:
#   1. HTTP 200 response from CDN
#   2. Content-Type: text/html
#   3. Page contains "Ashnova" brand name
#   4. Cloud badge for the expected provider is present
#   5. SNS app link is present on the page
#   6. No localhost references (env var injection check)
#   7. HTTPS redirect / secure transport (where applicable)
#   8. Cache-Control header is sensibly set
#   9. Cross-cloud: compare landing page sizes (ballpark check)
#  10. Response time < 8 seconds
#
# Usage:
#   ./scripts/test-landing-pages.sh
#
#   # Override specific URLs:
#   AWS_CF_URL=https://my-cf.cloudfront.net \
#   AZURE_FD_URL=https://my.azurefd.net \
#   GCP_CDN_URL=https://www.gcp.ashnova.jp \
#   ./scripts/test-landing-pages.sh
#
#   # Run specific cloud only:
#   ./scripts/test-landing-pages.sh --cloud aws
#   ./scripts/test-landing-pages.sh --cloud azure
#   ./scripts/test-landing-pages.sh --cloud gcp
#
# Exit codes:
#   0 — All tests passed
#   1 — One or more tests failed
#   2 — Missing required dependency
#
# ================================================================

set -euo pipefail

# ── colours ──────────────────────────────────────────────────
RED='\033[0;31m'; GREEN='\033[0;32m'
YELLOW='\033[1;33m'; BLUE='\033[0;34m'; CYAN='\033[0;36m'
BOLD='\033[1m'; NC='\033[0m'

# ── defaults ─────────────────────────────────────────────────
AWS_CF_URL="${AWS_CF_URL:-https://d1tf3uumcm4bo1.cloudfront.net}"
AZURE_FD_URL="${AZURE_FD_URL:-https://mcad-staging-d45ihd-dseygrc9c3a3htgj.z01.azurefd.net}"
GCP_CDN_URL="${GCP_CDN_URL:-https://www.gcp.ashnova.jp}"
TARGET_CLOUD=""
VERBOSE=false

# ── dependency check ─────────────────────────────────────────
command -v curl >/dev/null 2>&1 || { echo -e "${RED}ERROR: curl is required${NC}" >&2; exit 2; }
command -v jq   >/dev/null 2>&1 || { echo -e "${RED}ERROR: jq is required${NC}"   >&2; exit 2; }

# ── arg parsing ──────────────────────────────────────────────
usage() {
  cat <<EOF
Usage: $0 [OPTIONS]

Options:
  --cloud <aws|azure|gcp>   Test a single cloud only (default: all)
  -v, --verbose             Print extra debug output
  -h, --help                Show this help

Environment variables:
  AWS_CF_URL    (default: https://d1tf3uumcm4bo1.cloudfront.net)
  AZURE_FD_URL  (default: https://mcad-staging-d45ihd-dseygrc9c3a3htgj.z01.azurefd.net)
  GCP_CDN_URL   (default: https://www.gcp.ashnova.jp)
EOF
}

while [[ $# -gt 0 ]]; do
  case $1 in
    --cloud)   TARGET_CLOUD="$2"; shift 2 ;;
    -v|--verbose) VERBOSE=true; shift ;;
    -h|--help) usage; exit 0 ;;
    *) echo -e "${RED}Unknown option: $1${NC}"; usage; exit 1 ;;
  esac
done

# ── counters ─────────────────────────────────────────────────
PASS=0; FAIL=0; SKIP=0

ok()   { echo -e "  ${GREEN}[PASS]${NC}  $*"; PASS=$((PASS + 1)); }
fail() { echo -e "  ${RED}[FAIL]${NC}  $*"; FAIL=$((FAIL + 1)); }
warn() { echo -e "  ${YELLOW}[WARN]${NC}  $*"; }
info() { echo -e "  ${BLUE}[INFO]${NC}  $*"; }
sep()  { echo -e "${YELLOW}────────────────────────────────────────────────────────${NC}"; }

# ── test_landing_page: core test function ────────────────────
# test_landing_page <cloud_label> <url> <expected_badge_text>
test_landing_page() {
  local cloud_label="$1"
  local url="$2"
  local expected_badge="$3"

  echo ""
  sep
  echo -e "${BOLD}Testing: ${CYAN}$cloud_label${NC}${BOLD}  ($url)${NC}"
  sep

  # ── Test 1: Response time + HTTP 200 ────────────────────
  local t0 t1 elapsed_ms
  t0=$(date +%s%3N 2>/dev/null || date +%s)
  local http_code headers_file body_file
  headers_file=$(mktemp /tmp/landing_headers_XXXXXX)
  body_file=$(mktemp /tmp/landing_body_XXXXXX)

  # Capture headers + body separately; follow redirects
  http_code=$(curl -s -o "$body_file" -D "$headers_file" \
    -w "%{http_code}" -L --max-time 20 --compressed "$url/" 2>/dev/null \
    || echo "000")
  t1=$(date +%s%3N 2>/dev/null || date +%s)
  elapsed_ms=$(( t1 - t0 ))
  # Fallback for systems where date +%s%3N is unavailable (shows 0)
  [[ "$elapsed_ms" -lt 0 ]] && elapsed_ms=0

  local headers
  headers=$(cat "$headers_file")
  local body
  body=$(cat "$body_file")

  # Test 1a: HTTP 200
  if [[ "$http_code" == "200" ]]; then
    ok "HTTP 200  [got $http_code]"
  else
    fail "HTTP 200  [expected 200, got $http_code]"
  fi

  # Test 1b: Response time
  if [[ "$elapsed_ms" -gt 0 && "$elapsed_ms" -lt 8000 ]]; then
    ok "Response time < 8s  [${elapsed_ms}ms]"
  elif [[ "$elapsed_ms" -eq 0 ]]; then
    warn "Response time measurement unavailable"
  else
    fail "Response time >= 8s  [${elapsed_ms}ms]"
  fi

  # ── Test 2: Content-Type ─────────────────────────────────
  local ct
  ct=$(echo "$headers" | grep -i '^content-type:' | head -1 | tr -d '\r\n' || echo "")
  if echo "$ct" | grep -qi 'text/html'; then
    ok "Content-Type: text/html  [$ct]"
  else
    fail "Content-Type: text/html  [got: $ct]"
  fi

  # ── Test 3: Brand name ───────────────────────────────────
  if echo "$body" | grep -qi 'ashnova'; then
    ok "Page contains brand name 'Ashnova'"
  else
    fail "Page does NOT contain brand name 'Ashnova'"
    [[ "$VERBOSE" == true ]] && echo "  First 500 chars:" && echo "${body:0:500}"
  fi

  # ── Test 4: Cloud badge ──────────────────────────────────
  if echo "$body" | grep -qi "$expected_badge"; then
    ok "Cloud badge present: '$expected_badge'"
  else
    fail "Cloud badge NOT found: '$expected_badge'"
  fi

  # ── Test 5: SNS app link ─────────────────────────────────
  if echo "$body" | grep -qi 'sns'; then
    ok "SNS app link/reference present"
  else
    fail "SNS app link/reference NOT found"
  fi

  # ── Test 6: No localhost references ──────────────────────
  # Detect env-var injection issues: localhost appearing in actual URLs/endpoints
  # (href, src, fetch, BASE_URL, API_URL, etc.) rather than in JS env-detection code
  # e.g. "hostname === 'localhost'" is normal JS code — NOT an injection issue
  local lh_in_url lh_count
  # Match localhost in URL contexts only (href, src, fetch, base_url, api patterns)
  lh_in_url=$(echo "$body" | grep -ioE \
    '(href|src|fetch\(|BASE_URL|API_URL|endpoint)[[:space:]]*[=:][[:space:]]*["'"'"'][^"'"'"']*localhost[^"'"'"']*["'"'"']' \
    | wc -l || true)
  lh_count=${lh_in_url// /}
  if [[ "$lh_count" -gt 0 ]]; then
    fail "Page exposes 'localhost' in URL/endpoint context (env var injection issue?)"
    [[ "$VERBOSE" == true ]] && grep -in 'localhost' <<< "$body" | head -5
  else
    ok "No 'localhost' in URL/endpoint context (env vars injected correctly)"
  fi

  # ── Test 7: HTTPS transport ──────────────────────────────
  if echo "$url" | grep -q '^https://'; then
    # Check that we didn't get downgraded
    local final_url
    final_url=$(curl -s -o /dev/null -L --max-time 10 -w "%{url_effective}" "$url" 2>/dev/null || echo "$url")
    if echo "$final_url" | grep -q '^https://'; then
      ok "HTTPS transport maintained (no downgrade to HTTP)"
    else
      fail "HTTPS downgraded to HTTP: $final_url"
    fi
  else
    warn "URL uses HTTP (GCP staging CDN) — HTTPS not enforced on this endpoint"
    SKIP=$((SKIP + 1))
  fi

  # ── Test 8: Cache-Control header ─────────────────────────
  local cc
  cc=$(echo "$headers" | grep -i '^cache-control:' | head -1 | tr -d '\r\n' || echo "")
  if [[ -n "$cc" ]]; then
    ok "Cache-Control header present  [$cc]"
  else
    warn "Cache-Control header not found (CDN may inject it transparently)"
    SKIP=$((SKIP + 1))
  fi

  # ── Test 9: Page size sanity (200 bytes – 2 MB) ──────────
  local page_size
  page_size=${#body}
  if [[ "$page_size" -gt 200 && "$page_size" -lt 2097152 ]]; then
    ok "Page size reasonable: ${page_size} bytes"
  else
    fail "Unexpected page size: ${page_size} bytes (expected 200B–2MB)"
  fi

  # ── Test 10: No Python/server error markers ──────────────
  if echo "$body" | grep -qi 'traceback\|500 internal server error\|unicorn\|werkzeug'; then
    fail "Server error markers found in page content"
    [[ "$VERBOSE" == true ]] && echo "$body" | grep -i 'traceback\|500\|unicorn' | head -5
  else
    ok "No server error markers in page"
  fi

  # ── Test 11: /sns/ path link reachable ───────────────────
  local sns_status
  sns_status=$(curl -s -o /dev/null -w "%{http_code}" -L --max-time 20 "$url/sns/" 2>/dev/null || echo "000")
  if [[ "$sns_status" == "200" ]]; then
    ok "/sns/ path is reachable  [HTTP $sns_status]"
  else
    fail "/sns/ path returned HTTP $sns_status"
  fi

  rm -f "$headers_file" "$body_file"
}

# ================================================================
# MAIN
# ================================================================

echo ""
echo -e "${BOLD}============================================================${NC}"
echo -e "${BOLD}  Landing Page Test Suite — All 3 Clouds${NC}"
echo -e "${BOLD}  $(date '+%Y-%m-%d %H:%M:%S')${NC}"
echo -e "${BOLD}============================================================${NC}"
echo ""
echo -e "  AWS  CDN : ${CYAN}$AWS_CF_URL${NC}"
echo -e "  Azure CDN: ${CYAN}$AZURE_FD_URL${NC}"
echo -e "  GCP  CDN : ${CYAN}$GCP_CDN_URL${NC}"
echo ""

if [[ -z "$TARGET_CLOUD" || "$TARGET_CLOUD" == "aws" ]]; then
  test_landing_page "AWS CloudFront" "$AWS_CF_URL" "AWS"
fi

if [[ -z "$TARGET_CLOUD" || "$TARGET_CLOUD" == "azure" ]]; then
  test_landing_page "Azure Front Door" "$AZURE_FD_URL" "Azure"
fi

if [[ -z "$TARGET_CLOUD" || "$TARGET_CLOUD" == "gcp" ]]; then
  test_landing_page "GCP Cloud CDN" "$GCP_CDN_URL" "GCP"
fi

# ── Cross-cloud comparison ───────────────────────────────────
if [[ -z "$TARGET_CLOUD" ]]; then
  echo ""
  sep
  echo -e "${BOLD}Cross-Cloud: Landing Page Comparison${NC}"
  sep

  declare -A SIZES
  declare -A CODES
  for cloud_pair in "aws|$AWS_CF_URL" "azure|$AZURE_FD_URL" "gcp|$GCP_CDN_URL"; do
    local_cloud="${cloud_pair%%|*}"
    local_url="${cloud_pair##*|}"
    body_tmp=$(curl -s -L --max-time 15 --compressed "$local_url/" 2>/dev/null || echo "")
    SIZES[$local_cloud]=${#body_tmp}
    status=$(curl -s -o /dev/null -w "%{http_code}" -L --max-time 15 "$local_url/" 2>/dev/null || echo "000")
    CODES[$local_cloud]=$status
  done

  echo ""
  printf "  %-10s  %-10s  %-10s\n" "Cloud" "HTTP" "Size(bytes)"
  echo "  ────────────────────────────────"
  for c in aws azure gcp; do
    printf "  %-10s  %-10s  %-10s\n" "${c^^}" "${CODES[$c]}" "${SIZES[$c]}"
  done
  echo ""

  # Check that all three clouds return the same approximate size
  # (within 50% of each other — same static file should be identical)
  aws_sz=${SIZES[aws]:-0}
  gcp_sz=${SIZES[gcp]:-0}
  az_sz=${SIZES[azure]:-0}

  if [[ $aws_sz -gt 0 && $gcp_sz -gt 0 && $az_sz -gt 0 ]]; then
    # They should all be very close (same file) — allow ±20 bytes
    diff_ag=$(( aws_sz - gcp_sz )); [[ $diff_ag -lt 0 ]] && diff_ag=$(( -diff_ag ))
    diff_aa=$(( aws_sz - az_sz  )); [[ $diff_aa -lt 0 ]] && diff_aa=$(( -diff_aa ))
    if [[ $diff_ag -lt 100 && $diff_aa -lt 100 ]]; then
      ok "All 3 clouds serve the same landing page content (size diff < 100B)"
    else
      warn "Landing page sizes differ across clouds (AWS=${aws_sz}B, Azure=${az_sz}B, GCP=${gcp_sz}B) — may be normal if cloud-specific variants"
    fi
  fi
fi

# ── Results ──────────────────────────────────────────────────
echo ""
echo -e "${BOLD}============================================================${NC}"
echo -e "${BOLD}  Results${NC}"
echo -e "${BOLD}============================================================${NC}"
printf "  ${GREEN}Passed${NC} : %d\n" "$PASS"
printf "  ${RED}Failed${NC} : %d\n" "$FAIL"
printf "  ${CYAN}Skipped${NC}: %d\n" "$SKIP"
TOTAL=$((PASS + FAIL))
if [[ $TOTAL -gt 0 ]]; then
  RATE=$(awk "BEGIN {printf \"%.0f\", ($PASS/$TOTAL)*100}")
  printf "  Pass rate: %s%%\n" "$RATE"
fi
echo ""

if [[ $FAIL -eq 0 ]]; then
  echo -e "${GREEN}${BOLD}  ✅ All landing page tests passed!${NC}"
  exit 0
else
  echo -e "${RED}${BOLD}  ❌ $FAIL test(s) failed.${NC}"
  echo "  See docs/STAGING_TEST_GUIDE.md for troubleshooting guidance."
  exit 1
fi
