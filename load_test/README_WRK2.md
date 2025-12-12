# wrk2 Login API Load Testing

This directory contains wrk2 scripts for load testing the login API endpoint.

## Prerequisites

Install wrk2:
- **macOS**: `brew install wrk2`
- **Linux**: Follow instructions at https://github.com/giltene/wrk2
- **Windows**: Use WSL or a Linux VM

## Quick Start

### 1. Update Test Credentials

Edit `login_test.lua` and update the test credentials:

```lua
local phone_number = "+918109285049"  -- Your test user phone number
local password = "stringst"           -- Your test user password
```

### 2. Run the Test

**Option A: Using the shell script (Recommended)**
```bash
chmod +x run_login_test.sh
./run_login_test.sh
```

**Option B: Direct wrk2 command**
```bash
wrk -t12 -c400 -d30s -R2000 --latency -s login_test.lua http://localhost:8000
```

## Configuration

### Environment Variables

You can customize the test using environment variables:

```bash
# Custom host
HOST=http://your-server:8000 ./run_login_test.sh

# Custom rate (requests per second)
RATE=5000 ./run_login_test.sh

# Custom duration
DURATION=60s ./run_login_test.sh

# Custom connections
CONNECTIONS=1000 ./run_login_test.sh
```

### Command Line Parameters

The wrk2 command syntax:
```bash
wrk -t<threads> -c<connections> -d<duration> -R<rate> --latency -s <script> <url>
```

**Parameters:**
- `-t`: Number of threads (default: 12)
- `-c`: Number of connections (default: 400)
- `-d`: Test duration (e.g., 30s, 1m, 5m)
- `-R`: Target request rate per second (default: 2000)
- `--latency`: Show latency statistics
- `-s`: Lua script file
- `<url>`: Base URL of the API

## Example Test Scenarios

### Light Load Test
```bash
wrk -t4 -c100 -d30s -R500 --latency -s login_test.lua http://localhost:8000
```

### Medium Load Test
```bash
wrk -t12 -c400 -d60s -R2000 --latency -s login_test.lua http://localhost:8000
```

### Heavy Load Test
```bash
wrk -t24 -c1000 -d5m -R5000 --latency -s login_test.lua http://localhost:8000
```

### Stress Test (Find Breaking Point)
```bash
wrk -t24 -c2000 -d10m -R10000 --latency -s login_test.lua http://localhost:8000
```

## Understanding Results

### Key Metrics

1. **Requests/sec**: Throughput - how many requests per second the server can handle
2. **Latency Percentiles**:
   - **50th (p50)**: Median response time
   - **75th (p75)**: 75% of requests complete within this time
   - **90th (p90)**: 90% of requests complete within this time
   - **99th (p99)**: 99% of requests complete within this time
   - **99.9th (p99.9)**: 99.9% of requests complete within this time

### Interpreting Results

- **Good Performance**: p99 latency < 500ms, low error rate
- **Acceptable**: p99 latency < 1s, error rate < 1%
- **Needs Optimization**: p99 latency > 1s or error rate > 5%

## Troubleshooting

### Connection Errors
- Check if the server is running
- Verify the host and port are correct
- Check firewall settings

### High Error Rate
- Server may be overloaded - reduce `-R` (rate)
- Check server logs for errors
- Verify test credentials are correct

### Low Throughput
- Increase `-c` (connections) if server can handle it
- Check server CPU/memory usage
- Verify database connection pool settings

## Notes

- Each request uses a unique device_id to simulate different devices
- The script generates UUID-like device IDs for each request
- Modify the script to test with multiple user credentials if needed
- For production testing, use realistic test data and gradual ramp-up

## Advanced: Multiple Users

To test with multiple users, modify `login_test.lua`:

```lua
-- Array of test users
local users = {
    {phone = "+918109285049", password = "password1"},
    {phone = "+918109285050", password = "password2"},
    -- Add more users...
}

-- Select random user for each request
function request()
    local user = users[math.random(#users)]
    -- ... rest of the code
end
```

