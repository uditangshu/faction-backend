/**
 * k6 Treasure Endpoints Test
 * Tests the treasure (mindmap) endpoints
 * 
 * Usage:
 *   k6 run treasure_test.js
 *   k6 run --vus 20 --duration 2m treasure_test.js
 */

import http from 'k6/http';
import { check, sleep } from 'k6';
import { Rate } from 'k6/metrics';
import { getApiUrl, createLoginPayload, extractAccessToken, config } from '../utils/config.js';

const loginSuccessRate = new Rate('login_success');
const treasureSuccessRate = new Rate('treasure_success');

export const options = {
  stages: [
    { duration: '30s', target: 10 },   // Ramp up to 10 users
    { duration: '1m', target: 10 },      // Stay at 10 users
    { duration: '30s', target: 20 },    // Ramp up to 20 users
    { duration: '1m', target: 20 },      // Stay at 20 users
    { duration: '30s', target: 0 },     // Ramp down
  ],
  thresholds: {
    ...config.thresholds,
    login_success: ['rate>0.95'],
    treasure_success: ['rate>0.90'],
  },
  tags: {
    ...config.tags,
    test: 'treasure',
  },
};

let accessToken = null;

export default function () {
  // Login
  if (!accessToken) {
    const loginUrl = getApiUrl('/auth/login');
    const loginPayload = JSON.stringify(createLoginPayload());
    
    const loginResponse = http.post(loginUrl, loginPayload, {
      headers: { 'Content-Type': 'application/json' },
      tags: { name: 'POST /auth/login' },
    });
    
    const loginSuccess = check(loginResponse, {
      'login status is 200': (r) => r.status === 200,
    });
    
    loginSuccessRate.add(loginSuccess);
    
    if (loginSuccess) {
      accessToken = extractAccessToken(loginResponse);
    } else {
      sleep(1);
      return;
    }
  }

  // Test GET /treasures endpoint
  // Note: This assumes you have subjects/chapters in the user's class
  const treasuresResponse = http.get(getApiUrl('/treasures'), {
    headers: {
      'Authorization': `Bearer ${accessToken}`,
    },
    tags: { name: 'GET /treasures' },
  });

  const treasureSuccess = check(treasuresResponse, {
    'treasures status is 200': (r) => r.status === 200,
    'treasures has treasures array': (r) => {
      try {
        const body = JSON.parse(r.body);
        return Array.isArray(body.treasures) || body.treasures !== undefined;
      } catch (e) {
        return false;
      }
    },
  });

  treasureSuccessRate.add(treasureSuccess);

  // Test with filters
  const filteredResponse = http.get(getApiUrl('/treasures'), {
    params: {
      sort_order: 'latest',
      limit: 10,
    },
    headers: {
      'Authorization': `Bearer ${accessToken}`,
    },
    tags: { name: 'GET /treasures (filtered)' },
  });

  check(filteredResponse, {
    'filtered treasures status is 200': (r) => r.status === 200,
  });

  sleep(2);
}

export function handleSummary(data) {
  return {
    'stdout': textSummary(data, { indent: ' ', enableColors: true }),
    'k6_treasure_test_results.json': JSON.stringify(data),
  };
}

function textSummary(data, options = {}) {
  const indent = options.indent || '';
  const summary = [];
  
  summary.push(`${indent}Treasure Endpoints Test Summary`);
  summary.push(`${indent}${'='.repeat(50)}`);
  summary.push(`${indent}Total Requests: ${data.metrics.http_reqs.values.count}`);
  summary.push(`${indent}Failed Requests: ${data.metrics.http_req_failed.values.passes}`);
  summary.push(`${indent}Success Rate: ${(1 - data.metrics.http_req_failed.values.rate) * 100}%`);
  summary.push(`${indent}Avg Response Time: ${data.metrics.http_req_duration.values.avg.toFixed(2)}ms`);
  summary.push(`${indent}P95 Response Time: ${data.metrics.http_req_duration.values['p(95)'].toFixed(2)}ms`);
  summary.push(`${indent}P99 Response Time: ${data.metrics.http_req_duration.values['p(99)'].toFixed(2)}ms`);
  
  return summary.join('\n');
}

