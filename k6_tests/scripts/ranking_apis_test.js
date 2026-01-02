/**
 * k6 Load Test for Ranking APIs
 * Tests the following endpoints:
 * - GET /api/v1/contests/ (with type query parameter)
 * - GET /api/v1/arena-ranking/
 * - GET /api/v1/streak-ranking/
 * - GET /api/v1/contest-ranking/
 * 
 * Usage:
 *   k6 run scripts/ranking_apis_test.js
 *   k6 run --vus 50 --duration 5m scripts/ranking_apis_test.js
 *   BASE_URL=http://your-server:8000 k6 run scripts/ranking_apis_test.js
 */

import http from 'k6/http';
import { check, sleep } from 'k6';
import { Rate, Trend } from 'k6/metrics';
import { getApiUrl, createLoginPayload, extractAccessToken, config } from '../utils/config.js';

// Custom metrics
const authSuccessRate = new Rate('auth_success');
const contestsSuccessRate = new Rate('contests_success');
const arenaRankingSuccessRate = new Rate('arena_ranking_success');
const streakRankingSuccessRate = new Rate('streak_ranking_success');
const contestRankingSuccessRate = new Rate('contest_ranking_success');

// Response time trends for each endpoint
const contestsResponseTime = new Trend('contests_response_time');
const arenaRankingResponseTime = new Trend('arena_ranking_response_time');
const streakRankingResponseTime = new Trend('streak_ranking_response_time');
const contestRankingResponseTime = new Trend('contest_ranking_response_time');

export const options = {
  stages: [
    { duration: '30s', target: 20 },   // Ramp up to 20 users
  ],
  thresholds: {
    ...config.thresholds,
    // Authentication thresholds
    auth_success: ['rate>0.95'],
    
    // Endpoint success rate thresholds
    contests_success: ['rate>0.90'],
    arena_ranking_success: ['rate>0.90'],
    streak_ranking_success: ['rate>0.90'],
    contest_ranking_success: ['rate>0.90'],
    
    // Response time thresholds (p95 should be under 1 second)
    'http_req_duration{name:GET /contests}': ['p(95)<1000'],
    'http_req_duration{name:GET /arena-ranking}': ['p(95)<1000'],
    'http_req_duration{name:GET /streak-ranking}': ['p(95)<1000'],
    'http_req_duration{name:GET /contest-ranking}': ['p(95)<1000'],
    
    // Overall HTTP request thresholds
    http_req_duration: ['p(95)<1500', 'p(99)<3000'],
    http_req_failed: ['rate<0.05'], // Less than 5% failures
  },
  tags: {
    ...config.tags,
    test: 'ranking_apis',
  },
};

// Shared state for VU (Virtual User)
let accessToken = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJlNTlkMTMxMS01MDBhLTQ2MjUtYjYwYy1kZGNhOWRmMTdjMDEiLCJwaG9uZSI6Iis5MTgxMDkyODUwNDkiLCJzZXNzaW9uX2lkIjoiN2UyOTJkMmItY2QzOS00ZWVkLTg2MzctNWRkNjMzNmNjYjlkIiwiZXhwIjoxNzY3MzI2MTIyLCJ0eXBlIjoiYWNjZXNzIn0.AFR-wzQknafbCYz11ttjDO_r9lTmtx6aKYBbFOTGa4o";
/**
 * Login and get access token
 */


/**
 * Test GET /contests/ endpoint
 */
function testContests(token) {
  // Test both 'upcoming' and 'past' types
  const types = ['upcoming', 'past'];
  const type = types[Math.floor(Math.random() * types.length)];
  
  const url = getApiUrl(`/contests/?type=${type}`);
  const params = {
    headers: {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json',
    },
    tags: {
      name: 'GET /contests',
      endpoint: 'contests',
      type: type,
    },
  };
  
  const response = http.get(url, params);
  const duration = response.timings.duration;
  
  const success = check(response, {
    [`contests ${type} status is 200`]: (r) => r.status === 200,
    [`contests ${type} has contests array`]: (r) => {
      try {
        const body = JSON.parse(r.body);
        return Array.isArray(body.contests);
      } catch (e) {
        return false;
      }
    },
    [`contests ${type} response time < 2000ms`]: (r) => r.timings.duration < 2000,
  });
  
  contestsSuccessRate.add(success);
  contestsResponseTime.add(duration);
  
  return success;
}

/**
 * Test GET /arena-ranking/ endpoint
 */
