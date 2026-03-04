#!/bin/bash
# Continuous monitoring script for staging environment endpoints
# Usage: ./scripts/monitor-staging.sh [--interval SECONDS] [--log-file PATH]

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INTERVAL=300  # Default: 5 minutes
LOG_FILE="${SCRIPT_DIR}/../logs/staging-monitoring.log"
TIMESTAMP_FMT="+%Y-%m-%d %H:%M:%S"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'  # No Color

# Parse arguments
while [[ $# -gt 0 ]]; do
  case "$1" in
    -i|--interval)
      INTERVAL="$2"
      shift 2
      ;;
    -l|--log-file)
      LOG_FILE="$2"
      shift 2
      ;;
    -h|--help)
      echo "Usage: $0 [OPTIONS]"
      echo ""
      echo "Options:"
      echo "  -i, --interval SECONDS    Check interval (default: 300 seconds)"
      echo "  -l, --log-file PATH       Log file path (default: logs/staging-monitoring.log)"
      echo "  -h, --help                Show this help message"
      exit 0
      ;;
    *)
      echo "Unknown option: $1" >&2
      exit 1
      ;;
  esac
done

# Ensure log directory exists
mkdir -p "$(dirname "$LOG_FILE")"

# Monitoring endpoints
declare -A ENDPOINTS=(
  # AWS
  ["AWS Frontend"]="http://multicloud-auto-deploy-staging-frontend.s3-website-ap-northeast-1.amazonaws.com/"
  ["AWS API"]="https://z42qmqdqac.execute-api.ap-northeast-1.amazonaws.com/health"
  
  # Azure
  ["Azure Storage"]="https://mcadwebd45ihd.z11.web.core.windows.net/"
  ["Azure API"]="https://multicloud-auto-deploy-staging-func-d8a2guhfere0etcq.japaneast-01.azurewebsites.net/api/health"
  
  # GCP
  ["GCP Cloud Run"]="https://multicloud-auto-deploy-staging-api-son5b3ml7a-an.a.run.app/"
)

# Thresholds
TIMEOUT=10
EXPECTED_CODE=200
FAIL_THRESHOLD=2  # Allow 2 consecutive failures before alerting

declare -A FAILURE_COUNTS=()

# Initialize failure counts
for endpoint in "${!ENDPOINTS[@]}"; do
  FAILURE_COUNTS["$endpoint"]=0
done

check_endpoint() {
  local name="$1"
  local url="$2"
  local status
  
  status=$(curl -s -o /dev/null -w "%{http_code}" --max-time "$TIMEOUT" "$url" 2>/dev/null || echo "000")
  
  echo "$status"
}

log_message() {
  local level="$1"
  local message="$2"
  local timestamp
  timestamp=$(date "$TIMESTAMP_FMT")
  
  local log_entry="[$timestamp] [$level] $message"
  echo "$log_entry" >> "$LOG_FILE"
  
  case "$level" in
    ERROR)
      echo -e "${RED}[ERROR]${NC} $message"
      ;;
    WARN)
      echo -e "${YELLOW}[WARN]${NC} $message"
      ;;
    INFO)
      echo -e "${BLUE}[INFO]${NC} $message"
      ;;
    OK)
      echo -e "${GREEN}[OK]${NC} $message"
      ;;
  esac
}

run_check() {
  local timestamp
  timestamp=$(date "$TIMESTAMP_FMT")
  
  echo ""
  echo -e "${BLUE}========================================${NC}"
  echo -e "Monitor Check: ${BLUE}$timestamp${NC}"
  echo -e "${BLUE}========================================${NC}"
  
  local all_ok=true
  
  for endpoint in "${!ENDPOINTS[@]}"; do
    local url="${ENDPOINTS[$endpoint]}"
    local status
    status=$(check_endpoint "$endpoint" "$url")
    
    if [[ "$status" == "$EXPECTED_CODE" ]]; then
      log_message "OK" "$endpoint returned HTTP $status"
      FAILURE_COUNTS["$endpoint"]=0
    else
      FAILURE_COUNTS["$endpoint"]=$((FAILURE_COUNTS["$endpoint"] + 1))
      log_message "WARN" "$endpoint returned HTTP $status (failures: ${FAILURE_COUNTS[$endpoint]}/$FAIL_THRESHOLD)"
      all_ok=false
      
      if [[ ${FAILURE_COUNTS["$endpoint"]} -ge $FAIL_THRESHOLD ]]; then
        log_message "ERROR" "$endpoint CRITICAL - $FAIL_THRESHOLD consecutive failures"
      fi
    fi
  done
  
  if [[ "$all_ok" == true ]]; then
    log_message "INFO" "All endpoints healthy"
  else
    log_message "WARN" "Some endpoints degraded - see above"
  fi
}

# Main monitoring loop
log_message "INFO" "Staging monitoring started (interval: ${INTERVAL}s)"

while true; do
  run_check
  
  if [[ $INTERVAL -gt 0 ]]; then
    echo ""
    echo "Next check in $INTERVAL seconds... (Press Ctrl+C to stop)"
    sleep "$INTERVAL"
  else
    break
  fi
done
