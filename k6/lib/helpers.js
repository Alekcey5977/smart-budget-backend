import { check } from 'k6';
import { Rate } from 'k6/metrics';

export const errorRate = new Rate('errors');

/**
 * Wraps k6 check() and records failures in the custom error rate metric.
 * Returns true if all checks pass.
 */
export function checkStatus(res, expectedStatus, label) {
  const passed = check(res, {
    [`${label} — status ${expectedStatus}`]: (r) => r.status === expectedStatus,
  });
  if (!passed) {
    errorRate.add(1);
    console.warn(
      `[FAIL] ${label} — got ${res.status} body: ${res.body ? res.body.substring(0, 200) : '(empty)'}`,
    );
  } else {
    errorRate.add(0);
  }
  return passed;
}

/**
 * Generate a unique email address safe to use concurrently.
 * Uses __VU and __ITER to guarantee uniqueness within a run.
 */
export function randomEmail(prefix = 'k6') {
  return `${prefix}_vu${__VU}_iter${__ITER}_${Date.now()}@loadtest.example.com`;
}

/** Shared JSON headers (no auth). */
export const JSON_HEADERS = { 'Content-Type': 'application/json' };

/**
 * Build JSON + auth headers from a token object { accessToken, refreshToken }
 * or a plain access token string.
 *
 * k6 does NOT propagate HttpOnly cookies back via its jar for `localhost`,
 * so we inject the refresh_token as a Cookie header manually.
 * The gateway forwards it upstream, satisfying the jti-binding in users-service.
 */
export function authHeaders(token) {
  if (token && typeof token === 'object') {
    const headers = {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${token.accessToken}`,
    };
    if (token.refreshToken) {
      headers['Cookie'] = `refresh_token=${token.refreshToken}`;
    }
    return headers;
  }
  // Fallback: plain string — no cookie (backwards-compat)
  return {
    'Content-Type': 'application/json',
    Authorization: `Bearer ${token}`,
  };
}

export const SMOKE_THRESHOLDS = {
  http_req_failed: [{ threshold: 'rate<0.01', abortOnFail: true }],
  http_req_duration: [{ threshold: 'p(95)<1000', abortOnFail: true }],
  errors: [{ threshold: 'rate<0.01', abortOnFail: true }],
};

export const LOAD_THRESHOLDS = {
  http_req_failed: [{ threshold: 'rate<0.02', abortOnFail: false }],
  http_req_duration: [{ threshold: 'p(95)<2000', abortOnFail: false }],
  errors: [{ threshold: 'rate<0.02', abortOnFail: false }],
};

export const STRESS_THRESHOLDS = {
  http_req_failed: [{ threshold: 'rate<0.10', abortOnFail: false }],
  http_req_duration: [{ threshold: 'p(95)<5000', abortOnFail: false }],
  errors: [{ threshold: 'rate<0.10', abortOnFail: false }],
};

export const SPIKE_THRESHOLDS = {
  http_req_failed: [{ threshold: 'rate<0.20', abortOnFail: false }],
  http_req_duration: [{ threshold: 'p(99)<10000', abortOnFail: false }],
  errors: [{ threshold: 'rate<0.20', abortOnFail: false }],
};
