/**
 * k6 Spike Test
 * Sudden spike in traffic to test system resilience
 */

import http from 'k6/http';
import { check, sleep } from 'k6';
import { getApiUrl, createLoginPayload, config } from '../utils/config.js';

export const options = {
  stages: [
    { duration: '10s', target: 100 },  // Normal load
    { duration: '1m', target: 100 },  // Stay normal
    { duration: '10s', target: 1000 }, // Spike to 1000 users
    { duration: '1m', target: 1000 },  // Stay at spike
    { duration: '10s', target: 100 },  // Back to normal
    { duration: '1m', target: 100 },   // Stay normal
    { duration: '10s', target: 0 },    // Ramp down
  ],
  thresholds: {
    http_req_duration: ['p(95)<3000'], // More lenient during spike
    http_req_failed: ['rate<0.2'],     // Allow up to 20% errors during spike
  },
  tags: {
    ...config.tags,
    test: 'spike',
  },
};

export default function () {
  const url = getApiUrl('/auth/login');
  const payload = JSON.stringify(createLoginPayload());
  
  const response = http.post(url, payload, {
    headers: { 'Content-Type': 'application/json' },
    tags: { name: 'POST /auth/login (Spike Test)' },
  });

  check(response, {
    'status is 200 or 429': (r) => r.status === 200 || r.status === 429, // Allow rate limiting
  });

  sleep(0.5);
}

