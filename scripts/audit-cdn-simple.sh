#!/bin/bash

# T8: CDN Cache Strategy Audit - Simplified
# Analyze current cache configuration across AWS/Azure/GCP

echo ""
echo "========================================"
echo "T8: CDN Cache Strategy Audit"
echo "========================================"
echo ""

# === GCP Cloud CDN Config ===

echo "ℹ Phase 1: GCP Cloud CDN Configuration"
echo ""

if command -v gcloud &> /dev/null; then
    echo "Fetching GCP backend bucket config..."

    GCP_CONFIG=$(gcloud compute backend-buckets describe \
      "multicloud-auto-deploy-production-cdn-backend" \
      --project="ashnova" \
      --format=json 2>/dev/null)

    if [ ! -z "$GCP_CONFIG" ]; then
        echo "✅ GCP Cloud CDN configuration:"
        echo ""
        echo "CDN Enabled: $(echo "$GCP_CONFIG" | jq -r '.enableCdn')"
        echo "Cache Mode: $(echo "$GCP_CONFIG" | jq -r '.cdnPolicy.cacheMode // "cache_all_static"')"
        echo "Default TTL: $(echo "$GCP_CONFIG" | jq -r '.cdnPolicy.defaultTtl // 3600')s"
        echo "Max TTL: $(echo "$GCP_CONFIG" | jq -r '.cdnPolicy.maxTtl // 86400')s"
        echo ""
    else
        echo "❌ Could not fetch GCP config"
    fi
else
    echo "❌ gcloud CLI not found"
fi

# === AWS CloudFront Config ===

echo "ℹ Phase 2: AWS CloudFront Configuration"
echo ""

if command -v aws &> /dev/null; then
    echo "Checking AWS CloudFront distributions..."

    DISTRIBUTIONS=$(aws cloudfront list-distributions --query 'DistributionList.Items[0]' --output json 2>/dev/null)

    if [ ! -z "$DISTRIBUTIONS" ] && [ "$DISTRIBUTIONS" != "null" ]; then
        DIST_ID=$(echo "$DISTRIBUTIONS" | jq -r '.Id')
        echo "✅ CloudFront Distribution ID: $DIST_ID"
        echo "Domain: $(echo "$DISTRIBUTIONS" | jq -r '.DomainName')"
        echo "Status: $(echo "$DISTRIBUTIONS" | jq -r '.Status')"
        echo ""
    else
        echo "⚠️  No CloudFront distributions found"
    fi
else
    echo "❌ AWS CLI not found"
fi

# === Summary ===

echo ""
echo "========================================"
echo "T8 Optimization Recommendations"
echo "========================================"
echo ""

echo "Priority 1: Static Assets (CSS, JS, Images)"
echo "├─ Recommended TTL: 2592000s (30 days)"
echo "└─ Impact: Better performance for repeat visitors"
echo ""

echo "Priority 2: HTML Documents"
echo "├─ Recommended TTL: 300s (5 min)"
echo "└─ Impact: Fresh content while using cache"
echo ""

echo "Priority 3: Query String Optimization"
echo "├─ Remove: utm_*, fbclid, ga_* from cache key"
echo "└─ Impact: +20-30% cache hit rate"
echo ""

echo "Priority 4: Compression"
echo "├─ Enable: gzip, brotli (text files)"
echo "└─ Impact: 60-80% size reduction"
echo ""

echo "Implementation:"
echo "└─ See: docs/PHASE2_OPTIMIZATION_PLAN.md (T8 section)"
echo ""
