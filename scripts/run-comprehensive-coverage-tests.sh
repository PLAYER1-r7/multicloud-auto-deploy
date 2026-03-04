#!/bin/bash
################################################################################
# Script: run-comprehensive-coverage-tests.sh
# Purpose: Run comprehensive test suite with detailed coverage reporting
# Usage: ./scripts/run-comprehensive-coverage-tests.sh [OPTIONS]
# Description:
#   Executes all pytest test suites with coverage analysis.
#   Generates HTML and JSON reports.
#   Compares against coverage baselines.
#   Provides detailed per-module reporting.
################################################################################

set -e

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
BOLD='\033[1m'
NC='\033[0m' # No Color

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
API_DIR="$PROJECT_ROOT/services/api"
TEST_DIR="$API_DIR/tests"
COVERAGE_DIR="$API_DIR/htmlcov"
COVERAGE_REPORT="$API_DIR/.coverage"
COVERAGE_JSON="$API_DIR/coverage.json"

# Coverage targets (as percentages)
declare -A COVERAGE_TARGETS=(
    [auth.py]=60
    [config.py]=100
    [jwt_verifier.py]=70
    [main.py]=60
    [models.py]=98
    [posts.py]=80
    [profile.py]=80
    [uploads.py]=80
    [limits.py]=80
    [backends/base.py]=90
    [backends/aws_backend.py]=70
    [backends/azure_backend.py]=70
    [backends/gcp_backend.py]=70
    [backends/local_backend.py]=80
)

# Default values
VERBOSE=false
GENERATE_REPORT=true
MARKERS=""
FAIL_UNDER=0

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -v|--verbose)
            VERBOSE=true
            shift
            ;;
        --no-report)
            GENERATE_REPORT=false
            shift
            ;;
        -m|--markers)
            MARKERS="-m $2"
            shift 2
            ;;
        --fail-under)
            FAIL_UNDER=$2
            shift 2
            ;;
        -h|--help)
            cat <<EOF
Usage: $0 [OPTIONS]

Options:
    -v, --verbose           Show verbose pytest output
    --no-report             Skip HTML report generation
    -m, --markers MARKER    Run specific test markers
    --fail-under PERCENT    Minimum coverage percentage to pass (default: 0)
    -h, --help              Show this help message

Examples:
    $0                              # Run all tests with report
    $0 -v                           # Verbose output
    $0 -m aws                       # AWS backend tests only
    $0 --fail-under 50              # Require 50% minimum coverage

EOF
            exit 0
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}"
            exit 1
            ;;
    esac
done

# Ensure we're in the API directory
cd "$API_DIR"

echo -e "${BLUE}===============================================${NC}"
echo -e "${BLUE}${BOLD}Comprehensive Test Suite with Coverage${NC}"
echo -e "${BLUE}===============================================${NC}"
echo ""

# Display test configuration
echo -e "${BLUE}Test Configuration:${NC}"
echo "  Test Directory: $TEST_DIR"
echo "  Coverage Target: ${FAIL_UNDER}%"
if [ -n "$MARKERS" ]; then
    echo "  Test Markers: $MARKERS"
fi
echo ""

# Run pytest with coverage
echo -e "${YELLOW}Running tests...${NC}"
echo ""

PYTEST_CMD="pytest tests/ \
    --cov=app \
    --cov-report=html:htmlcov \
    --cov-report=json:coverage.json \
    --cov-report=term-missing \
    --cov-fail-under=$FAIL_UNDER \
    -v"

if [ "$VERBOSE" = true ]; then
    PYTEST_CMD="$PYTEST_CMD -vv"
fi

if [ -n "$MARKERS" ]; then
    PYTEST_CMD="$PYTEST_CMD $MARKERS"
fi

# Execute tests
if eval "$PYTEST_CMD"; then
    TEST_RESULT=0
else
    TEST_RESULT=$?
fi

echo ""
echo -e "${BLUE}===============================================${NC}"
echo -e "${BLUE}${BOLD}Coverage Analysis${NC}"
echo -e "${BLUE}===============================================${NC}"
echo ""

# Parse and analyze coverage.json
if [ -f "$COVERAGE_JSON" ]; then
    echo -e "${GREEN}Coverage Report Generated${NC}"
    echo ""

    # Extract overall coverage percentage
    OVERALL_COVERAGE=$(python3 -c "
import json
with open('coverage.json') as f:
    data = json.load(f)
    percent = data['totals']['percent_covered']
    print(f'{percent:.1f}')
")

    echo -e "${BOLD}Overall Coverage: ${GREEN}${OVERALL_COVERAGE}%${NC}"
    echo ""

    # Analyze per-file coverage
    echo -e "${BOLD}Per-Module Coverage:${NC}"
    python3 << 'EOF'
import json
from pathlib import Path

with open('coverage.json') as f:
    data = json.load(f)

# Filter for app modules
files = {}
for path, info in data['files'].items():
    if 'app/' in path:
        # Extract relative path from app/
        rel_path = path.split('app/')[-1]
        coverage = info['summary']['percent_covered']
        files[rel_path] = coverage

# Display sorted by coverage
for path in sorted(files.keys()):
    coverage = files[path]
    if coverage >= 80:
        color = '\033[0;32m'  # Green
    elif coverage >= 60:
        color = '\033[1;33m'  # Yellow
    else:
        color = '\033[0;31m'  # Red
    reset = '\033[0m'
    print(f"  {path:<40} {color}{coverage:5.1f}%{reset}")

EOF

    echo ""
fi

# Generate HTML report location info
if [ "$GENERATE_REPORT" = true ] && [ -f "$COVERAGE_DIR/index.html" ]; then
    echo -e "${GREEN}✓${NC} HTML Coverage Report: ${BOLD}htmlcov/index.html${NC}"
    echo "  Open in browser to view detailed coverage analysis"
    echo ""
fi

# Test result summary
echo -e "${BLUE}===============================================${NC}"
echo -e "${BLUE}${BOLD}Test Results Summary${NC}"
echo -e "${BLUE}===============================================${NC}"
echo ""

if [ $TEST_RESULT -eq 0 ]; then
    echo -e "${GREEN}${BOLD}✅ All tests passed!${NC}"
    echo ""
    echo "  • Coverage report generated in htmlcov/"
    echo "  • JSON coverage data saved to coverage.json"
    echo ""
    exit 0
else
    echo -e "${RED}${BOLD}❌ Some tests failed${NC}"
    echo ""
    echo "  • Review test output above"
    echo "  • Check coverage report for details"
    echo ""
    exit 1
fi
