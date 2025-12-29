# k6 Load Testing for Faction Backend

This directory contains k6 load testing scripts for the Faction Backend API. k6 is a modern load testing tool that uses JavaScript/ES6 for test scripts.

## Prerequisites

### Install k6

**macOS:**
```bash
brew install k6
```

**Linux:**
```bash
# Debian/Ubuntu
sudo gpg -k
sudo gpg --no-default-keyring --keyring /usr/share/keyrings/k6-archive-keyring.gpg --keyserver hkp://keyserver.ubuntu.com:80 --recv-keys C5AD17C747E3415A3642D57D77C6C491D6AC1D69
echo "deb [signed-by=/usr/share/keyrings/k6-archive-keyring.gpg] https://dl.k6.io/deb stable main" | sudo tee /etc/apt/sources.list.d/k6.list
sudo apt-get update
sudo apt-get install k6
```

**Windows:**
```bash
# Using Chocolatey
choco install k6

# Or download from: https://k6.io/docs/getting-started/installation/
```

**Docker:**
```bash
docker pull grafana/k6
```

## Quick Start

### 1. Update Test Credentials

Edit `utils/config.js` or set environment variables:

```bash
export TEST_PHONE="+918109285049"
export TEST_PASSWORD="your_password"
export BASE_URL="http://localhost:8000"
```

### 2. Run Tests

**Using the helper script (Recommended):**
```bash
cd k6_tests
chmod +x run_tests.sh
./run_tests.sh smoke      # Quick smoke test
./run_tests.sh load        # Normal load test
./run_tests.sh stress      # Stress test
./run_tests.sh spike       # Spike test
./run_tests.sh auth        # Authentication test
./run_tests.sh authenticated # Authenticated endpoints test
```

**Direct k6 commands:**
```bash
# Smoke test
k6 run scenarios/smoke_test.js

# Load test
k6 run scenarios/load_test.js

# Stress test
k6 run scripts/stress_test.js

# With custom base URL
BASE_URL=http://your-server:8000 k6 run scenarios/smoke_test.js
```

## Test Types

### 1. Smoke Test (`scenarios/smoke_test.js`)
- **Purpose**: Quick verification that the system is working
- **Load**: 1 user, 30 seconds
- **Use Case**: Before deploying, quick health check

```bash
k6 run scenarios/smoke_test.js
```

### 2. Load Test (`scenarios/load_test.js`)
- **Purpose**: Test normal expected load
- **Load**: 50-100 concurrent users
- **Use Case**: Validate system performance under normal conditions

```bash
k6 run scenarios/load_test.js
```

### 3. Stress Test (`scripts/stress_test.js`)
- **Purpose**: Find the breaking point
- **Load**: Gradually increases from 50 to 500 users
- **Use Case**: Determine maximum capacity

```bash
k6 run scripts/stress_test.js
```

### 4. Spike Test (`scenarios/spike_test.js`)
- **Purpose**: Test system resilience to sudden traffic spikes
- **Load**: Sudden spike from 100 to 1000 users
- **Use Case**: Test how system handles viral traffic

```bash
k6 run scenarios/spike_test.js
```

### 5. Authentication Test (`scripts/auth_test.js`)
- **Purpose**: Test login endpoint specifically
- **Load**: 50-100 users with ramp-up
- **Use Case**: Validate authentication performance

```bash
k6 run scripts/auth_test.js
```

### 6. Authenticated Endpoints Test (`scripts/authenticated_test.js`)
- **Purpose**: Test authenticated endpoints after login
- **Load**: 30-50 users
- **Endpoints**: `/users/me`, `/streaks/me`, `/questions/qotd`
- **Use Case**: Validate protected endpoint performance

```bash
k6 run scripts/authenticated_test.js
```

## Configuration

### Environment Variables

```bash
# API Configuration
BASE_URL=http://localhost:8000          # API base URL
TEST_PHONE=+918109285049                # Test user phone number
TEST_PASSWORD=your_password             # Test user password

# Test Configuration
ENV=local                               # Environment tag
OUTPUT_DIR=./results                    # Results output directory
```

### Customizing Tests

Edit `utils/config.js` to modify:
- Base URL and API prefix
- Test credentials
- Default thresholds
- Tags

## Understanding Results

### Key Metrics

1. **http_req_duration**: Response time metrics
   - `avg`: Average response time
   - `p(95)`: 95th percentile (95% of requests faster than this)
   - `p(99)`: 99th percentile
   - `max`: Maximum response time

2. **http_req_failed**: Error rate
   - `rate`: Percentage of failed requests

