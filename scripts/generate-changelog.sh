#!/bin/bash
# ========================================
# Script Name: generate-changelog.sh
# Description: Generate CHANGELOG.md from Git History
# Author: PLAYER1-r7
# Created: 2026-02-15
# Last Modified: 2026-02-15
# Version: 1.0.0
# ========================================
#
# Usage: ./scripts/generate-changelog.sh [output-file]
#
# Description:
#   Generates a CHANGELOG.md file from git commit history.
#   Uses Conventional Commits format for categorization.
#
# Parameters:
#   $1 - Output file path (default: CHANGELOG.md)
#
# Commit Categories:
#   - feat: New features
#   - fix: Bug fixes
#   - docs: Documentation changes
#   - style: Code style changes
#   - refactor: Code refactoring
#   - perf: Performance improvements
#   - test: Test changes
#   - chore: Build/tooling changes
#
# Prerequisites:
#   - Git repository with commit history
#
# Exit Codes:
#   0 - CHANGELOG generated successfully
#   1 - Generation failed
#
# ========================================

set -e

# Configuration
OUTPUT_FILE="${1:-CHANGELOG.md}"
REPO_NAME="multicloud-auto-deploy"

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  Generating CHANGELOG from Git History${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Get repository info
REPO_URL=$(git config --get remote.origin.url | sed 's/\.git$//')
CURRENT_BRANCH=$(git branch --show-current)

# Create temporary file for processing
TEMP_FILE=$(mktemp)

# Function to output commits for a specific date
output_commits_for_date() {
    local date=$1
    
    echo "" >> "$OUTPUT_FILE"
    echo "## $date" >> "$OUTPUT_FILE"
    echo "" >> "$OUTPUT_FILE"
    
    # Output in specific order
    if [ -n "${commits_by_type[feat]}" ]; then
        echo "### ✨ Features" >> "$OUTPUT_FILE"
        echo "" >> "$OUTPUT_FILE"
        echo "${commits_by_type[feat]}" >> "$OUTPUT_FILE"
        echo "" >> "$OUTPUT_FILE"
    fi
    
    if [ -n "${commits_by_type[fix]}" ]; then
        echo "### 🐛 Bug Fixes" >> "$OUTPUT_FILE"
        echo "" >> "$OUTPUT_FILE"
        echo "${commits_by_type[fix]}" >> "$OUTPUT_FILE"
        echo "" >> "$OUTPUT_FILE"
    fi
    
    if [ -n "${commits_by_type[docs]}" ]; then
        echo "### 📚 Documentation" >> "$OUTPUT_FILE"
        echo "" >> "$OUTPUT_FILE"
        echo "${commits_by_type[docs]}" >> "$OUTPUT_FILE"
        echo "" >> "$OUTPUT_FILE"
    fi
    
    if [ -n "${commits_by_type[refactor]}" ]; then
        echo "### ♻️ Refactoring" >> "$OUTPUT_FILE"
        echo "" >> "$OUTPUT_FILE"
        echo "${commits_by_type[refactor]}" >> "$OUTPUT_FILE"
        echo "" >> "$OUTPUT_FILE"
    fi
    
    if [ -n "${commits_by_type[perf]}" ]; then
        echo "### ⚡ Performance" >> "$OUTPUT_FILE"
        echo "" >> "$OUTPUT_FILE"
        echo "${commits_by_type[perf]}" >> "$OUTPUT_FILE"
        echo "" >> "$OUTPUT_FILE"
    fi
    
    if [ -n "${commits_by_type[test]}" ]; then
        echo "### 🧪 Tests" >> "$OUTPUT_FILE"
        echo "" >> "$OUTPUT_FILE"
        echo "${commits_by_type[test]}" >> "$OUTPUT_FILE"
        echo "" >> "$OUTPUT_FILE"
    fi
    
    if [ -n "${commits_by_type[style]}" ]; then
        echo "### 💄 Styling" >> "$OUTPUT_FILE"
        echo "" >> "$OUTPUT_FILE"
        echo "${commits_by_type[style]}" >> "$OUTPUT_FILE"
        echo "" >> "$OUTPUT_FILE"
    fi
    
    if [ -n "${commits_by_type[chore]}" ]; then
        echo "### 🔧 Chores" >> "$OUTPUT_FILE"
        echo "" >> "$OUTPUT_FILE"
        echo "${commits_by_type[chore]}" >> "$OUTPUT_FILE"
        echo "" >> "$OUTPUT_FILE"
    fi
    
    if [ -n "${commits_by_type[other]}" ]; then
        echo "### 📝 Other Changes" >> "$OUTPUT_FILE"
        echo "" >> "$OUTPUT_FILE"
        echo "${commits_by_type[other]}" >> "$OUTPUT_FILE"
        echo "" >> "$OUTPUT_FILE"
    fi
}

# Generate header
cat > "$OUTPUT_FILE" << EOF
# Changelog

All notable changes to the **$REPO_NAME** project are documented in this file.

This changelog is automatically generated from git commit history using [Conventional Commits](https://www.conventionalcommits.org/) format.

**Repository**: [$REPO_URL]($REPO_URL)  
**Branch**: \`$CURRENT_BRANCH\`  
**Generated**: $(date '+%Y-%m-%d %H:%M:%S')

---

EOF

# Get all commits with format: hash|date|subject|author
git log --pretty=format:"%h|%ad|%s|%an" --date=short --reverse > "$TEMP_FILE"

# Process commits by date
current_date=""
declare -A commits_by_type

while IFS='|' read -r hash date subject author; do
    # Check if date changed
    if [ "$date" != "$current_date" ]; then
        # Output previous date's commits if any
        if [ -n "$current_date" ]; then
            output_commits_for_date "$current_date"
        fi
        
        # Reset for new date
        current_date="$date"
        unset commits_by_type
        declare -A commits_by_type
    fi
    
    # Parse commit type using conventional commits
    commit_type="other"
    commit_msg="$subject"
    
    if [[ "$subject" =~ ^feat:\ (.+)$ ]] || [[ "$subject" =~ ^feat\(.*\):\ (.+)$ ]]; then
        commit_type="feat"
        commit_msg="${BASH_REMATCH[1]}"
    elif [[ "$subject" =~ ^fix:\ (.+)$ ]] || [[ "$subject" =~ ^fix\(.*\):\ (.+)$ ]]; then
        commit_type="fix"
        commit_msg="${BASH_REMATCH[1]}"
    elif [[ "$subject" =~ ^docs:\ (.+)$ ]] || [[ "$subject" =~ ^docs\(.*\):\ (.+)$ ]]; then
        commit_type="docs"
        commit_msg="${BASH_REMATCH[1]}"
    elif [[ "$subject" =~ ^style:\ (.+)$ ]] || [[ "$subject" =~ ^style\(.*\):\ (.+)$ ]]; then
        commit_type="style"
        commit_msg="${BASH_REMATCH[1]}"
    elif [[ "$subject" =~ ^refactor:\ (.+)$ ]] || [[ "$subject" =~ ^refactor\(.*\):\ (.+)$ ]]; then
        commit_type="refactor"
        commit_msg="${BASH_REMATCH[1]}"
    elif [[ "$subject" =~ ^perf:\ (.+)$ ]] || [[ "$subject" =~ ^perf\(.*\):\ (.+)$ ]]; then
        commit_type="perf"
        commit_msg="${BASH_REMATCH[1]}"
    elif [[ "$subject" =~ ^test:\ (.+)$ ]] || [[ "$subject" =~ ^test\(.*\):\ (.+)$ ]]; then
        commit_type="test"
        commit_msg="${BASH_REMATCH[1]}"
    elif [[ "$subject" =~ ^chore:\ (.+)$ ]] || [[ "$subject" =~ ^chore\(.*\):\ (.+)$ ]]; then
        commit_type="chore"
        commit_msg="${BASH_REMATCH[1]}"
    fi
    
    # Store commit
    if [ -z "${commits_by_type[$commit_type]}" ]; then
        commits_by_type[$commit_type]="- $commit_msg ([\`$hash\`]($REPO_URL/commit/$hash))"
    else
        commits_by_type[$commit_type]="${commits_by_type[$commit_type]}
- $commit_msg ([\`$hash\`]($REPO_URL/commit/$hash))"
    fi
    
done < "$TEMP_FILE"

# Output last date's commits
if [ -n "$current_date" ]; then
    output_commits_for_date "$current_date"
fi

# Add footer
cat >> "$OUTPUT_FILE" << EOF

---

## Legend

- ✨ **Features**: New functionality
- 🐛 **Bug Fixes**: Bug fixes and corrections
- 📚 **Documentation**: Documentation improvements
- ♻️ **Refactoring**: Code refactoring
- ⚡ **Performance**: Performance improvements
- 🧪 **Tests**: Test additions or modifications
- 💄 **Styling**: Code style and formatting
- 🔧 **Chores**: Build, tooling, and maintenance

---

**Note**: This changelog is automatically generated. For more details, see the [commit history]($REPO_URL/commits/$CURRENT_BRANCH).
EOF

# Cleanup
rm -f "$TEMP_FILE"

echo -e "${GREEN}✓ CHANGELOG generated successfully: $OUTPUT_FILE${NC}"
echo ""
echo "Summary:"
TOTAL_COMMITS=$(git rev-list --count HEAD)
echo "  Total commits: $TOTAL_COMMITS"
echo "  Output file: $OUTPUT_FILE"
echo "  File size: $(wc -c < "$OUTPUT_FILE") bytes"
echo ""
