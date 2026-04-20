/**
 * High load test — 5000 VUs sustained.
 * Between max (3000) and extreme (10000).
 *
 * Timeline:
 *   0-10s  — ramp 0 → 1000
 *   10-20s — ramp 1000 → 3000
 *   20-35s — ramp 3000 → 5000
 *   35-55s — hold 5000
 *   55-75s — ramp 5000 → 0
 *
 * Usage:
 *   k6 run k6/high.js
 *   k6 run --env BASE_URL=http://localhost:18000 k6/high.js
 */
import http from 'k6/http';
import { checkStatus, authHeaders } from './lib/helpers.js';
import { register, login, addBankAccount, BANK_ACCOUNT_NUMBERS, BASE } from './lib/auth.js';

export const options = {
  stages: [
    { duration: '10s', target: 1000 },
    { duration: '10s', target: 3000 },
    { duration: '15s', target: 5000 },
    { duration: '20s', target: 5000 },
    { duration: '20s', target: 0 },
  ],
  thresholds: {
    http_req_failed: [{ threshold: 'rate<0.90', abortOnFail: false }],
    http_req_duration: [{ threshold: 'p(99)<45000', abortOnFail: false }],
    errors: [{ threshold: 'rate<0.90', abortOnFail: false }],
  },
};

let vuToken = null;

export function setup() {
  const users = [];
  for (let i = 0; i < BANK_ACCOUNT_NUMBERS.length; i++) {
    const email = `high_${i}_${Date.now()}@loadtest.example.com`;
    const password = 'StrongPass1!';
    try {
      register(email, password, 'High', `Seed${i}`);
      const token = login(email, password);
      addBankAccount(token, BANK_ACCOUNT_NUMBERS[i], `High Card ${i}`);
      users.push({ email, password });
    } catch (e) {
      console.warn(`high setup slot ${i}: ${e}`);
      users.push(null);
    }
  }
  return users;
}

export default function (users) {
  const slot = (__VU - 1) % users.length;
  const user = users[slot];
  if (!user) return;

  if (!vuToken) {
    try {
      vuToken = login(user.email, user.password);
    } catch (e) {
      return;
    }
  }

  const hdrs = authHeaders(vuToken);

  const meRes = http.get(`${BASE}/auth/me`, { headers: hdrs });
  if (meRes.status === 401) { vuToken = null; return; }
  checkStatus(meRes, 200, 'GET /auth/me');

  const myRes = http.get(`${BASE}/purposes/my`, { headers: hdrs });
  checkStatus(myRes, 200, 'GET /purposes/my');

  const notifRes = http.get(`${BASE}/notifications/user/me`, { headers: hdrs });
  checkStatus(notifRes, 200, 'GET /notifications/user/me');
}
