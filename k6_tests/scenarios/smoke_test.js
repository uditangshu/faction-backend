/**
 * k6 Smoke Test
 * Quick test to verify system is working
 * Low load - 1-5 users
 */

import http from 'k6/http';
import { check } from 'k6';
import { getApiUrl, createLoginPayload, config } from '../utils/config.js';

export const options = {
  vus: 1,
  duration: '30s',
  thresholds: {
    http_req_duration: ['p(95)<500'],
    http_req_failed: ['rate<0.01'],
  },
  tags: {
    ...config.tags,
    test: 'smoke',
  },
};

export default function () {
  const url = getApiUrl('/auth/login');
  const payload = JSON.stringify(createLoginPayload());
  
  const response = http.post(url, payload, {
    headers: { 'Content-Type': 'application/json' },
    tags: { name: 'POST /auth/login' },
  });

  check(response, {
    'status is 200': (r) => r.status === 200,
    'has access_token': (r) => {
      try {
        const body = JSON.parse(r.body);
        return body.access_token !== undefined;
      } catch (e) {
        return false;
      }
    },
  });
}

