/**
 * k6 Load Test
 * Normal expected load
 * 50-100 concurrent users
 */

import http from 'k6/http';
import { check, sleep } from 'k6';
import { getApiUrl, createLoginPayload, extractAccessToken, config } from '../utils/config.js';

export const options = {
  stages: [
    { duration: '1m', target: 50 },   // Ramp up to 50 users
    { duration: '3m', target: 50 },   // Stay at 50 users
    { duration: '1m', target: 100 },  // Ramp up to 100 users
    { duration: '3m', target: 100 },  // Stay at 100 users
    { duration: '1m', target: 0 },     // Ramp down
  ],
  thresholds: {
    ...config.thresholds,
  },
  tags: {
    ...config.tags,
    test: 'load',
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
    
    if (loginResponse.status === 200) {
      accessToken = extractAccessToken(loginResponse);
    }
  }

  // Test various endpoints
  if (accessToken) {
    // Get user profile
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
  }
}

