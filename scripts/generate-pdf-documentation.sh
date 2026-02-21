#!/bin/bash

# ========================================
# Script Name: generate-pdf-documentation.sh
# Description: Generate comprehensive PDF documentation from all Markdown files
# Author: PLAYER1-r7
# Created: 2026-02-15
# Last Modified: 2026-02-15
# Version: 1.0.0
# ========================================
#
# Usage: ./scripts/generate-pdf-documentation.sh [output_filename]
#
# Parameters:
#   output_filename (optional) : Name of the output PDF file (default: multicloud-auto-deploy-documentation.pdf)
#
# Examples:
#   ./scripts/generate-pdf-documentation.sh
#   ./scripts/generate-pdf-documentation.sh my-documentation.pdf
#
# Prerequisites:
#   - pandoc (for Markdown to PDF conversion)
#   - texlive-xetex (LaTeX engine for PDF generation)
#   - texlive-fonts-recommended (fonts)
#
# Exit Codes:
#   0 : Success
#   1 : pandoc not found
#   2 : Source files not found
#   3 : PDF generation failed
# ========================================

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OUTPUT_FILE="${1:-multicloud-auto-deploy-documentation.pdf}"
TEMP_DIR=$(mktemp -d)
MERGED_MD="$TEMP_DIR/merged-documentation.md"

# Check if pandoc is installed
if ! command -v pandoc &> /dev/null; then
    echo -e "${RED}✗ Error: pandoc is not installed${NC}"
    echo "Install with: sudo apt-get install pandoc texlive-xetex texlive-fonts-recommended"
    exit 1
