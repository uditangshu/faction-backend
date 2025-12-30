/**
 * k6 Rating Ranking API Load Test
 * Tests the GET /api/v1/rating-ranking/ endpoint
 * 
 * Usage:
 *   # Using access token from environment variable
 *   ACCESS_TOKEN=your_token_here k6 run scripts/rating_ranking_test.js
 * 
 *   # Or set in the script directly (see below)
 *   k6 run scripts/rating_ranking_test.js
 * 
 *   # Custom load
 *   k6 run --vus 100 --duration 5m scripts/rating_ranking_test.js
 */

import http from 'k6/http';
import { check, sleep } from 'k6';
import { Rate, Trend } from 'k6/metrics';
import { getApiUrl, config } from '../utils/config.js';

// Custom metrics
const ratingRankingSuccessRate = new Rate('rating_ranking_success');
const ratingRankingResponseTime = new Trend('rating_ranking_response_time');

// Access token - can be set via environment variable or hardcoded
const ACCESS_TOKEN =  'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJlNTlkMTMxMS01MDBhLTQ2MjUtYjYwYy1kZGNhOWRmMTdjMDEiLCJwaG9uZSI6Iis5MTgxMDkyODUwNDkiLCJzZXNzaW9uX2lkIjoiN2ZkZDI5NmEtYjg5Zi00ZjdlLWIzYjUtOGFjM2Q3NjU0ZDBmIiwiZXhwIjoxNzY3MTIxODQwLCJ0eXBlIjoiYWNjZXNzIn0.nMdpTzh6tBgC1UKtw9mSXH6o9luCutSJFgs6Cqe_k8g';

export const options = {
  stages: [
    { duration: '30s', target: 50 },   // Ramp up to 50 users
    { duration: '2m', target: 50 },      // Stay at 50 users
    { duration: '30s', target: 100 },   // Ramp up to 100 users
    { duration: '2m', target: 100 },     // Stay at 100 users
    { duration: '30s', target: 150 },    // Ramp up to 150 users
    { duration: '2m', target: 150 },     // Stay at 150 users
    { duration: '30s', target: 0 },      // Ramp down
  ],
  thresholds: {
    ...config.thresholds,
    rating_ranking_success: ['rate>0.95'], // 95% success rate
    http_req_duration: ['p(95)<2000'],     // 95% of requests under 2s
    http_req_failed: ['rate<0.05'],        // Less than 5% failures
  },
  tags: {
    ...config.tags,
    test: 'rating_ranking',
    endpoint: '/rating-ranking',
  },
};

export default function () {
  // Test different pagination scenarios
  const skipOptions = [0, 10, 20, 50];
  const limitOptions = [10, 20, 50, 100];
  
  const skip = skipOptions[Math.floor(Math.random() * skipOptions.length)];
  const limit = limitOptions[Math.floor(Math.random() * limitOptions.length)];
  
  // Build URL with query parameters
  const url = getApiUrl(`/rating-ranking/?skip=${skip}&limit=${limit}`);
  
  const params = {
    headers: {
      'Authorization': `Bearer ${ACCESS_TOKEN}`,
      'Content-Type': 'application/json',
    },
    tags: {
      name: 'GET /rating-ranking',
      skip: skip.toString(),
      limit: limit.toString(),
    },
  };

  // Make request
  const response = http.get(url, params);

  // Check response
  const success = check(response, {
    'status is 200': (r) => r.status === 200,
    'response has users array': (r) => {
      try {
        const body = JSON.parse(r.body);
        return Array.isArray(body.users);
      } catch (e) {
        return false;
      }
    },
    'response has total count': (r) => {
      try {
        const body = JSON.parse(r.body);
        return typeof body.total === 'number';
      } catch (e) {
        return false;
      }
    },
    'response has pagination fields': (r) => {
      try {
        const body = JSON.parse(r.body);
        return typeof body.skip === 'number' && typeof body.limit === 'number';
      } catch (e) {
        return false;
      }
    },
    'response time < 2000ms': (r) => r.timings.duration < 2000,
    'response time < 5000ms': (r) => r.timings.duration < 5000,
  });

  ratingRankingSuccessRate.add(success);
  ratingRankingResponseTime.add(response.timings.duration);

  // Log error details if request failed
  if (!success) {
    console.error(`Request failed: ${response.status} - ${response.status_text}`);
    console.error(`URL: ${url}`);
    if (response.body) {
      try {
        const errorBody = JSON.parse(response.body);
        console.error(`Error: ${JSON.stringify(errorBody, null, 2)}`);
      } catch (e) {
        console.error(`Response body: ${response.body.substring(0, 200)}`);
      }
    }
  }

  // Simulate user think time (1-3 seconds)
  sleep(Math.random() * 2 + 1);
}

export function handleSummary(data) {
  return {
    'stdout': textSummary(data, { indent: ' ', enableColors: true }),
    'k6_rating_ranking_test_results.json': JSON.stringify(data),
  };
}

function textSummary(data, options = {}) {
  const indent = options.indent || '';
  const summary = [];
  
  summary.push(`${indent}Rating Ranking API Load Test Summary`);
  summary.push(`${indent}${'='.repeat(60)}`);
  summary.push(`${indent}Total Requests: ${data.metrics.http_reqs.values.count}`);
  summary.push(`${indent}Failed Requests: ${data.metrics.http_req_failed.values.count || 0}`);
  summary.push(`${indent}Success Rate: ${((1 - (data.metrics.http_req_failed.values.rate || 0)) * 100).toFixed(2)}%`);
  summary.push(`${indent}Avg Response Time: ${data.metrics.http_req_duration.values.avg.toFixed(2)}ms`);
  summary.push(`${indent}Min Response Time: ${data.metrics.http_req_duration.values.min.toFixed(2)}ms`);
  summary.push(`${indent}Max Response Time: ${data.metrics.http_req_duration.values.max.toFixed(2)}ms`);
  summary.push(`${indent}P90 Response Time: ${data.metrics.http_req_duration.values['p(90)'].toFixed(2)}ms`);
  summary.push(`${indent}P95 Response Time: ${data.metrics.http_req_duration.values['p(95)'].toFixed(2)}ms`);
  summary.push(`${indent}P99 Response Time: ${data.metrics.http_req_duration.values['p(99)'].toFixed(2)}ms`);
  summary.push(`${indent}Requests per Second: ${data.metrics.http_reqs.values.rate.toFixed(2)}`);
  
  if (data.metrics.rating_ranking_success) {
    summary.push(`${indent}Rating Ranking Success Rate: ${(data.metrics.rating_ranking_success.values.rate * 100).toFixed(2)}%`);
  }
  
  summary.push(`${indent}${'='.repeat(60)}`);
  
  return summary.join('\n');
}

