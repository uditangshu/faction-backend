/**
 * k6 Authenticated Endpoints Test
 * Tests authenticated endpoints after login
 * 
 * Usage:
 *   k6 run authenticated_test.js
 *   k6 run --vus 50 --duration 2m authenticated_test.js
 */

import http from 'k6/http';
import { check, sleep } from 'k6';
import { Rate } from 'k6/metrics';
import { getApiUrl, createLoginPayload, extractAccessToken, config } from '../utils/config.js';

// Custom metrics
const authSuccessRate = new Rate('auth_success');
const endpointSuccessRate = new Rate('endpoint_success');

export const options = {
  stages: [
    { duration: '30s', target: 30 },   // Ramp up to 30 users
    { duration: '1m', target: 30 },    // Stay at 30 users
    { duration: '30s', target: 50 },   // Ramp up to 50 users
    { duration: '1m', target: 50 },     // Stay at 50 users
    { duration: '30s', target: 0 },    // Ramp down
  ],
  thresholds: {
    ...config.thresholds,
    auth_success: ['rate>0.95'],
    endpoint_success: ['rate>0.90'],
  },
  tags: {
    ...config.tags,
    test: 'authenticated',
  },
};

// Shared state for VU (Virtual User)
let accessToken = null;

export function setup() {
  // Login once per test run to get a token (optional - can also login per VU)
  const loginUrl = getApiUrl('/auth/login');
  const loginPayload = JSON.stringify(createLoginPayload());
  
  const loginResponse = http.post(loginUrl, loginPayload, {
    headers: { 'Content-Type': 'application/json' },
  });
  
  if (loginResponse.status === 200) {
    const token = extractAccessToken(loginResponse);
    return { token };
  }
  
  return { token: null };
}

export default function (data) {
  // Login per VU to get unique token
  if (!accessToken) {
    const loginUrl = getApiUrl('/auth/login');
    const loginPayload = JSON.stringify(createLoginPayload());
    
    const loginResponse = http.post(loginUrl, loginPayload, {
      headers: { 'Content-Type': 'application/json' },
      tags: { name: 'POST /auth/login' },
    });
    
    const authSuccess = check(loginResponse, {
      'login status is 200': (r) => r.status === 200,
    });
    
    authSuccessRate.add(authSuccess);
    
    if (authSuccess) {
      accessToken = extractAccessToken(loginResponse);
    } else {
      sleep(1);
      return; // Skip this iteration if login failed
    }
  }

  // Test authenticated endpoints
  const endpoints = [
    {
      name: 'GET /users/me',
      url: getApiUrl('/users/me'),
      method: 'GET',
    },
    {
      name: 'GET /streaks/me',
      url: getApiUrl('/streaks/me'),
      method: 'GET',
    },
    {
      name: 'GET /questions/qotd',
      url: getApiUrl('/questions/qotd'),
      method: 'GET',
    },
  ];

  // Randomly select an endpoint to test
  const endpoint = endpoints[Math.floor(Math.random() * endpoints.length)];
  
  const params = {
    headers: {
      'Authorization': `Bearer ${accessToken}`,
      'Content-Type': 'application/json',
    },
    tags: {
      name: endpoint.name,
    },
  };

  let response;
  if (endpoint.method === 'GET') {
    response = http.get(endpoint.url, params);
  } else {
    response = http.post(endpoint.url, null, params);
  }

  const success = check(response, {
    [`${endpoint.name} status is 200`]: (r) => r.status === 200,
    [`${endpoint.name} response time < 1000ms`]: (r) => r.timings.duration < 1000,
  });

  endpointSuccessRate.add(success);

  // Simulate user think time
  sleep(Math.random() * 3 + 1); // 1-4 seconds
}

export function handleSummary(data) {
  return {
    'stdout': textSummary(data, { indent: ' ', enableColors: true }),
    'k6_authenticated_test_results.json': JSON.stringify(data),
  };
}

function textSummary(data, options = {}) {
  const indent = options.indent || '';
  const summary = [];
  
  summary.push(`${indent}Authenticated Endpoints Test Summary`);
  summary.push(`${indent}${'='.repeat(50)}`);
  summary.push(`${indent}Total Requests: ${data.metrics.http_reqs.values.count}`);
  summary.push(`${indent}Failed Requests: ${data.metrics.http_req_failed.values.passes}`);
  summary.push(`${indent}Success Rate: ${(1 - data.metrics.http_req_failed.values.rate) * 100}%`);
  summary.push(`${indent}Avg Response Time: ${data.metrics.http_req_duration.values.avg.toFixed(2)}ms`);
  summary.push(`${indent}P95 Response Time: ${data.metrics.http_req_duration.values['p(95)'].toFixed(2)}ms`);
  summary.push(`${indent}P99 Response Time: ${data.metrics.http_req_duration.values['p(99)'].toFixed(2)}ms`);
  
  return summary.join('\n');
}