function testArenaRanking(token) {
  const timeFilters = ['daily', 'weekly', 'all_time'];
  const timeFilter = timeFilters[Math.floor(Math.random() * timeFilters.length)];
  
  const url = getApiUrl(`/arena-ranking/?time_filter=${timeFilter}&skip=0&limit=20`);
  const params = {
    headers: {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json',
    },
    tags: {
      name: 'GET /arena-ranking',
      endpoint: 'arena_ranking',
      time_filter: timeFilter,
    },
  };
  
  const response = http.get(url, params);
  const duration = response.timings.duration;
  
  const success = check(response, {
    [`arena-ranking ${timeFilter} status is 200`]: (r) => r.status === 200,
    [`arena-ranking ${timeFilter} has users array`]: (r) => {
      try {
        const body = JSON.parse(r.body);
        return Array.isArray(body.users);
      } catch (e) {
        return false;
      }
    },
    [`arena-ranking ${timeFilter} response time < 2000ms`]: (r) => r.timings.duration < 2000,
  });
  
  arenaRankingSuccessRate.add(success);
  arenaRankingResponseTime.add(duration);
  
  return success;
}

/**
 * Test GET /streak-ranking/ endpoint
 */
function testStreakRanking(token) {
  const skip = Math.floor(Math.random() * 10) * 20; // Random skip: 0, 20, 40, etc.
  const limit = 20;
  
  const url = getApiUrl(`/streak-ranking/?skip=${skip}&limit=${limit}`);
  const params = {
    headers: {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json',
    },
    tags: {
      name: 'GET /streak-ranking',
      endpoint: 'streak_ranking',
    },
  };
  
  const response = http.get(url, params);
  const duration = response.timings.duration;
  
  const success = check(response, {
    'streak-ranking status is 200': (r) => r.status === 200,
    'streak-ranking has users array': (r) => {
      try {
        const body = JSON.parse(r.body);
        return Array.isArray(body.users);
      } catch (e) {
        return false;
      }
    },
    'streak-ranking response time < 2000ms': (r) => r.timings.duration < 2000,
  });
  
  streakRankingSuccessRate.add(success);
  streakRankingResponseTime.add(duration);
  
  return success;
}

/**
 * Test GET /contest-ranking/ endpoint
 */
function testContestRanking(token) {
  const filterTypes = ['best_rating_first', 'best_delta_first'];
  const filterType = filterTypes[Math.floor(Math.random() * filterTypes.length)];
  const skip = Math.floor(Math.random() * 10) * 20; // Random skip: 0, 20, 40, etc.
  const limit = 20;
  
  const url = getApiUrl(`/contest-ranking/?filter_type=${filterType}&skip=${skip}&limit=${limit}`);
  const params = {
    headers: {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json',
    },
    tags: {
      name: 'GET /contest-ranking',
      endpoint: 'contest_ranking',
      filter_type: filterType,
    },
  };
  
  const response = http.get(url, params);
  const duration = response.timings.duration;
  
  const success = check(response, {
    [`contest-ranking ${filterType} status is 200`]: (r) => r.status === 200,
    [`contest-ranking ${filterType} has users array`]: (r) => {
      try {
        const body = JSON.parse(r.body);
        return Array.isArray(body.users);
      } catch (e) {
        return false;
      }
    },
    [`contest-ranking ${filterType} response time < 2000ms`]: (r) => r.timings.duration < 2000,
  });
  
  contestRankingSuccessRate.add(success);
  contestRankingResponseTime.add(duration);
  
  return success;
}

/**
 * Main test function
 */
export default function () {
  // Login if we don't have a token

    if (!accessToken) {
      sleep(1);
      return; // Skip this iteration if login failed
    }
  
  // Test all endpoints in random order to simulate realistic user behavior
  const endpoints = [
    () => testContests(accessToken),
    () => testArenaRanking(accessToken),
    () => testStreakRanking(accessToken),
    () => testContestRanking(accessToken),
  ];
  
  // Randomly select 1-3 endpoints to test per iteration
  const numEndpoints = Math.floor(Math.random() * 3) + 1; // 1-3 endpoints
  const shuffled = endpoints.sort(() => Math.random() - 0.5);
  
  for (let i = 0; i < numEndpoints; i++) {
    shuffled[i]();
    sleep(Math.random() * 2 + 0.5); // 0.5-2.5 seconds between requests
  }
  
  // Simulate user think time
  sleep(Math.random() * 3 + 1); // 1-4 seconds
}

/**
 * Summary handler for detailed results
 */
