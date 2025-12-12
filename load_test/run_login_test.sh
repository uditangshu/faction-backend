#!/bin/bash

# wrk2 script for testing login API
# Make sure wrk2 is installed: https://github.com/giltene/wrk2

# Configuration
HOST="${HOST:-http://localhost:8000}"
THREADS="${THREADS:-12}"
CONNECTIONS="${CONNECTIONS:-400}"
DURATION="${DURATION:-30s}"
RATE="${RATE:-2000}"  # Requests per second
SCRIPT="login_test.lua"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}  Login API Load Test (wrk2)${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo "Configuration:"
echo "  Host: $HOST"
echo "  Threads: $THREADS"
echo "  Connections: $CONNECTIONS"
echo "  Duration: $DURATION"
echo "  Rate: $RATE req/s"
echo "  Script: $SCRIPT"
echo ""

# Check if wrk2 is installed
if ! command -v wrk &> /dev/null; then
    echo -e "${RED}Error: wrk2 is not installed${NC}"
    echo ""
    echo "Installation:"
    echo "  macOS: brew install wrk2"
    echo "  Linux: See https://github.com/giltene/wrk2"
    exit 1
fi

# Check if script exists
if [ ! -f "$SCRIPT" ]; then
    echo -e "${RED}Error: Script file '$SCRIPT' not found${NC}"
    exit 1
fi

# Check if server is reachable
echo -e "${YELLOW}Checking if server is reachable...${NC}"
if ! curl -s -o /dev/null -w "%{http_code}" "$HOST/health" > /dev/null 2>&1; then
    echo -e "${YELLOW}Warning: Server health check failed. Continuing anyway...${NC}"
fi

echo ""
echo -e "${GREEN}Starting load test...${NC}"
echo ""

# Run wrk2
wrk -t"$THREADS" \
    -c"$CONNECTIONS" \
    -d"$DURATION" \
    -R"$RATE" \
    --latency \
    -s "$SCRIPT" \
    "$HOST"

EXIT_CODE=$?

echo ""
if [ $EXIT_CODE -eq 0 ]; then
    echo -e "${GREEN}Test completed successfully!${NC}"
else
    echo -e "${RED}Test failed with exit code: $EXIT_CODE${NC}"
fi

exit $EXIT_CODE

