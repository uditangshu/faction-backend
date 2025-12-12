# Understanding wrk2 Latency Analysis Output

When you run wrk2 with the `--latency` flag, it generates a detailed latency distribution analysis. Here's what each section means:

## Typical wrk2 Output Structure

```
Running 30s test @ http://localhost:8000
  12 threads and 400 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency    45.23ms   12.45ms  234.56ms   85.23%
    Req/Sec   166.67     45.23    250.00     78.45%
  Latency Distribution
     50%   42.34ms
     75%   56.78ms
     90%   78.90ms
     99%  145.67ms
  59940 requests in 30.00s, 12.34MB read
Requests/sec:   1998.00
Transfer/sec:    420.80KB
```

## Detailed Explanation

### 1. Thread Statistics (Lines ~311-315)

```
Thread Stats   Avg      Stdev     Max   +/- Stdev
  Latency    45.23ms   12.45ms  234.56ms   85.23%
  Req/Sec   166.67     45.23    250.00     78.45%
```

**Latency Row:**
- **Avg (Average)**: Mean response time across all requests
- **Stdev (Standard Deviation)**: Measures variability in response times
  - Low stdev = consistent performance
  - High stdev = inconsistent performance (some requests much slower)
- **Max**: Worst-case response time observed
- **+/- Stdev**: Percentage of requests within one standard deviation of the mean
  - Higher % = more consistent performance

**Req/Sec Row:**
- **Avg**: Average requests per second per thread
- **Stdev**: Variability in request rate
- **Max**: Peak requests per second achieved
- **+/- Stdev**: Consistency of request rate

### 2. Latency Distribution (Lines ~316-325)

```
Latency Distribution
     50%   42.34ms    (Median - p50)
     75%   56.78ms    (75th percentile - p75)
     90%   78.90ms    (90th percentile - p90)
     99%  145.67ms    (99th percentile - p99)
  99.999% 234.56ms    (99.999th percentile - p99.999)
```

**What These Percentiles Mean:**

- **50% (p50 / Median)**: Half of all requests complete within this time
  - Most common response time
  - Not affected by outliers

- **75% (p75)**: 75% of requests complete within this time
  - Good indicator of typical user experience

- **90% (p90)**: 90% of requests complete within this time
  - Important for SLA monitoring
  - Most users experience this or better

- **99% (p99)**: 99% of requests complete within this time
  - Critical for understanding worst-case scenarios
  - Only 1% of requests are slower
  - Key metric for production systems

- **99.9% (p99.9)**: 99.9% of requests complete within this time
  - Catches extreme outliers
  - Important for high-traffic systems

- **99.999% (p99.999)**: 99.999% of requests complete within this time
  - Catches rare extreme cases
  - Used in very high-scale systems

### 3. Latency Histogram (Lines ~326-358)

```
Latency Distribution (Histogram)
  < 1ms      0 (0.00%)
  1-5ms      1250 (2.08%)
  5-10ms     3500 (5.84%)
  10-25ms    12000 (20.00%)
  25-50ms    18000 (30.00%)
  50-100ms   15000 (25.00%)
  100-250ms  8000 (13.33%)
  250-500ms  2000 (3.33%)
  500ms+     250 (0.42%)
```

**What This Shows:**
- **Distribution of response times** across different latency buckets
- Helps identify:
  - **Normal distribution**: Most requests in middle buckets
  - **Bimodal distribution**: Two peaks (e.g., cache hits vs misses)
  - **Long tail**: Many requests in high-latency buckets (performance issue)

### 4. Summary Statistics

```
59940 requests in 30.00s, 12.34MB read
Requests/sec:   1998.00
Transfer/sec:    420.80KB
```

- **Total Requests**: Number of requests completed
- **Duration**: Actual test duration
- **Data Transferred**: Total bytes read
- **Requests/sec**: Throughput (requests per second)
- **Transfer/sec**: Data transfer rate

## Interpreting the Analysis

### Good Performance Indicators:
- ✅ p99 latency < 500ms
- ✅ Low standard deviation (< 30% of average)
- ✅ High +/- Stdev percentage (> 80%)
- ✅ Most requests in lower latency buckets
- ✅ Low error rate (< 1%)

### Performance Issues:
- ⚠️ p99 latency > 1s
- ⚠️ High standard deviation (> 50% of average)
- ⚠️ Many requests in high-latency buckets (250ms+)
- ⚠️ High error rate (> 5%)
- ⚠️ Large gap between p50 and p99 (inconsistent performance)

### Example Analysis:

**Scenario 1: Consistent Performance**
```
Latency: 50ms avg, 10ms stdev, 85% within 1 stdev
p50: 48ms, p99: 120ms
```
→ Good: Low variability, predictable performance

**Scenario 2: Inconsistent Performance**
```
Latency: 50ms avg, 40ms stdev, 60% within 1 stdev
p50: 45ms, p99: 800ms
```
→ Problem: High variability, some requests very slow

**Scenario 3: Overloaded System**
```
Latency: 200ms avg, 150ms stdev, 50% within 1 stdev
p50: 180ms, p99: 2000ms
Error rate: 15%
```
→ Critical: System is overloaded, many failures

## Key Takeaways

1. **Don't just look at averages** - p99 tells you about worst-case scenarios
2. **Standard deviation matters** - Low variability = better user experience
3. **Histogram reveals patterns** - Shows distribution, not just summary stats
4. **Compare percentiles** - Large gap between p50 and p99 indicates inconsistency
5. **Monitor error rates** - High latency often correlates with errors

## Using This for Optimization

- **If p50 is good but p99 is bad**: Focus on eliminating slow requests (database queries, external APIs)
- **If both are bad**: System is overloaded, need to scale or optimize
- **If stdev is high**: Look for bottlenecks causing inconsistent performance
- **If histogram shows long tail**: Identify and fix slow code paths

