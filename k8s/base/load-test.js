import http from 'k6/http';
import { check, sleep } from 'k6';
import { Rate, Trend } from 'k6/metrics';

// ---------------------------------------------------------------------------
// Custom metrics
// ---------------------------------------------------------------------------
const errorRate = new Rate('error_rate');
const backendLatency = new Trend('backend_latency_ms', true);

// ---------------------------------------------------------------------------
// Test configuration
// ---------------------------------------------------------------------------
const BASE_URL = __ENV.BASE_URL || 'http://localhost:8080';
const API_URL  = __ENV.API_URL  || 'http://localhost:8000';

export const options = {
  stages: [
    { duration: '30s', target: 10  },  // ramp-up
    { duration: '1m',  target: 50  },  // sustained load
    { duration: '30s', target: 100 },  // stress spike
    { duration: '30s', target: 0   },  // ramp-down
  ],
  thresholds: {
    http_req_failed:   ['rate<0.05'],          // <5% errors
    http_req_duration: ['p(95)<2000'],         // 95th percentile < 2 s
    error_rate:        ['rate<0.05'],
  },
};

// ---------------------------------------------------------------------------
// Helper: authenticated request headers
// ---------------------------------------------------------------------------
function headers() {
  return { 'Content-Type': 'application/json' };
}

// ---------------------------------------------------------------------------
// Main VU function
// ---------------------------------------------------------------------------
export default function () {
  // 1. Frontend health
  const frontendRes = http.get(`${BASE_URL}/`, { tags: { name: 'frontend_root' } });
  check(frontendRes, {
    'frontend status 200': (r) => r.status === 200,
  });
  errorRate.add(frontendRes.status !== 200);

  sleep(0.5);

  // 2. Backend health endpoint
  const healthRes = http.get(`${API_URL}/health`, { tags: { name: 'backend_health' } });
  check(healthRes, {
    'backend health 200': (r) => r.status === 200,
  });
  backendLatency.add(healthRes.timings.duration);
  errorRate.add(healthRes.status !== 200);

  sleep(0.5);

  // 3. Complaints list (read-heavy endpoint)
  const complaintsRes = http.get(`${API_URL}/api/complaints`, {
    headers: headers(),
    tags: { name: 'complaints_list' },
  });
  check(complaintsRes, {
    'complaints list 2xx': (r) => r.status >= 200 && r.status < 300,
  });
  errorRate.add(complaintsRes.status >= 400);

  // 4. Stats endpoint
  const statsRes = http.get(`${API_URL}/api/stats`, {
    headers: headers(),
    tags: { name: 'stats' },
  });
  check(statsRes, {
    'stats 2xx': (r) => r.status >= 200 && r.status < 300,
  });

  sleep(1);
}

// ---------------------------------------------------------------------------
// Setup: print test config
// ---------------------------------------------------------------------------
export function setup() {
  console.log(`Load test targeting: frontend=${BASE_URL}  api=${API_URL}`);
}
