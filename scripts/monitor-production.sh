#!/bin/bash
# ============================================================================
# PRODUCTION Environment Continuous Health Monitoring
# ============================================================================
# Monitors all 3 cloud production endpoints for availability and latency.
# 
# Features:
#   - Configurable check interval (5 min default, 0 = single run)
#   - Tracks endpoint response times and HTTP status codes
#   - Persistent logging to log file
#   - Failure counting and threshold alerts
#   - Color-coded console output
#
# Usage:
#   ./scripts/monitor-production.sh [--interval SECONDS] [--log-file PATH]
#
# Examples:
#   # Single run (interval=0)
#   ./scripts/monitor-production.sh
#
#   # Continuous monitoring every 10 minutes
#   ./scripts/monitor-production.sh --interval 600
#
#   # Custom log file
#   ./scripts/monitor-production.sh --interval 300 --log-file /var/log/app-monitor.log
# ============================================================================

set -u
IFS=$'\n\t'

# ── Color codes ────────────────────────────────────────────────────────
readonly RED='\033[0;31m'
readonly GREEN='\033[0;32m'
readonly YELLOW='\033[1;33m'
readonly CYAN='\033[0;36m'
readonly NC='\033[0m' # No Color

# ── Configuration ──────────────────────────────────────────────────────
INTERVAL=${INTERVAL:-300}        # Default: 5 minutes
LOG_FILE="${LOG_FILE:-logs/production-monitoring.log}"
FAILURE_THRESHOLD=${FAILURE_THRESHOLD:-3}  # Alert after N consecutive failures
MAX_RESPONSE_TIME=5000            # milliseconds (alert if > 5 sec)

# ── Production Endpoints ───────────────────────────────────────────────
declare -A ENDPOINTS=(
  ["AWS Frontend"]="https://www.aws.ashnova.jp/"
  ["AWS API"]="https://qkzypr32af.execute-api.ap-northeast-1.amazonaws.com/health"
  ["Azure Function API"]="https://multicloud-auto-deploy-production-func-cfdne7ecbngnh0d0.japaneast-01.azurewebsites.net/api/health"
  ["GCP Frontend"]="https://www.gcp.ashnova.jp/"
  ["GCP Cloud Run API"]="https://multicloud-auto-deploy-production-api-son5b3ml7a-an.a.run.app/health"
)

# Track consecutive failures per endpoint
declare -A FAILURE_COUNT=()
for endpoint in "${!ENDPOINTS[@]}"; do
  FAILURE_COUNT["$endpoint"]=0
done

# ── Functions ──────────────────────────────────────────────────────────

die() {
  echo -e "${RED}ERROR: $*${NC}" >&2
  exit 1
}

log() {
  local level="$1"
  shift
  local message="$*"
  local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
  
  # Log to file
  mkdir -p "$(dirname "$LOG_FILE")"
  echo "[$timestamp] [$level] $message" >> "$LOG_FILE"
  
  # Log to console (info and error only)
  case "$level" in
    INFO|ERROR|WARN) echo -e "${CYAN}[$timestamp]${NC} [$level] $message" ;;
    DEBUG) [[ "${DEBUG:-0}" == "1" ]] && echo "[$timestamp] [$level] $message" ;;
  esac
}

