#!/bin/bash
################################################################################
# Script: watch-deployment.sh
# Description: Monitor GitHub Actions deployments in real-time
# Usage: ./scripts/watch-deployment.sh [branch] [interval]
# Example: ./scripts/watch-deployment.sh main 10
################################################################################

set -euo pipefail

# Configuration
REPO_OWNER="PLAYER1-r7"
REPO_NAME="multicloud-auto-deploy"
BRANCH="${1:-main}"
INTERVAL="${2:-10}"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Status symbols
SUCCESS="✓"
FAILURE="✗"
IN_PROGRESS="⏳"
QUEUED="⏸"

echo -e "${BLUE}🔍 Watching deployments on branch: ${BRANCH}${NC}"
echo -e "${BLUE}🔄 Refresh interval: ${INTERVAL}s${NC}"
echo -e "${YELLOW}Press Ctrl+C to stop${NC}"
echo ""

while true; do
    clear
    echo "═══════════════════════════════════════════════════════════════"
    echo "   Multi-Cloud Deployment Monitor"
    echo "   Branch: $BRANCH | $(date '+%Y-%m-%d %H:%M:%S')"
    echo "═══════════════════════════════════════════════════════════════"
    echo ""

    # Fetch latest workflow runs
    RESPONSE=$(curl -s "https://api.github.com/repos/${REPO_OWNER}/${REPO_NAME}/actions/runs?branch=${BRANCH}&per_page=5")

    # Check if API call was successful
    if echo "$RESPONSE" | jq -e '.workflow_runs' > /dev/null 2>&1; then
        echo "$RESPONSE" | jq -r '.workflow_runs[] | 
            {
                status: .status,
                conclusion: .conclusion,
                name: .name,
                commit: .head_sha[0:7],
                created: .created_at,
                url: .html_url
            } | 
            if .status == "completed" then
                if .conclusion == "success" then
                    "[\u001b[32m✓\u001b[0m] \(.name)\n   Status: \u001b[32msuccess\u001b[0m | Commit: \(.commit) | \(.created)\n   URL: \(.url)\n"
                elif .conclusion == "failure" then
                    "[\u001b[31m✗\u001b[0m] \(.name)\n   Status: \u001b[31mfailure\u001b[0m | Commit: \(.commit) | \(.created)\n   URL: \(.url)\n"
                else
                    "[\u001b[33m○\u001b[0m] \(.name)\n   Status: \(.conclusion // "unknown") | Commit: \(.commit) | \(.created)\n   URL: \(.url)\n"
                end
            elif .status == "in_progress" then
                "[\u001b[34m⏳\u001b[0m] \(.name)\n   Status: \u001b[34min progress\u001b[0m | Commit: \(.commit) | \(.created)\n   URL: \(.url)\n"
            else
                "[⏸] \(.name)\n   Status: \(.status) | Commit: \(.commit) | \(.created)\n   URL: \(.url)\n"
            end
        '
        
        echo "═══════════════════════════════════════════════════════════════"
        echo -e "${YELLOW}Next refresh in ${INTERVAL}s...${NC}"
    else
        echo -e "${RED}Error: Failed to fetch workflow runs from GitHub API${NC}"
        echo "$RESPONSE" | jq '.' 2>/dev/null || echo "$RESPONSE"
        echo ""
        echo "═══════════════════════════════════════════════════════════════"
        echo -e "${YELLOW}Retrying in ${INTERVAL}s...${NC}"
    fi

    sleep "$INTERVAL"
done