fi

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  Generating PDF Documentation${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Create temporary merged Markdown file
cat > "$MERGED_MD" << 'HEADER'
---
title: "Multi-Cloud Auto-Deploy Platform"
subtitle: "Complete Documentation"
author: "PLAYER1-r7"
date: "2026-02-15"
geometry: margin=2.5cm
fontsize: 11pt
documentclass: report
toc: true
toc-depth: 3
numbersections: true
colorlinks: true
linkcolor: blue
urlcolor: blue
---

\newpage

HEADER

echo -e "${YELLOW}📝 Merging Markdown files...${NC}"

# Function to convert emojis to text equivalents
convert_emojis() {
    local file=$1
    sed -i \
        -e 's/✨/[NEW]/g' \
        -e 's/🐛/[FIX]/g' \
        -e 's/📚/[DOCS]/g' \
        -e 's/♻️/[REFACTOR]/g' \
        -e 's/♻/[REFACTOR]/g' \
        -e 's/⚡/[PERF]/g' \
        -e 's/🧪/[TEST]/g' \
        -e 's/💄/[STYLE]/g' \
        -e 's/🔧/[CHORE]/g' \
        -e 's/💥/[BREAKING]/g' \
        -e 's/✅/[OK]/g' \
        -e 's/✓/[OK]/g' \
        -e 's/❌/[ERROR]/g' \
        -e 's/⚠️/[WARNING]/g' \
        -e 's/⚠/[WARNING]/g' \
        -e 's/📝/[NOTE]/g' \
        -e 's/🚀/[DEPLOY]/g' \
        -e 's/📦/[PACKAGE]/g' \
        -e 's/🔒/[SECURITY]/g' \
        -e 's/🔐/[SECURE]/g' \
        -e 's/🌐/[WEB]/g' \
        -e 's/🔗/[LINK]/g' \
        -e 's/📊/[STATS]/g' \
        -e 's/📈/[CHART]/g' \
        -e 's/📅/[DATE]/g' \
        -e 's/📁/[FILES]/g' \
        -e 's/🗄️/[STORAGE]/g' \
        -e 's/🗄/[STORAGE]/g' \
        -e 's/🛠️/[TOOLS]/g' \
        -e 's/🛠/[TOOLS]/g' \
        -e 's/💡/[TIP]/g' \
        -e 's/⏱️/[TIME]/g' \
        -e 's/⏱/[TIME]/g' \
        -e 's/🔄/[SYNC]/g' \
        -e 's/📌/[PIN]/g' \
        -e 's/🎯/[TARGET]/g' \
        -e 's/🔍/[SEARCH]/g' \
        -e 's/✔️/[CHECK]/g' \
        -e 's/✔/[CHECK]/g' \
        -e 's/🗑️/[DELETE]/g' \
        -e 's/🗑/[DELETE]/g' \
        -e 's/⏳/[WAIT]/g' \
        -e 's/♾️/[INFINITY]/g' \
        -e 's/♾/[INFINITY]/g' \
        -e 's/➕/[PLUS]/g' \
        -e 's/➖/[MINUS]/g' \
        -e 's/🔑/[KEY]/g' \
        -e 's/🌟/[STAR]/g' \
        -e 's/🎉/[CELEBRATE]/g' \
        -e 's/📋/[LIST]/g' \
        -e 's/📄/[DOCUMENT]/g' \
        -e 's/🖥️/[COMPUTER]/g' \
        -e 's/🖥/[COMPUTER]/g' \
        -e 's/☁️/[CLOUD]/g' \
        -e 's/☁/[CLOUD]/g' \
        -e 's/👤/[USER]/g' \
        -e 's/👥/[USERS]/g' \
        -e 's/🏃/[RUN]/g' \
        -e 's/🆕/[NEW]/g' \
        -e 's/🚪/[DOOR]/g' \
        -e 's/🏆/[TROPHY]/g' \
        -e 's/○/[O]/g' \
        -e 's/●/[*]/g' \
        -e 's/◯/[O]/g' \
        -e 's/◉/[*]/g' \
        -e 's/💻/[PC]/g' \
        -e 's/📂/[FOLDER]/g' \
        -e 's/⚙️/[SETTINGS]/g' \
        -e 's/⚙/[SETTINGS]/g' \
        -e 's/🔔/[BELL]/g' \
        -e 's/📧/[EMAIL]/g' \
        -e 's/📬/[MAILBOX]/g' \
        -e 's/🏗️/[BUILDING]/g' \
        -e 's/🏗/[BUILDING]/g' \
        -e 's/🎨/[ART]/g' \
        -e 's/🔀/[SHUFFLE]/g' \
        -e 's/🔁/[REPEAT]/g' \
        -e 's/🔂/[REPEAT_ONE]/g' \
        -e 's/▶️/[PLAY]/g' \
        -e 's/▶/[PLAY]/g' \
        -e 's/⏸️/[PAUSE]/g' \
        -e 's/⏸/[PAUSE]/g' \
        -e 's/⏹️/[STOP]/g' \
        -e 's/⏹/[STOP]/g' \
        -e 's/⏺️/[RECORD]/g' \
        -e 's/⏺/[RECORD]/g' \
        -e 's/📖/[BOOK]/g' \
        -e 's/🌍/[EARTH]/g' \
        -e 's/🌎/[EARTH]/g' \
        -e 's/🌏/[EARTH]/g' \
        -e 's/📱/[MOBILE]/g' \
        -e 's/️//g' \
        "$file"
}

# Function to analyze Mermaid diagram complexity and determine optimal width
analyze_mermaid_complexity() {
    local mermaid_content="$1"
    local lines=$(echo "$mermaid_content" | wc -l)
    local nodes=0
    local edges=0
    local participants=0
    
    # Count graph elements (use grep with -- to avoid option confusion)
    # grep -c returns 0 when no match, but with exit status 1, so we need to handle it carefully
    nodes=$(echo "$mermaid_content" | grep -cE '^\s*[A-Za-z0-9_]+[\[\(]' 2>/dev/null || true)
    nodes=${nodes:-0}
    
    local edge1=$(echo "$mermaid_content" | grep -c -- '-->' 2>/dev/null || true)
    edge1=${edge1:-0}
    local edge2=$(echo "$mermaid_content" | grep -c -- '---' 2>/dev/null || true)
    edge2=${edge2:-0}
    local edge3=$(echo "$mermaid_content" | grep -c -- '==>' 2>/dev/null || true)
    edge3=${edge3:-0}
    edges=$((edge1 + edge2 + edge3))
    
    participants=$(echo "$mermaid_content" | grep -cE '^\s*participant' 2>/dev/null || true)
    participants=${participants:-0}
    
    # Determine diagram type and calculate complexity score
    local complexity=0
    if echo "$mermaid_content" | grep -q "sequenceDiagram"; then
        # Sequence diagrams: vertical layout, needs moderate width
        complexity=$((participants * 10 + edges * 2))
    elif echo "$mermaid_content" | grep -qE "graph TB|graph TD"; then
        # Top-bottom graphs: compact, can be smaller
        complexity=$((nodes * 8 + edges * 2))
    elif echo "$mermaid_content" | grep -qE "graph LR|graph RL"; then
        # Left-right graphs: horizontal, needs more width
        complexity=$((nodes * 12 + edges * 3))
    else
        # Default based on line count
        complexity=$((lines * 5))
    fi
    
    # Map complexity to width (50% - 90%)
    local width=70
    if [ "$complexity" -lt 50 ]; then
        width=50
    elif [ "$complexity" -lt 100 ]; then
        width=60
    elif [ "$complexity" -lt 150 ]; then
        width=70
    elif [ "$complexity" -lt 200 ]; then
        width=80
    else
        width=90
    fi
    
    echo "$width"
}

# Function to convert Mermaid diagrams to SVG using mermaid.ink API
convert_mermaid() {
    local input_file=$1
    local output_file=$2
    local diagram_counter=0
    local temp_file=$(mktemp)
    local in_mermaid=0
    local mermaid_file=$(mktemp)
    
    while IFS= read -r line; do
        if [[ "$line" =~ ^\`\`\`mermaid ]]; then
            in_mermaid=1
            > "$mermaid_file"  # Clear file
            continue
        fi
        
        if [ "$in_mermaid" -eq 1 ]; then
            if [[ "$line" =~ ^\`\`\` ]]; then
                # End of mermaid block, analyze complexity
                diagram_counter=$((diagram_counter + 1))
                local svg_file="$TEMP_DIR/diagram_${diagram_counter}.svg"
                local png_file="$TEMP_DIR/diagram_${diagram_counter}.png"
                
                # Analyze Mermaid content to determine optimal width
                local mermaid_content=$(cat "$mermaid_file")
                local optimal_width=$(analyze_mermaid_complexity "$mermaid_content")
                
                # Use mermaid.ink API (ARM-compatible, no browser needed)
                local encoded=$(base64 -w 0 < "$mermaid_file" | sed 's/+/-/g; s/\//_/g; s/=//g')
                local mermaid_url="https://mermaid.ink/svg/${encoded}"
                
                # Download SVG from mermaid.ink
                if curl -s -f -o "$svg_file" "$mermaid_url" 2>/dev/null && [ -s "$svg_file" ]; then
                    # Convert SVG to PNG using Chromium headless (handles foreignObject correctly)
                    local html_wrapper="$TEMP_DIR/diagram_${diagram_counter}.html"
                    cat > "$html_wrapper" << 'HTMLEOF'
<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<style>
body { margin: 0; padding: 0; background: white; display: flex; justify-content: center; align-items: center; min-height: 100vh; }
img { max-width: 100%; height: auto; }
</style>
</head>
<body>
HTMLEOF
                    echo "<img src=\"diagram_${diagram_counter}.svg\">" >> "$html_wrapper"
                    echo "</body></html>" >> "$html_wrapper"
                    
                    if timeout 15 chromium --headless=new --disable-gpu --screenshot="$png_file" --window-size=2400,1600 --hide-scrollbars "file://$html_wrapper" >/dev/null 2>&1 && [ -s "$png_file" ]; then
                        echo -e "${GREEN}    ✓ Converted diagram $diagram_counter to PNG (width=${optimal_width}%)${NC}"
                        echo "![Diagram $diagram_counter]($png_file){width=${optimal_width}%}" >> "$temp_file"
                    else
                        # Fallback to SVG if PNG conversion fails
                        echo -e "${YELLOW}    ⚠ PNG conversion failed, using SVG for diagram $diagram_counter${NC}"
                        echo "![Diagram $diagram_counter]($svg_file){width=${optimal_width}%}" >> "$temp_file"
                    fi
                    echo "" >> "$temp_file"
                else
                    echo -e "${YELLOW}    ⚠ Failed to convert diagram $diagram_counter, keeping as code block${NC}"
                    echo '```mermaid' >> "$temp_file"
                    cat "$mermaid_file" >> "$temp_file"
                    echo '```' >> "$temp_file"
                fi
                
                in_mermaid=0
            else
                echo "$line" >> "$mermaid_file"
            fi
        else
            echo "$line" >> "$temp_file"
        fi
    done < "$input_file"
    
    rm -f "$mermaid_file"
    mv "$temp_file" "$output_file"
}

# Function to add chapter to merged file
add_chapter() {
    local file=$1
    local title=$2
    local level=$3
    
    if [ -f "$file" ]; then
        echo -e "${GREEN}  ✓ Adding: $title${NC}"
        echo "" >> "$MERGED_MD"
        echo "$(printf '#%.0s' $(seq 1 $level)) $title" >> "$MERGED_MD"
        echo "" >> "$MERGED_MD"
        
        # Create temporary file for processing
        local temp_chapter=$(mktemp)
        local file_dir=$(dirname "$file")
        
        # Remove the first heading from the file if it exists (we already added our own)
        # And fix relative image paths to be absolute
        tail -n +2 "$file" | sed '/^#/,1d' | sed "s|!\[\([^]]*\)\](images/|\![\1]($file_dir/images/|g" > "$temp_chapter"
        
        # Convert Mermaid diagrams to SVG if any exist
        if grep -q '^```mermaid' "$temp_chapter"; then
            echo -e "${YELLOW}    Converting Mermaid diagrams...${NC}"
            convert_mermaid "$temp_chapter" "$temp_chapter"
        fi
        
        # Add to merged document
        cat "$temp_chapter" >> "$MERGED_MD"
        rm "$temp_chapter"
        
        echo "" >> "$MERGED_MD"
        echo '\newpage' >> "$MERGED_MD"
        echo "" >> "$MERGED_MD"
    else
        echo -e "${YELLOW}  ⚠ Warning: $file not found, skipping${NC}"
    fi
}

# Part 1: Project Overview
echo -e "\n${BLUE}Part 1: Project Overview${NC}"
add_chapter "$PROJECT_ROOT/README.md" "Project Overview" 1
add_chapter "$PROJECT_ROOT/docs/AI_AGENT_01_OVERVIEW.md" "AI Agent Overview" 2

# Part 2: Architecture
echo -e "\n${BLUE}Part 2: Architecture${NC}"
add_chapter "$PROJECT_ROOT/docs/AI_AGENT_03_ARCHITECTURE.md" "System Architecture" 1

# Part 3: Setup and Configuration
echo -e "\n${BLUE}Part 3: Setup and Configuration${NC}"
add_chapter "$PROJECT_ROOT/docs/AI_AGENT_02_LAYOUT.md" "Layout & Overview" 1
add_chapter "$PROJECT_ROOT/docs/AI_AGENT_GUIDE.md" "AI Agent Guide" 2

# Part 4: Deployment Guides
echo -e "\n${BLUE}Part 4: Deployment Guides${NC}"
echo -e '\n# Deployment Guides\n' >> "$MERGED_MD"
add_chapter "$PROJECT_ROOT/docs/AI_AGENT_05_INFRA.md" "Infrastructure" 2
add_chapter "$PROJECT_ROOT/docs/CUSTOM_DOMAIN_SETUP.md" "Custom Domain Setup" 2
add_chapter "$PROJECT_ROOT/docs/INTEGRATION_TESTS_GUIDE.md" "Integration Tests Guide" 2
add_chapter "$PROJECT_ROOT/docs/LAMBDA_LAYER_OPTIMIZATION.md" "Lambda Layer Optimization" 2
add_chapter "$PROJECT_ROOT/docs/AWS_HTTPS_FIX_REPORT.md" "AWS HTTPS Fix Report" 2
add_chapter "$PROJECT_ROOT/docs/AWS_SNS_FIX_REPORT.md" "AWS SNS Fix Report" 2
add_chapter "$PROJECT_ROOT/docs/AWS_PRODUCTION_SNS_FIX_REPORT.md" "AWS Production SNS Fix Report" 2
add_chapter "$PROJECT_ROOT/docs/AZURE_SNS_FIX_REPORT.md" "Azure SNS Fix Report" 2

# Part 5: CI/CD
echo -e "\n${BLUE}Part 5: CI/CD${NC}"
add_chapter "$PROJECT_ROOT/docs/AI_AGENT_06_CICD.md" "CI/CD Setup" 1

# Part 6: Tools and Utilities
echo -e "\n${BLUE}Part 6: Tools and Utilities${NC}"
add_chapter "$PROJECT_ROOT/docs/AI_AGENT_08_RUNBOOKS.md" "Runbooks" 1
add_chapter "$PROJECT_ROOT/docs/AI_AGENT_09_SECURITY.md" "Security" 1
add_chapter "$PROJECT_ROOT/docs/AI_AGENT_10_TASKS.md" "Task Management" 1

# Part 7: API Reference
echo -e "\n${BLUE}Part 7: API Reference${NC}"
add_chapter "$PROJECT_ROOT/docs/AI_AGENT_04_API.md" "API Reference" 1

# Part 8: Status / Monitoring
echo -e "\n${BLUE}Part 8: Status / Monitoring${NC}"
add_chapter "$PROJECT_ROOT/docs/AI_AGENT_07_STATUS.md" "Status & Monitoring" 1
add_chapter "$PROJECT_ROOT/docs/AI_AGENT_11_WORKSPACE_MIGRATION.md" "Workspace Migration" 1

# Part 9: Services and Infrastructure
echo -e "\n${BLUE}Part 9: Services and Infrastructure${NC}"
echo -e '\n# Services and Infrastructure\n' >> "$MERGED_MD"

if [ -f "$PROJECT_ROOT/services/api/README.md" ]; then
    add_chapter "$PROJECT_ROOT/services/api/README.md" "Backend API Service" 2
fi

if [ -f "$PROJECT_ROOT/services/frontend_react/README.md" ]; then
    add_chapter "$PROJECT_ROOT/services/frontend_react/README.md" "Frontend (React) Service" 2
fi

if [ -f "$PROJECT_ROOT/services/frontend_reflex/README.md" ]; then
    add_chapter "$PROJECT_ROOT/services/frontend_reflex/README.md" "Frontend (Reflex) Service" 2
fi

if [ -f "$PROJECT_ROOT/infrastructure/pulumi/aws/simple-sns/README.md" ]; then
    add_chapter "$PROJECT_ROOT/infrastructure/pulumi/aws/simple-sns/README.md" "Pulumi Infrastructure (AWS)" 2
fi

# Part 10: Contributing
echo -e "\n${BLUE}Part 10: Contributing${NC}"
add_chapter "$PROJECT_ROOT/CONTRIBUTING.md" "Contributing Guidelines" 1

# Part 11: Changelog
echo -e "\n${BLUE}Part 11: Changelog${NC}"
add_chapter "$PROJECT_ROOT/CHANGELOG.md" "Changelog" 1

echo ""
echo -e "${YELLOW}� Converting emojis to text...${NC}"
convert_emojis "$MERGED_MD"

echo ""
echo -e "${YELLOW}🔧 Fixing list formatting...${NC}"
# Add blank line between bold text and immediately following list
# This ensures Pandoc treats them as separate blocks
perl -i -pe 'BEGIN{undef $/;} s/(\*\*[^\*]+\*\*[^\n]*)\n(- )/$1\n\n$2/g' "$MERGED_MD"

# Fix nested lists after colons (both half-width : and full-width ：)
# Add blank line after colon when followed by a list item  
perl -i -pe 'BEGIN{undef $/;} s/([^#\n][：:]\s*)\n(- )/$1\n\n$2/g' "$MERGED_MD"

echo ""
echo "🔧 Adding page breaks before figures..."

# Add page break before each figure to keep them on separate pages
# This ensures figures are properly separated in the document
perl -i -pe 's/^(!\[)/\\clearpage\n\n$1/g' "$MERGED_MD"
echo "  Added page breaks before figures"

echo ""
echo "🔧 Fixing table formatting..."

# Remove any zero-width spaces (U+200B) that may have been inserted
perl -i -pe 's/\x{200b}//g' "$MERGED_MD"

# Remove all backticks from table cells to unify font across tables
# Only process lines that contain table delimiters (|)
BEFORE_COUNT=$(grep '|' "$MERGED_MD" | grep -o '`[^`]*`' | wc -l)
perl -i -pe 'if (/\|.*\|/) { s/`([^`]+)`/$1/g }' "$MERGED_MD"
AFTER_COUNT=$(grep '|' "$MERGED_MD" | grep -o '`[^`]*`' | wc -l)
echo "  Removed backticks from $((BEFORE_COUNT - AFTER_COUNT)) table cells"
echo "  Unified font across all tables"

echo ""
echo -e "${YELLOW}📄 Generating PDF with pandoc...${NC}"
echo ""

# Generate PDF using pandoc with custom LaTeX settings
cd "$PROJECT_ROOT"

# Check if LaTeX header exists
LATEX_HEADER="$PROJECT_ROOT/scripts/latex-header.tex"
if [ ! -f "$LATEX_HEADER" ]; then
    echo -e "${RED}✗ Error: LaTeX header not found at $LATEX_HEADER${NC}"
    exit 3
fi

# Generate PDF using Pandoc directly with Lua filter for table columns
LUA_FILTER="$PROJECT_ROOT/scripts/table-columns.lua"
if pandoc "$MERGED_MD" \
    -o "$OUTPUT_FILE" \
    --pdf-engine=xelatex \
    --template="$PROJECT_ROOT/scripts/custom-latex-template.tex" \
    --lua-filter="$LUA_FILTER" \
    --toc \
    --toc-depth=3 \
    --number-sections \
    --include-in-header="$LATEX_HEADER" \
    --highlight-style=tango \
    --listings \
    --variable documentclass=report \
    --variable fontsize=11pt \
    --variable papersize=a4 \
    --variable geometry:margin=2.5cm \
    --variable tables=true \
    --variable graphics=true \
    --variable lmodern=false \
    2>&1; then
    
    echo ""
    echo -e "${GREEN}========================================${NC}"
    echo -e "${GREEN}  ✓ PDF Generated Successfully!${NC}"
    echo -e "${GREEN}========================================${NC}"
    echo ""
    echo "Output file: $OUTPUT_FILE"
    echo "File size: $(du -h "$OUTPUT_FILE" | cut -f1)"
    echo "Location: $(realpath "$OUTPUT_FILE")"
    echo ""
    
    # Cleanup
    rm -rf "$TEMP_DIR"
    
    exit 0
else
    echo ""
    echo -e "${RED}✗ Error: PDF generation failed${NC}"
    echo -e "${YELLOW}Merged Markdown file saved at: $MERGED_MD${NC}"
    echo -e "${YELLOW}You can inspect this file or try generating PDF manually.${NC}"
    exit 3
fi