check_endpoint() {
  local name="$1"
  local url="$2"
  local http_code
  local response_time
  local start_time
  local end_time
  
  start_time=$(date +%s%N)
  http_code=$(curl -s -o /dev/null -w "%{http_code}" "$url" 2>/dev/null || echo "000")
  end_time=$(date +%s%N)
  
  # Calculate response time in milliseconds
  response_time=$(( (end_time - start_time) / 1000000 ))
  
  # Determine status
  local status="PASS"
  local color="$GREEN"
  
  if [[ "$http_code" != "200" ]]; then
    status="FAIL"
    color="$RED"
    ((FAILURE_COUNT["$name"]++))
  elif [[ $response_time -gt $MAX_RESPONSE_TIME ]]; then
    status="SLOW"
    color="$YELLOW"
    ((FAILURE_COUNT["$name"]++))
  else
    FAILURE_COUNT["$name"]=0
  fi
  
  # Log result
  local log_level="INFO"
  [[ "$status" == "FAIL" ]] && log_level="ERROR"
  [[ "$status" == "SLOW" ]] && log_level="WARN"
  
  log "$log_level" "$name: $status (HTTP $http_code, ${response_time}ms)"
  
  # Console output
  printf "${color}[%-3s]${NC} %-25s HTTP %-3s (%4dms) " "$status" "$name:" "$http_code" "$response_time"
  
  # Failure count alert
  if [[ ${FAILURE_COUNT["$name"]} -ge $FAILURE_THRESHOLD ]]; then
    printf "${RED}⚠️ %d consecutive failures${NC}" "${FAILURE_COUNT["$name"]}"
  fi
  
  printf "\n"
  
  # Return 0 if pass, 1 if fail
  [[ "$status" == "PASS" ]]
}

check_all_endpoints() {
  local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
  local total=0
  local passed=0
  
  echo -e "\n${CYAN}════════════════════════════════════════════════════════════${NC}"
  echo -e "${CYAN}PRODUCTION MONITORING — $timestamp${NC}"
  echo -e "${CYAN}════════════════════════════════════════════════════════════${NC}\n"
  
  log "INFO" "════════ Health Check Cycle Started ════════"
  
  for endpoint in "${!ENDPOINTS[@]}"; do
    url="${ENDPOINTS[$endpoint]}"
    ((total++))
    
    if check_endpoint "$endpoint" "$url"; then
      ((passed++))
    fi
  done
  
  # Summary
  local pass_rate=$((passed * 100 / total))
  local status_color="$GREEN"
  [[ $pass_rate -lt 100 ]] && status_color="$RED"
  
  echo ""
  echo -e "${status_color}Summary: $passed/$total endpoints operational (${pass_rate}%)${NC}"
  
  log "INFO" "Health Check Cycle Completed. Status: $passed/$total (${pass_rate}%)"
  
  # Return fail if not all passed
  [[ $passed -eq $total ]]
}

print_help() {
  cat <<'EOF'
usage: monitor-production.sh [--interval SECONDS] [--log-file PATH]

Options:
  --interval SECONDS    Check interval in seconds (default: 300 = 5 min)
                        Use 0 for single run (no loop)
  --log-file PATH       Log file path (default: logs/production-monitoring.log)
  --help                Show this help message

Examples:
  # Single run
  ./scripts/monitor-production.sh

  # Continuous monitoring every 10 minutes
  ./scripts/monitor-production.sh --interval 600

  # Custom log file
  ./scripts/monitor-production.sh --log-file /var/log/app.log

Environment Variables:
  INTERVAL              Override check interval
  LOG_FILE              Override log file path
  FAILURE_THRESHOLD     Alert after N failures (default: 3)
EOF
}

# ── Main ───────────────────────────────────────────────────────────────

# Parse arguments
while [[ $# -gt 0 ]]; do
  case "$1" in
    --interval)     INTERVAL="$2"; shift 2 ;;
    --log-file)     LOG_FILE="$2"; shift 2 ;;
    --help|-h)      print_help; exit 0 ;;
    *)              die "Unknown option: $1" ;;
  esac
done

# Validation
if ! command -v curl >/dev/null 2>&1; then
  die "curl is required but not installed"
fi

log "INFO" "PRODUCTION MONITORING STARTED"
log "INFO" "Configuration: interval=${INTERVAL}s, log_file=$LOG_FILE, threshold=${FAILURE_THRESHOLD}"
log "INFO" "Monitoring ${#ENDPOINTS[@]} endpoints"

# Single run or continuous loop?
if [[ $INTERVAL -eq 0 ]]; then
  # Single run
  check_all_endpoints
  exit $?
else
  # Continuous loop
  while true; do
    check_all_endpoints
    
    if [[ $INTERVAL -gt 0 ]]; then
      echo -e "\n${CYAN}Next check in ${INTERVAL}s...${NC}"
      sleep "$INTERVAL"
    else
      break
    fi
  done
fi
