/**
 * k6 Stress Test
 * Gradually increases load to find breaking point
 * 
 * Usage:
 *   k6 run stress_test.js
 *   k6 run --duration 10m stress_test.js
 */

import http from 'k6/http';
import { check, sleep } from 'k6';
import { Rate } from 'k6/metrics';
import { getApiUrl, createLoginPayload, config } from '../utils/config.js';

const errorRate = new Rate('errors');

export const options = {
  stages: [
    { duration: '1m', target: 50 },    // Ramp up to 50 users over 1 minute
    { duration: '2m', target: 50 },    // Stay at 50 users
    { duration: '1m', target: 100 },   // Ramp up to 100 users
    { duration: '2m', target: 100 },    // Stay at 100 users
    { duration: '1m', target: 200 },   // Ramp up to 200 users
    { duration: '2m', target: 200 },    // Stay at 200 users
    { duration: '1m', target: 300 },   // Ramp up to 300 users
    { duration: '2m', target: 300 },    // Stay at 300 users
    { duration: '1m', target: 500 },   // Ramp up to 500 users
    { duration: '2m', target: 500 },    // Stay at 500 users
    { duration: '1m', target: 0 },     // Ramp down
  ],
  thresholds: {
    http_req_duration: ['p(95)<2000'], // 95% of requests < 2s
    http_req_failed: ['rate<0.1'],     // Error rate < 10%
    errors: ['rate<0.05'],             // Custom error rate < 5%
  },
  tags: {
    ...config.tags,
    test: 'stress',
  },
};

export default function () {
  const url = getApiUrl('/auth/login');
  const payload = JSON.stringify(createLoginPayload());
  
  const params = {
    headers: {
      'Content-Type': 'application/json',
    },
    tags: {
      name: 'POST /auth/login (Stress Test)',
    },
  };

  const response = http.post(url, payload, params);

  const success = check(response, {
    'status is 200': (r) => r.status === 200,
    'response time < 2000ms': (r) => r.timings.duration < 2000,
  });

  errorRate.add(!success);

  // Minimal sleep to maximize load
  sleep(0.5);
}

export function handleSummary(data) {
  return {
    'stdout': textSummary(data, { indent: ' ', enableColors: true }),
    'k6_stress_test_results.json': JSON.stringify(data),
  };
}

function textSummary(data, options = {}) {
  const indent = options.indent || '';
  const summary = [];
  
  summary.push(`${indent}Stress Test Summary`);
  summary.push(`${indent}${'='.repeat(50)}`);
  summary.push(`${indent}Total Requests: ${data.metrics.http_reqs.values.count}`);
  summary.push(`${indent}Failed Requests: ${data.metrics.http_req_failed.values.passes}`);
  summary.push(`${indent}Error Rate: ${(data.metrics.http_req_failed.values.rate * 100).toFixed(2)}%`);
  summary.push(`${indent}Avg Response Time: ${data.metrics.http_req_duration.values.avg.toFixed(2)}ms`);
  summary.push(`${indent}P95 Response Time: ${data.metrics.http_req_duration.values['p(95)'].toFixed(2)}ms`);
  summary.push(`${indent}P99 Response Time: ${data.metrics.http_req_duration.values['p(99)'].toFixed(2)}ms`);
  summary.push(`${indent}Max Response Time: ${data.metrics.http_req_duration.values.max.toFixed(2)}ms`);
  
  return summary.join('\n');
}

