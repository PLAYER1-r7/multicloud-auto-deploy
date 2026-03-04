#!/bin/bash

# T7: Lambda/Cloud Functions Coldstart Analysis
# Measure baseline cold start latency across AWS/Azure/GCP
# Usage: bash scripts/analyze-coldstart.sh [--days N] [--function-name NAME]

set -o pipefail

# === Configuration ===
DAYS=${1:-7}
GCP_FUNCTION="multicloud-auto-deploy-production-api"
GCP_REGION="asia-northeast1"
GCP_PROJECT="ashnova"
AWS_FUNCTION_PATTERN="multicloud-auto-deploy-api"
AWS_REGION="ap-northeast-1"

# === Colors ===
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() {
    echo -e "${BLUE}ℹ ${1}${NC}"
}

log_success() {
    echo -e "${GREEN}✅ ${1}${NC}"
}

log_warn() {
    echo -e "${YELLOW}⚠️  ${1}${NC}"
}

log_error() {
    echo -e "${RED}❌ ${1}${NC}"
}

# === Helper Functions ===

# Calculate percentiles from array of numbers
calc_percentile() {
    local percentile=$1
    shift
    local values=("$@")
    local count=${#values[@]}

    if [ $count -eq 0 ]; then
        echo "0"
        return
    fi

    # Simple percentile calculation (90th = 0.9 * count)
    local index=$(awk "BEGIN {printf \"%.0f\", $percentile * $count / 100}")

    # Sort values and get index
    printf '%s\n' "${values[@]}" | sort -n | sed -n "$((index+1))p"
}

# === GCP Cloud Functions Analysis ===

echo ""
echo "========================================"
echo "T7: Lambda Coldstart Baseline Analysis"
echo "========================================"
echo ""

log_info "Phase 1: GCP Cloud Functions Analysis"
echo ""

# Query Cloud Logging for function execution times
log_info "Querying Cloud Logging (past $DAYS days)..."

GCP_LOGS=$(gcloud logging read \
  "resource.type=cloud_function AND resource.labels.function_name=$GCP_FUNCTION AND resource.labels.region=$GCP_REGION" \
  --project=$GCP_PROJECT \
  --limit=1000 \
  --format="json" 2>/dev/null)

if [ -z "$GCP_LOGS" ] || [ "$GCP_LOGS" == "[]" ]; then
    log_warn "No logs found for $GCP_FUNCTION in past $DAYS days"
    log_info "Attempting to fetch from recent invocations..."

    # Try alternative: check execution metrics
    EXEC_TIMES=$(gcloud monitoring read \
      --filter='resource.type="cloud_function" AND metric.type="cloudfunctions.googleapis.com/execution_times"' \
      --format="json" \
      --project=$GCP_PROJECT 2>/dev/null | jq -r '.[] | .value.double_value // empty' 2>/dev/null)
else
    # Extract execution_ms from logs
    EXEC_TIMES=$(echo "$GCP_LOGS" | jq -r '.[] | select(.jsonPayload.execution_ms) | .jsonPayload.execution_ms' 2>/dev/null)
fi

# If we got execution times, analyze them
if [ ! -z "$EXEC_TIMES" ]; then
    EXEC_ARRAY=($EXEC_TIMES)
    COUNT=${#EXEC_ARRAY[@]}

    if [ $COUNT -gt 0 ]; then
        log_success "Found $COUNT execution records"

        # Calculate statistics
        MIN=$(printf '%s\n' "${EXEC_ARRAY[@]}" | sort -n | head -1)
        MAX=$(printf '%s\n' "${EXEC_ARRAY[@]}" | sort -n | tail -1)
        AVG=$(awk -v sum="$(printf '%s\n' "${EXEC_ARRAY[@]}" | paste -sd+ | bc)" -v count=$COUNT 'BEGIN {printf "%.0f", sum/count}')
        P50=$(calc_percentile 50 "${EXEC_ARRAY[@]}")
        P95=$(calc_percentile 95 "${EXEC_ARRAY[@]}")
        P99=$(calc_percentile 99 "${EXEC_ARRAY[@]}")

        echo ""
        echo "GCP Cloud Functions ($GCP_FUNCTION):"
        echo "┌─── Execution Time Statistics ───────"
        echo "│ Sample Count:  $COUNT invocations"
        echo "│ Min:           ${MIN}ms"
        echo "│ Max:           ${MAX}ms"
        echo "│ Average:       ${AVG}ms"
        echo "│ P50 (Median):  ${P50}ms"
        echo "│ P95:           ${P95}ms"
        echo "│ P99:           ${P99}ms"
        echo "└────────────────────────────────────"

        # Coldstart detection heuristic:
        # Cold starts typically >3x slower than warm starts
        # Usually >2000ms for Python runtime
        COLDSTART_THRESHOLD=$(awk "BEGIN {printf \"%.0f\", $AVG * 1.5}")
        ESTIMATED_COLDSTART=$(printf '%s\n' "${EXEC_ARRAY[@]}" | awk -v threshold=$COLDSTART_THRESHOLD '$1 > threshold' | wc -l)

        echo ""
        echo "Coldstart Detection (threshold: ${COLDSTART_THRESHOLD}ms):"
        echo "├─ Estimated cold starts: $ESTIMATED_COLDSTART / $COUNT"
        echo "└─ Estimated rate: $(awk "BEGIN {printf \"%.1f%%\", $ESTIMATED_COLDSTART * 100 / $COUNT}")%"
    else
        log_warn "No valid execution time data available"
    fi
else
    log_warn "Could not extract execution time metrics from logs"
fi

# === AWS Lambda Analysis ===

echo ""
log_info "Phase 2: AWS Lambda Analysis"
echo ""

log_info "Checking AWS Lambda functions..."

AWS_FUNCTIONS=$(aws lambda list-functions \
  --region $AWS_REGION \
  --query "Functions[?contains(FunctionName, 'multicloud')].FunctionName" \
  --output text 2>/dev/null)

if [ -z "$AWS_FUNCTIONS" ]; then
    log_warn "No Lambda functions found in $AWS_REGION"
else
    for FUNC in $AWS_FUNCTIONS; do
        log_info "Analyzing $FUNC..."

        FUNC_CONFIG=$(aws lambda get-function \
          --function-name "$FUNC" \
          --region $AWS_REGION \
          --query 'Configuration | {Runtime, MemorySize, Timeout, EphemeralStorageSize}' \
          --output json 2>/dev/null)

        if [ ! -z "$FUNC_CONFIG" ]; then
            echo ""
            echo "AWS Lambda ($FUNC):"
            echo "┌─── Configuration ───────────────────"
            echo "$FUNC_CONFIG" | jq -r 'to_entries[] | "│ \(.key): \(.value)"'
            echo "└────────────────────────────────────"

            # Query CloudWatch Logs for Duration metric
            DURATIONS=$(aws logs filter-log-events \
              --log-group-name "/aws/lambda/$FUNC" \
              --region $AWS_REGION \
              --query 'events[] | map(select(.message | contains("Duration")) | .message)' \
              --output text 2>/dev/null | \
              grep -oP 'Duration: \K\d+' | head -100)

            if [ ! -z "$DURATIONS" ]; then
                DURATION_ARRAY=($DURATIONS)
                COUNT=${#DURATION_ARRAY[@]}

                if [ $COUNT -gt 0 ]; then
                    log_success "Found $COUNT duration records"

                    MIN=$(printf '%s\n' "${DURATION_ARRAY[@]}" | sort -n | head -1)
                    MAX=$(printf '%s\n' "${DURATION_ARRAY[@]}" | sort -n | tail -1)
                    AVG=$(awk -v sum="$(printf '%s\n' "${DURATION_ARRAY[@]}" | paste -sd+ | bc)" -v count=$COUNT 'BEGIN {printf "%.0f", sum/count}')
                    P50=$(calc_percentile 50 "${DURATION_ARRAY[@]}")
                    P95=$(calc_percentile 95 "${DURATION_ARRAY[@]}")
                    P99=$(calc_percentile 99 "${DURATION_ARRAY[@]}")

                    echo ""
                    echo "  Execution Time (past 7 days):"
                    echo "  ├─ Sample Count:  $COUNT"
                    echo "  ├─ Min:           ${MIN}ms"
                    echo "  ├─ Max:           ${MAX}ms"
                    echo "  ├─ Average:       ${AVG}ms"
                    echo "  ├─ P50:           ${P50}ms"
                    echo "  ├─ P95:           ${P95}ms"
                    echo "  └─ P99:           ${P99}ms"
                fi
            else
                log_warn "No duration metrics found in CloudWatch Logs"
            fi
        fi
    done
fi

# === Azure Functions Analysis ===

echo ""
log_info "Phase 3: Azure Functions Analysis"
echo ""

log_warn "Azure Functions analysis requires Azure CLI authentication"
log_warn "Run: az login && az accounts set --subscription <subscription-id>"
log_warn "Then re-run this script"

# === Summary & Recommendations ===

echo ""
echo "========================================"
echo "T7 Summary & Recommendations"
echo "========================================"
echo ""

echo "Baseline Measurement Status:"
echo "├─ GCP Cloud Functions: $([ ! -z "$EXEC_TIMES" ] && echo '✅ Measured' || echo '⚠️  Pending Invocations')"
echo "├─ AWS Lambda:          $([ ! -z "$DURATIONS" ] && echo '✅ Measured' || echo '⚠️  Pending')"
echo "└─ Azure Functions:     ⚠️  Pending"
echo ""

echo "Next Steps for T7 Implementation:"
echo "1. Generate baseline metrics for each cloud"
echo "2. Identify optimization opportunities:"
echo "   └─ GCP: Increase memory allocation (coldstart depends on runtime init + code size)"
echo "   └─ AWS: Enable provisioned concurrency or adjust timeout"
echo "   └─ Azure: Use Premium plan with always-on, or reduce package size"
echo "3. Implement optimization based on cost/benefit analysis"
echo "4. Re-measure after 1 week to validate improvement"
echo ""

echo "Documentation:"
echo "└─ See: docs/PHASE2_OPTIMIZATION_PLAN.md (T7 section)"
echo ""