3. **http_reqs**: Request rate
   - `rate`: Requests per second

4. **vus**: Virtual Users
   - Current number of concurrent users

### Interpreting Results

**Good Performance:**
- p95 latency < 500ms
- p99 latency < 1000ms
- Error rate < 1%

**Acceptable Performance:**
- p95 latency < 1000ms
- p99 latency < 2000ms
- Error rate < 5%

**Needs Optimization:**
- p95 latency > 1000ms
- p99 latency > 2000ms
- Error rate > 5%

## Advanced Usage

### Custom Load Scenarios

Create your own test file:

```javascript
import http from 'k6/http';
import { check } from 'k6';
import { getApiUrl, createLoginPayload } from './utils/config.js';

export const options = {
  vus: 100,
  duration: '5m',
  thresholds: {
    http_req_duration: ['p(95)<500'],
  },
};

export default function () {
  const response = http.post(
    getApiUrl('/auth/login'),
    JSON.stringify(createLoginPayload()),
    { headers: { 'Content-Type': 'application/json' } }
  );
  
  check(response, {
    'status is 200': (r) => r.status === 200,
  });
}
```

### Running with Docker

```bash
docker run -i --rm -v $(pwd):/scripts grafana/k6 run /scripts/scenarios/smoke_test.js
```

### Cloud Execution (k6 Cloud)

```bash
# Login to k6 Cloud
k6 login cloud

# Run test in cloud
k6 cloud scenarios/load_test.js
```

### CI/CD Integration

Example GitHub Actions workflow:

```yaml
name: Load Test
on: [push]
jobs:
  load-test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Install k6
        run: |
          sudo gpg -k
          sudo gpg --no-default-keyring --keyring /usr/share/keyrings/k6-archive-keyring.gpg --keyserver hkp://keyserver.ubuntu.com:80 --recv-keys C5AD17C747E3415A3642D57D77C6C491D6AC1D69
          echo "deb [signed-by=/usr/share/keyrings/k6-archive-keyring.gpg] https://dl.k6.io/deb stable main" | sudo tee /etc/apt/sources.list.d/k6.list
          sudo apt-get update
          sudo apt-get install k6
      - name: Run smoke test
        run: |
          cd k6_tests
          k6 run scenarios/smoke_test.js
```

## Troubleshooting

### Connection Errors
- Verify the server is running
- Check BASE_URL is correct
- Verify firewall/network settings

### High Error Rate
- Reduce number of virtual users
- Check server logs
- Verify database connection pool settings
- Check Redis connection

### Low Throughput
- Increase number of virtual users gradually
- Check server CPU/memory usage
- Verify database indexes
- Check for N+1 query problems

### Authentication Failures
- Verify test credentials are correct
- Check if user account is active
- Verify OTP/SMS service is working

## Best Practices

1. **Start Small**: Begin with smoke tests, then gradually increase load
2. **Monitor Resources**: Watch server CPU, memory, and database during tests
3. **Test Realistic Scenarios**: Use realistic user behavior and data
4. **Run Regularly**: Include load tests in CI/CD pipeline
5. **Document Baselines**: Keep track of performance baselines
6. **Test in Production-like Environment**: Use staging environment that mirrors production

## Comparison with Other Tools

| Feature | k6 | wrk2 | Locust |
|---------|----|------|--------|
| Scripting | JavaScript | Lua | Python |
| Learning Curve | Medium | Medium | Easy |
| Performance | High | Very High | Medium |
| Cloud Support | Yes | No | Yes |
| Metrics | Rich | Basic | Rich |
| CI/CD Integration | Excellent | Good | Good |

## Resources

- [k6 Documentation](https://k6.io/docs/)
- [k6 Examples](https://k6.io/docs/examples/)
- [k6 Best Practices](https://k6.io/docs/test-authoring/best-practices/)
- [k6 Cloud](https://k6.io/cloud/)

## Directory Structure

```
k6_tests/
├── scripts/              # Main test scripts
│   ├── auth_test.js      # Authentication endpoint test
│   ├── authenticated_test.js  # Authenticated endpoints test
│   └── stress_test.js    # Stress test
├── scenarios/            # Test scenarios
│   ├── smoke_test.js     # Quick smoke test
│   ├── load_test.js      # Normal load test
│   └── spike_test.js     # Spike test
├── utils/                # Utility functions
│   └── config.js         # Configuration and helpers
├── run_tests.sh          # Test runner script
└── README.md             # This file
```

## Support

For issues or questions:
1. Check k6 documentation: https://k6.io/docs/
2. Review test logs and server logs
3. Verify test credentials and configuration

