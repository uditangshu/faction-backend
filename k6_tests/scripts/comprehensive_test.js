/**
 * k6 Comprehensive Test
 * Tests multiple endpoints in a realistic user flow
 * 
 * Usage:
 *   k6 run comprehensive_test.js
 *   k6 run --vus 50 --duration 5m comprehensive_test.js
 */

import http from 'k6/http';
import { check, sleep } from 'k6';
import { Rate } from 'k6/metrics';
import { getApiUrl, createLoginPayload, extractAccessToken, config } from '../utils/config.js';

const loginSuccessRate = new Rate('login_success');
const endpointSuccessRate = new Rate('endpoint_success');

export const options = {
  stages: [
    { duration: '1m', target: 30 },   // Ramp up to 30 users
    { duration: '3m', target: 30 },    // Stay at 30 users
    { duration: '1m', target: 50 },    // Ramp up to 50 users
    { duration: '3m', target: 50 },      // Stay at 50 users
    { duration: '1m', target: 0 },      // Ramp down
  ],
  thresholds: {
    ...config.thresholds,
    login_success: ['rate>0.95'],
    endpoint_success: ['rate>0.90'],
  },
  tags: {
    ...config.tags,
    test: 'comprehensive',
  },
};

let accessToken = null;

export default function () {
  // Step 1: Login
  if (!accessToken) {
    const loginUrl = getApiUrl('/auth/login');
    const loginPayload = JSON.stringify(createLoginPayload());
    
    const loginResponse = http.post(loginUrl, loginPayload, {
      headers: { 'Content-Type': 'application/json' },
      tags: { name: 'POST /auth/login' },
    });
    
    const loginSuccess = check(loginResponse, {
      'login status is 200': (r) => r.status === 200,
      'login has access_token': (r) => {
        try {
          const body = JSON.parse(r.body);
          return body.access_token !== undefined;
        } catch (e) {
          return false;
        }
      },
    });
    
    loginSuccessRate.add(loginSuccess);
    
    if (loginSuccess) {
      accessToken = extractAccessToken(loginResponse);
    } else {
      sleep(1);
      return; // Skip this iteration if login failed
    }
  }

  // Step 2: Get user profile
  const profileResponse = http.get(getApiUrl('/users/me'), {
    headers: {
      'Authorization': `Bearer ${accessToken}`,
    },
    tags: { name: 'GET /users/me' },
  });

  check(profileResponse, {
    'profile status is 200': (r) => r.status === 200,
  });

  sleep(1);

  // Step 3: Get streaks
  const streaksResponse = http.get(getApiUrl('/streaks/me'), {
    headers: {
      'Authorization': `Bearer ${accessToken}`,
    },
    tags: { name: 'GET /streaks/me' },
  });

  check(streaksResponse, {
    'streaks status is 200': (r) => r.status === 200,
  });

  sleep(1);

  // Step 4: Get question of the day
  const qotdResponse = http.get(getApiUrl('/questions/qotd'), {
    headers: {
      'Authorization': `Bearer ${accessToken}`,
    },
    tags: { name: 'GET /questions/qotd' },
  });

  const qotdSuccess = check(qotdResponse, {
    'qotd status is 200': (r) => r.status === 200,
  });

  endpointSuccessRate.add(qotdSuccess);

  sleep(2);
}

export function handleSummary(data) {
  return {
    'stdout': textSummary(data, { indent: ' ', enableColors: true }),
    'k6_comprehensive_test_results.json': JSON.stringify(data),
  };
}

function textSummary(data, options = {}) {
  const indent = options.indent || '';
  const summary = [];
  
  summary.push(`${indent}Comprehensive Test Summary`);
  summary.push(`${indent}${'='.repeat(50)}`);
  summary.push(`${indent}Total Requests: ${data.metrics.http_reqs.values.count}`);
  summary.push(`${indent}Failed Requests: ${data.metrics.http_req_failed.values.passes}`);
  summary.push(`${indent}Success Rate: ${(1 - data.metrics.http_req_failed.values.rate) * 100}%`);
  summary.push(`${indent}Avg Response Time: ${data.metrics.http_req_duration.values.avg.toFixed(2)}ms`);
  summary.push(`${indent}P95 Response Time: ${data.metrics.http_req_duration.values['p(95)'].toFixed(2)}ms`);
  summary.push(`${indent}P99 Response Time: ${data.metrics.http_req_duration.values['p(99)'].toFixed(2)}ms`);
  
  return summary.join('\n');
}

