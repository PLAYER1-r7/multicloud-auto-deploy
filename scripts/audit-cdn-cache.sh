#!/bin/bash

# T8: CDN Cache Strategy Audit & Optimization
# Analyze current cache configuration and hit rates across AWS/Azure/GCP
# Usage: bash scripts/audit-cdn-cache.sh

set -o pipefail

# === Configuration ===
AWS_CF_DISTRIBUTION="d1qob7569mn5nw"  # CloudFront dist ID
AZURE_CDN_PROFILE="cdn-prod"
AZURE_CDN_ENDPOINT="frontend"
AZURE_RESOURCE_GROUP="rg-production"
GCP_BACKEND_BUCKET="multicloud-auto-deploy-production-cdn-backend"
GCP_PROJECT="ashnova"

# === Colors ===
BLUE='\033[0;34m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

log_info() { echo -e "${BLUE}ℹ ${1}${NC}"; }
log_success() { echo -e "${GREEN}✅ ${1}${NC}"; }
log_warn() { echo -e "${YELLOW}⚠️  ${1}${NC}"; }
log_error() { echo -e "${RED}❌ ${1}${NC}"; }

# === AWS CloudFront Audit ===

echo ""
echo "========================================"
echo "T8: CDN Cache Strategy Audit"
echo "========================================"
echo ""

log_info "Phase 1: AWS CloudFront Configuration"
echo ""

