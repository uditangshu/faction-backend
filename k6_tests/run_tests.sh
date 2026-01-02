#!/bin/bash

# k6 Test Runner Script
# Convenient script to run different k6 test scenarios

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Default values
BASE_URL="${BASE_URL:-http://localhost:8000}"
TEST_TYPE="${TEST_TYPE:-smoke}"
OUTPUT_DIR="${OUTPUT_DIR:-./results}"

# Check if k6 is installed
if ! command -v k6 &> /dev/null; then
    echo -e "${RED}Error: k6 is not installed${NC}"
    echo "Install k6: https://k6.io/docs/getting-started/installation/"
    exit 1
fi

# Create output directory
mkdir -p "$OUTPUT_DIR"

# Function to run a test
run_test() {
    local test_file=$1
    local test_name=$2
    
    echo -e "${GREEN}Running ${test_name}...${NC}"
    echo "Base URL: $BASE_URL"
    echo "Output: $OUTPUT_DIR/${test_name}_results.json"
    echo "----------------------------------------"
    
    BASE_URL="$BASE_URL" k6 run \
        --out json="$OUTPUT_DIR/${test_name}_results.json" \
        "$test_file"
    
    echo -e "${GREEN}✓ ${test_name} completed${NC}"
    echo ""
}

# Main menu
case "$TEST_TYPE" in
    smoke)
        run_test "./scenarios/smoke_test.js" "smoke"
        ;;
    load)
        run_test "./scenarios/load_test.js" "load"
        ;;
    stress)
        run_test "./scripts/stress_test.js" "stress"
        ;;
    spike)
        run_test "./scenarios/spike_test.js" "spike"
        ;;
    auth)
        run_test "./scripts/auth_test.js" "auth"
        ;;
    authenticated)
        run_test "./scripts/authenticated_test.js" "authenticated"
        ;;
    treasure)
        run_test "./scripts/treasure_test.js" "treasure"
        ;;
    comprehensive)
        run_test "./scripts/comprehensive_test.js" "comprehensive"
        ;;
    ranking)
        run_test "./scripts/ranking_apis_test.js" "ranking_apis"
        ;;
    all)
        echo -e "${YELLOW}Running all tests...${NC}"
        run_test "./scenarios/smoke_test.js" "smoke"
        sleep 5
        run_test "./scenarios/load_test.js" "load"
        sleep 5
        run_test "./scripts/stress_test.js" "stress"
        ;;
    *)
        echo "Usage: $0 [smoke|load|stress|spike|auth|authenticated|treasure|comprehensive|ranking|all]"
        echo ""
        echo "Test Types:"
        echo "  smoke         - Quick smoke test (1 user, 30s)"
        echo "  load          - Normal load test (50-100 users)"
        echo "  stress        - Stress test (gradual increase to 500 users)"
        echo "  spike         - Spike test (sudden traffic spike)"
        echo "  auth          - Authentication endpoint test"
        echo "  authenticated - Authenticated endpoints test"
        echo "  treasure      - Treasure endpoints test"
        echo "  comprehensive - Comprehensive multi-endpoint test"
        echo "  ranking       - Ranking APIs test (contests, arena, streak, contest-ranking)"
        echo "  all           - Run smoke, load, and stress tests"
        echo ""
        echo "Environment Variables:"
        echo "  BASE_URL      - API base URL (default: http://localhost:8000)"
        echo "  TEST_PHONE    - Test user phone number"
        echo "  TEST_PASSWORD - Test user password"
        echo "  OUTPUT_DIR   - Output directory for results (default: ./results)"
        echo ""
        echo "Examples:"
        echo "  BASE_URL=http://api.example.com:8000 ./run_tests.sh load"
        echo "  TEST_TYPE=stress ./run_tests.sh"
        exit 1
        ;;
esac

echo -e "${GREEN}All tests completed!${NC}"
echo "Results saved in: $OUTPUT_DIR"

