/**
 * k6 Authentication Test
 * Tests login endpoint with various load scenarios
 * 
 * Usage:
 *   k6 run auth_test.js
 *   k6 run --vus 100 --duration 30s auth_test.js
 *   BASE_URL=http://your-server:8000 k6 run auth_test.js
 */

import http from 'k6/http';
import { check, sleep } from 'k6';
import { Rate } from 'k6/metrics';
import { getApiUrl, createLoginPayload, config } from '../utils/config.js';

// Custom metrics
const loginSuccessRate = new Rate('login_success');
const loginFailureRate = new Rate('login_failure');

export const options = {
  stages: [
    { duration: '30s', target: 50 },   // Ramp up to 50 users
    { duration: '1m', target: 50 },    // Stay at 50 users
    { duration: '30s', target: 100 }, // Ramp up to 100 users
    { duration: '1m', target: 100 },    // Stay at 100 users
    { duration: '30s', target: 0 },     // Ramp down to 0 users
  ],
  thresholds: {
    ...config.thresholds,
    login_success: ['rate>0.95'], // 95% success rate
    login_failure: ['rate<0.05'],  // Less than 5% failure rate
  },
  tags: {
    ...config.tags,
    test: 'authentication',
  },
};

export default function () {
  const url = getApiUrl('/auth/login');
  const payload = JSON.stringify(createLoginPayload());
  
  const params = {
    headers: {
      'Content-Type': 'application/json',
      'User-Agent': 'k6-load-test/1.0',
    },
    tags: {
      name: 'POST /auth/login',
    },
  };

  const response = http.post(url, payload, params);

  // Check response
  const success = check(response, {
    'status is 200': (r) => r.status === 200,
    'response has access_token': (r) => {
      try {
        const body = JSON.parse(r.body);
        return body.access_token !== undefined;
      } catch (e) {
        return false;
      }
    },
    'response has refresh_token': (r) => {
      try {
        const body = JSON.parse(r.body);
        return body.refresh_token !== undefined;
      } catch (e) {
        return false;
      }
    },
    'response time < 500ms': (r) => r.timings.duration < 500,
  });

  // Track custom metrics
  loginSuccessRate.add(success);
  loginFailureRate.add(!success);

  // Small sleep to simulate user think time
  sleep(Math.random() * 2 + 1); // 1-3 seconds
}

export function handleSummary(data) {
  return {
    'stdout': textSummary(data, { indent: ' ', enableColors: true }),
    'k6_auth_test_results.json': JSON.stringify(data),
  };
}

function textSummary(data, options = {}) {
  const indent = options.indent || '';
  const summary = [];
  
  summary.push(`${indent}Authentication Test Summary`);
  summary.push(`${indent}${'='.repeat(50)}`);
  summary.push(`${indent}Total Requests: ${data.metrics.http_reqs.values.count}`);
  summary.push(`${indent}Failed Requests: ${data.metrics.http_req_failed.values.passes}`);
  summary.push(`${indent}Success Rate: ${(1 - data.metrics.http_req_failed.values.rate) * 100}%`);
  summary.push(`${indent}Avg Response Time: ${data.metrics.http_req_duration.values.avg.toFixed(2)}ms`);
  summary.push(`${indent}P95 Response Time: ${data.metrics.http_req_duration.values['p(95)'].toFixed(2)}ms`);
  summary.push(`${indent}P99 Response Time: ${data.metrics.http_req_duration.values['p(99)'].toFixed(2)}ms`);
  
  return summary.join('\n');
}

