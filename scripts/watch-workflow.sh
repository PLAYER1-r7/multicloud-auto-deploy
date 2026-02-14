#!/bin/bash
# Watch GitHub Actions workflow status

REPO="PLAYER1-r7/multicloud-auto-deploy"
WORKFLOW="deploy-aws.yml"

echo "================================================"
echo "GitHub Actions Workflow Monitor"
echo "================================================"
echo ""
echo "Watching: $WORKFLOW in $REPO"
echo ""

# Function to check workflow status
check_status() {
    if ! gh auth status &> /dev/null; then
        echo "⚠️  GitHub CLI not authenticated"
        echo "Please authenticate with: gh auth login"
        echo ""
        echo "Or view in browser:"
        echo "https://github.com/$REPO/actions"
        return 1
    fi
    
    echo "📋 Recent workflow runs:"
    gh run list --repo $REPO --workflow=$WORKFLOW --limit 5
    
    echo ""
    echo "💡 To view logs of a specific run:"
    echo "  gh run view <run-id> --repo $REPO --log"
    echo ""
    echo "💡 To watch a run in real-time:"
    echo "  gh run watch <run-id> --repo $REPO"
}

check_status
