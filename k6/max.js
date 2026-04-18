/**
 * Maximum load test — find the absolute breaking point.
 * Ramps aggressively to 3000 VUs over ~1 minute.
 * No sleep — maximum request pressure.
 *
 * Goal: observe at what VU count the system collapses (error rate spikes,
 * latency explodes, or 504s dominate). Thresholds are intentionally loose —
 * this test is for observation, not pass/fail.
 *
 * Timeline:
 *   0-10s  — ramp 0 → 500
 *   10-20s — ramp 500 → 1500
 *   20-35s — ramp 1500 → 3000
 *   35-50s — hold 3000
 *   50-60s — ramp 3000 → 0
 *
 * Token cached per VU — avoids 3000 simultaneous logins during ramp.
 *
 * Usage:
 *   k6 run k6/max.js
 *   k6 run --env BASE_URL=http://localhost:18000 k6/max.js
 */
import http from 'k6/http';
import { checkStatus, authHeaders } from './lib/helpers.js';
import { register, login, addBankAccount, BANK_ACCOUNT_NUMBERS, BASE } from './lib/auth.js';

export const options = {
  stages: [
    { duration: '10s', target: 500 },
    { duration: '10s', target: 1500 },
    { duration: '15s', target: 3000 },
    { duration: '15s', target: 3000 },
    { duration: '10s', target: 0 },
  ],
  thresholds: {
    // Very loose — we just want to observe, not fail the test
    http_req_failed: [{ threshold: 'rate<0.80', abortOnFail: false }],
    http_req_duration: [{ threshold: 'p(99)<30000', abortOnFail: false }],
    errors: [{ threshold: 'rate<0.80', abortOnFail: false }],
  },
};

// Token cached at VU level — critical for max test: avoids 3000 simultaneous logins
let vuToken = null;

export function setup() {
  const users = [];
  for (let i = 0; i < BANK_ACCOUNT_NUMBERS.length; i++) {
    const email = `max_seed_${i}_${Date.now()}@loadtest.example.com`;
    const password = 'StrongPass1!';
    try {
      register(email, password, 'Max', `Seed${i}`);
      const token = login(email, password);
      addBankAccount(token, BANK_ACCOUNT_NUMBERS[i], `Max Card ${i}`);
      users.push({ email, password });
    } catch (e) {
      console.warn(`max setup slot ${i}: ${e}`);
      users.push(null);
    }
  }
  return users;
}

export default function (users) {
  const slot = (__VU - 1) % users.length;
  const user = users[slot];
  if (!user) return;

  // Login once per VU, reuse token for all iterations
  if (!vuToken) {
    try {
      vuToken = login(user.email, user.password);
    } catch (e) {
      return;
    }
  }

  const hdrs = authHeaders(vuToken);

  // Cheapest endpoints only — maximum concurrent pressure
  const meRes = http.get(`${BASE}/auth/me`, { headers: hdrs });
  if (meRes.status === 401) { vuToken = null; return; }
  checkStatus(meRes, 200, 'GET /auth/me');

  const myRes = http.get(`${BASE}/purposes/my`, { headers: hdrs });
  checkStatus(myRes, 200, 'GET /purposes/my');

  const notifRes = http.get(`${BASE}/notifications/user/me`, { headers: hdrs });
  checkStatus(notifRes, 200, 'GET /notifications/user/me');

  // No sleep — maximum request rate
}