export function handleSummary(data) {
  const summary = {
    timestamp: new Date().toISOString(),
    metrics: {
      http_reqs: {
        total: data.metrics.http_reqs.values.count,
        rate: data.metrics.http_reqs.values.rate,
      },
      http_req_duration: {
        avg: data.metrics.http_req_duration.values.avg,
        min: data.metrics.http_req_duration.values.min,
        max: data.metrics.http_req_duration.values.max,
        p95: data.metrics.http_req_duration.values['p(95)'],
        p99: data.metrics.http_req_duration.values['p(99)'],
      },
      http_req_failed: {
        rate: data.metrics.http_req_failed.values.rate,
        total: data.metrics.http_req_failed.values.passes,
      },
      auth_success: {
        rate: data.metrics.auth_success.values.rate,
      },
      contests_success: {
        rate: data.metrics.contests_success.values.rate,
      },
      arena_ranking_success: {
        rate: data.metrics.arena_ranking_success.values.rate,
      },
      streak_ranking_success: {
        rate: data.metrics.streak_ranking_success.values.rate,
      },
      contest_ranking_success: {
        rate: data.metrics.contest_ranking_success.values.rate,
      },
    },
    thresholds: {
      passed: data.root_group.checks ? 
        Object.values(data.root_group.checks).filter(c => c.passes > 0 && c.fails === 0).length : 0,
      failed: data.root_group.checks ? 
        Object.values(data.root_group.checks).filter(c => c.fails > 0).length : 0,
    },
  };
  
  return {
    'stdout': textSummary(data, { indent: ' ', enableColors: true }),
    'k6_ranking_apis_test_results.json': JSON.stringify(summary, null, 2),
  };
}

/**
 * Generate text summary
 */
function textSummary(data, options = {}) {
  const indent = options.indent || '';
  const summary = [];
  
  summary.push(`${indent}╔══════════════════════════════════════════════════════════╗`);
  summary.push(`${indent}║     Ranking APIs Load Test Summary                     ║`);
  summary.push(`${indent}╚══════════════════════════════════════════════════════════╝`);
  summary.push('');
  
  // Overall metrics
  summary.push(`${indent}Overall Metrics:`);
  summary.push(`${indent}  Total Requests: ${data.metrics.http_reqs.values.count}`);
  summary.push(`${indent}  Request Rate: ${data.metrics.http_reqs.values.rate.toFixed(2)} req/s`);
  summary.push(`${indent}  Failed Requests: ${(data.metrics.http_req_failed.values.rate * 100).toFixed(2)}%`);
  summary.push(`${indent}  Success Rate: ${((1 - data.metrics.http_req_failed.values.rate) * 100).toFixed(2)}%`);
  summary.push('');
  
  // Response times
  summary.push(`${indent}Response Times:`);
  summary.push(`${indent}  Average: ${data.metrics.http_req_duration.values.avg.toFixed(2)}ms`);
  summary.push(`${indent}  Min: ${data.metrics.http_req_duration.values.min.toFixed(2)}ms`);
  summary.push(`${indent}  Max: ${data.metrics.http_req_duration.values.max.toFixed(2)}ms`);
  summary.push(`${indent}  P95: ${data.metrics.http_req_duration.values['p(95)'].toFixed(2)}ms`);
  summary.push(`${indent}  P99: ${data.metrics.http_req_duration.values['p(99)'].toFixed(2)}ms`);
  summary.push('');
  
  // Endpoint-specific metrics
  summary.push(`${indent}Endpoint Success Rates:`);
  summary.push(`${indent}  Authentication: ${(data.metrics.auth_success.values.rate * 100).toFixed(2)}%`);
  summary.push(`${indent}  Contests: ${(data.metrics.contests_success.values.rate * 100).toFixed(2)}%`);
  summary.push(`${indent}  Arena Ranking: ${(data.metrics.arena_ranking_success.values.rate * 100).toFixed(2)}%`);
  summary.push(`${indent}  Streak Ranking: ${(data.metrics.streak_ranking_success.values.rate * 100).toFixed(2)}%`);
  summary.push(`${indent}  Contest Ranking: ${(data.metrics.contest_ranking_success.values.rate * 100).toFixed(2)}%`);
  summary.push('');
  
  // Thresholds
  if (data.root_group && data.root_group.checks) {
    const checks = Object.values(data.root_group.checks);
    const passed = checks.filter(c => c.passes > 0 && c.fails === 0).length;
    const failed = checks.filter(c => c.fails > 0).length;
    summary.push(`${indent}Thresholds:`);
    summary.push(`${indent}  Passed: ${passed}`);
    summary.push(`${indent}  Failed: ${failed}`);
  }
  
  return summary.join('\n');
}

