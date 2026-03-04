#!/bin/bash
################################################################################
# Script: test-coverage-quick.sh
# Purpose: Quick coverage test execution with minimal setup
# Usage: ./scripts/test-coverage-quick.sh [MODULE]
# Description:
#   Runs specific test suites and displays coverage improvements
################################################################################

set -e

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
BOLD='\033[1m'
NC='\033[0m'

# Navigation
API_DIR="services/api"
cd "$(dirname "$0")/.." || exit 1

if [ ! -d "$API_DIR" ]; then
    echo -e "${RED}Error: API directory not found${NC}"
    exit 1
fi

cd "$API_DIR" || exit 1

# Determine which tests to run
case "${1:-all}" in
    auth)
        TESTS="tests/test_auth.py"
        DESC="Auth Module"
        ;;
    jwt)
        TESTS="tests/test_jwt_verifier.py"
        DESC="JWT Verifier"
        ;;
    routes)
        TESTS="tests/test_routes.py"
        DESC="Routes"
        ;;
    all)
        TESTS="tests/"
        DESC="All Tests"
        ;;
    *)
        echo "Usage: $0 [auth|jwt|routes|all]"
        echo ""
        echo "Examples:"
        echo "  $0 auth          # Run auth tests only"
        echo "  $0 jwt           # Run JWT verifier tests"
        echo "  $0 routes        # Run routes tests"
        echo "  $0 all           # Run all tests (default)"
        exit 1
        ;;
esac

echo -e "${BLUE}${BOLD}═══════════════════════════════════════════════${NC}"
echo -e "${BLUE}${BOLD}Coverage Test: $DESC${NC}"
echo -e "${BLUE}${BOLD}═══════════════════════════════════════════════${NC}"
echo ""

# Run tests with coverage
python -m pytest "$TESTS" \
    --cov=app \
    --cov-report=term-missing \
    --cov-report=html \
    -v \
    --tb=short

echo ""
echo -e "${GREEN}${BOLD}✓ Coverage report generated${NC}"
echo -e "  View: ${BOLD}htmlcov/index.html${NC}"
echo ""