if command -v aws &> /dev/null; then
    log_info "Fetching CloudFront distribution config..."

    CF_CONFIG=$(aws cloudfront get-distribution-config \
      --id "$AWS_CF_DISTRIBUTION" \
      --query 'DistributionConfig' \
      --output json 2>/dev/null)

    if [ ! -z "$CF_CONFIG" ]; then
        log_success "CloudFront configuration retrieved"

        echo ""
        echo "AWS CloudFront ($AWS_CF_DISTRIBUTION):"
        echo "┌─── Cache Behaviors ───────────────────────────"

        # Extract cache behaviors
        echo "$CF_CONFIG" | jq -r '.CacheBehaviors[] |
          "│ PathPattern: \(.PathPattern)
            │   CachePolicyId: \(.CachePolicyId // "default")
            │   OriginRequestPolicyId: \(.OriginRequestPolicyId // "none")
            │   ForwardedValues:
            │     QueryString: \(.ForwardedValues.QueryString)
            │     Cookies: \(.ForwardedValues.Cookies.Forward)
            │     Headers: \(.ForwardedValues.Headers.Items // [])
            │" 2>/dev/null || echo "│ (Could not parse behaviors)"

        echo "└────────────────────────────────────────────────"
        echo ""

        # Check compression
        echo "Compression Settings:"
        if echo "$CF_CONFIG" | jq -e '.Compress' &>/dev/null; then
            COMPRESS=$(echo "$CF_CONFIG" | jq '.Compress')
            echo "├─ Compress enabled: $COMPRESS"
        else
            echo "├─ Compress enabled: unknown"
        fi
        echo "└─ Compression types: gzip, deflate, brotli (AWS default)"

        # Default cache behavior
        echo ""
        echo "Default Behavior TTL:"
        if echo "$CF_CONFIG" | jq -e '.DefaultCacheBehavior.CachePolicyId' &>/dev/null; then
            POLICY=$(echo "$CF_CONFIG" | jq -r '.DefaultCacheBehavior.CachePolicyId')
            echo "├─ Policy ID: $POLICY"
            echo "└─ Min TTL: (managed by policy)"
        else
            MIN_TTL=$(echo "$CF_CONFIG" | jq '.DefaultCacheBehavior.MinTTL // 0')
            MAX_TTL=$(echo "$CF_CONFIG" | jq '.DefaultCacheBehavior.MaxTTL // 31536000')
            DEF_TTL=$(echo "$CF_CONFIG" | jq '.DefaultCacheBehavior.DefaultTTL // 86400')

            echo "├─ Min TTL: ${MIN_TTL}s"
            echo "├─ Default TTL: ${DEF_TTL}s"
            echo "└─ Max TTL: ${MAX_TTL}s"
        fi

    else
        log_error "Could not fetch CloudFront config"
    fi

    # CloudFront Metrics
    log_info "Fetching CloudFront cache metrics (past 7 days)..."

    METRICS=$(aws cloudwatch get-metric-statistics \
      --namespace AWS/CloudFront \
      --metric-name CacheHitRate \
      --dimensions Name=DistributionId,Value="$AWS_CF_DISTRIBUTION" \
      --start-time $(date -u -d '7 days ago' +%Y-%m-%dT%H:%M:%S) \
      --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
      --period 86400 \
      --statistics Average,Maximum,Minimum \
      --output json 2>/dev/null)

    if [ ! -z "$METRICS" ] && [ "$(echo "$METRICS" | jq '.Datapoints | length')" -gt 0 ]; then
        log_success "Cache metrics retrieved"

        echo ""
        echo "Cache Performance (past 7 days):"
        echo "$METRICS" | jq -r '.Datapoints[] |
          "├─ \(.Timestamp | split("T")[0]): Avg \(.Average | floor)%, Min \(.Minimum | floor)%, Max \(.Maximum | floor)%"'
        echo "└─ (Target: >90% cache hit rate)"
    else
        log_warn "No cache metrics available (limited traffic?)"
    fi

else
    log_error "AWS CLI not found"
fi

# === Azure CDN Audit ===

echo ""
log_info "Phase 2: Azure CDN Configuration"
echo ""

if command -v az &> /dev/null; then
    log_info "Fetching Azure CDN endpoint config..."

    AZURE_CONFIG=$(az cdn endpoint show \
      --name "$AZURE_CDN_ENDPOINT" \
      --profile-name "$AZURE_CDN_PROFILE" \
      --resource-group "$AZURE_RESOURCE_GROUP" \
      --query '{optimizedDeliveryType, queryStringCachingBehavior, compressionEnabled, contentTypesToCompress}' \
      --output json 2>/dev/null)

    if [ ! -z "$AZURE_CONFIG" ] && [ "$AZURE_CONFIG" != "null" ]; then
        log_success "Azure CDN configuration retrieved"

        echo ""
        echo "Azure CDN ($AZURE_CDN_PROFILE/$AZURE_CDN_ENDPOINT):"
        echo "┌─── Configuration ─────────────────────────────"
        echo "$AZURE_CONFIG" | jq -r 'to_entries[] | "│ \(.key): \(.value)"'
        echo "└────────────────────────────────────────────────"

    else
        log_warn "Could not fetch Azure CDN config (may require different auth)"
    fi

    # Azure CDN Metrics
    log_info "Fetching Azure CDN cache metrics..."

    # Note: Azure metrics require more complex querying
    log_warn "Azure CDN metrics require Azure Monitor setup (skipping)"

else
    log_warn "Azure CLI not found"
fi

# === GCP Cloud CDN Audit ===

echo ""
log_info "Phase 3: GCP Cloud CDN Configuration"
echo ""

if command -v gcloud &> /dev/null; then
    log_info "Fetching GCP backend bucket config..."

    GCP_CONFIG=$(gcloud compute backend-buckets describe \
      "$GCP_BACKEND_BUCKET" \
      --project="$GCP_PROJECT" \
      --format=json 2>/dev/null)

    if [ ! -z "$GCP_CONFIG" ]; then
        log_success "GCP Cloud CDN configuration retrieved"

        echo ""
        echo "GCP Cloud CDN ($GCP_BACKEND_BUCKET):"
        echo "┌─── Configuration ─────────────────────────────"

        # CDN enabled
        CDN_ENABLED=$(echo "$GCP_CONFIG" | jq '.enableCdn')
        echo "│ CDN Enabled: $CDN_ENABLED"

        # Cache Mode
        CACHE_MODE=$(echo "$GCP_CONFIG" | jq -r '.cdnPolicy.cacheMode // "cache_all_static"')
        echo "│ Cache Mode: $CACHE_MODE"

        # Client TTL
        CLIENT_TTL=$(echo "$GCP_CONFIG" | jq '.cdnPolicy.clientTtl // 0')
        echo "│ Client TTL: ${CLIENT_TTL}s"

        # Default TTL
        DEFAULT_TTL=$(echo "$GCP_CONFIG" | jq '.cdnPolicy.defaultTtl // 3600')
        echo "│ Default TTL: ${DEFAULT_TTL}s"

        # Max TTL
        MAX_TTL=$(echo "$GCP_CONFIG" | jq '.cdnPolicy.maxTtl // 86400')
        echo "│ Max TTL: ${MAX_TTL}s"

        # Negative caching
        NEG_CACHE=$(echo "$GCP_CONFIG" | jq '.cdnPolicy.negativeCaching')
        echo "│ Negative Caching: $NEG_CACHE"

        echo "└────────────────────────────────────────────────"

        # GCP Logging
        log_info "Analyzing GCP Cloud Logging for cache metrics..."

        # Parse recent HTTP logs for cache decisions
        GCP_LOGS=$(gcloud logging read \
          "resource.type=http_load_balancer AND jsonPayload.cacheDecision:[*]=~\"CACHE.*\"" \
          --project="$GCP_PROJECT" \
          --limit=100 \
          --format=json 2>/dev/null)

        if [ ! -z "$GCP_LOGS" ] && [ "$GCP_LOGS" != "[]" ]; then
            CACHE_HITS=$(echo "$GCP_LOGS" | jq 'map(select(.jsonPayload.statusDetails == "response_from_cache")) | length' 2>/dev/null)
            CACHE_MISSES=$(echo "$GCP_LOGS" | jq 'map(select(.jsonPayload.statusDetails != "response_from_cache")) | length' 2>/dev/null)
            TOTAL=$((CACHE_HITS + CACHE_MISSES))

            if [ $TOTAL -gt 0 ]; then
                HIT_RATE=$((CACHE_HITS * 100 / TOTAL))
                log_success "Cache metrics analyzed from $TOTAL requests"

                echo ""
                echo "Cache Statistics (recent logs):"
                echo "├─ Cache hits: $CACHE_HITS ($HIT_RATE%)"
                echo "├─ Cache misses: $CACHE_MISSES ($((100-HIT_RATE))%)"
                echo "└─ Target: >90% cache hit rate"
            else
                log_warn "No cache decisions found in recent logs"
            fi
        else
            log_warn "No cache-related logs available"
        fi

    else
        log_error "Could not fetch GCP backend bucket config"
    fi

else
    log_error "gcloud CLI not found"
fi

# === Summary & Recommendations ===

echo ""
echo "========================================"
echo "T8 Summary & Recommendations"
echo "========================================"
echo ""

echo "Cache Optimization Opportunities:"
echo ""
echo "1. Static Assets (CSS, JS, Images)"
echo "   ├─ Recommended TTL: 1 month (2592000s)"
echo "   ├─ Vary headers: Accept-Encoding"
echo "   └─ Compression: gzip, brotli"
echo ""

echo "2. HTML Index"
echo "   ├─ Recommended TTL: 5 min (300s)"
echo "   ├─ Cache-Control: public, max-age=300"
echo "   └─ stale-while-revalidate: 86400"
echo ""

echo "3. API Responses (JSON)"
echo "   ├─ Recommended Cache: NO (or private)"
echo "   ├─ Cache-Control: private, no-cache"
echo "   └─ Vary: Authorization, Accept-Encoding"
echo ""

echo "4. Query String Handling"
echo "   ├─ Stop caching UTM params (utm_*, fbclid, etc)"
echo "   ├─ Implementation: Remove from cache key"
echo "   └─ Impact: Consolidate cache entries (+30% hit rate)"
echo ""

echo "5. Compression"
echo "   ├─ Enable brotli (if not already)"
echo "   ├─ File types: text/*, application/json, image/svg+xml"
echo "   └─ Exclude: images (jpg, png, webp), binary files"
echo ""

echo "Implementation Status:"
echo "├─ AWS CloudFront: Review cache policy IDs above"
echo "├─ Azure CDN: Configure cache expiration rules"
echo "└─ GCP Cloud CDN: Modify cdnPolicy in Pulumi config"
echo ""

echo "Next Action:"
echo "└─ See: docs/PHASE2_OPTIMIZATION_PLAN.md (T8 section)"
echo "   Implementation guide with code examples"
echo ""
