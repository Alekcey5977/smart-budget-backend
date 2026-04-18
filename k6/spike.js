/**
 * Spike test — sudden burst of 1000 VUs for 10s.
 * Models a sudden viral traffic event.
 * Goal: observe behaviour under shock load and measure recovery.
 *
 * Timeline:
 *   0-10s  — warm-up at 20 VUs
 *   10-20s — spike to 1000 VUs
 *   20-30s — drop back to 20 VUs
 *   30-60s — hold at 20 VUs (confirm recovery)
 *
 * Token cached per VU — avoids login thundering herd during spike ramp.
 *
 * Usage:
 *   k6 run k6/spike.js
 *   k6 run --env BASE_URL=http://localhost:18000 k6/spike.js
 */
import http from 'k6/http';
import { sleep } from 'k6';
import { checkStatus, authHeaders, SPIKE_THRESHOLDS } from './lib/helpers.js';
import { register, login, addBankAccount, BANK_ACCOUNT_NUMBERS, BASE } from './lib/auth.js';

export const options = {
  stages: [
    { duration: '10s', target: 20 },
    { duration: '10s', target: 1000 },
    { duration: '10s', target: 20 },
    { duration: '30s', target: 20 },
  ],
  thresholds: SPIKE_THRESHOLDS,
};

// Token cached at VU level — critical for spike: avoids 1000 simultaneous logins on ramp
let vuToken = null;

export function setup() {
  const users = [];
  for (let i = 0; i < BANK_ACCOUNT_NUMBERS.length; i++) {
    const email = `spike_seed_${i}_${Date.now()}@loadtest.example.com`;
    const password = 'StrongPass1!';
    try {
      register(email, password, 'Spike', `Seed${i}`);
      const token = login(email, password);
      addBankAccount(token, BANK_ACCOUNT_NUMBERS[i], `Spike Card ${i}`);
      users.push({ email, password });
    } catch (e) {
      console.warn(`spike setup slot ${i}: ${e}`);
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
      sleep(0.5);
      return;
    }
  }

  const hdrs = authHeaders(vuToken);

  // Cheapest, most-hit endpoints — simulates everyone opening the app at once
  const meRes = http.get(`${BASE}/auth/me`, { headers: hdrs });
  if (meRes.status === 401) { vuToken = null; return; }
  checkStatus(meRes, 200, 'GET /auth/me');

  const myRes = http.get(`${BASE}/purposes/my`, { headers: hdrs });
  checkStatus(myRes, 200, 'GET /purposes/my');

  const notifRes = http.get(`${BASE}/notifications/user/me`, { headers: hdrs });
  checkStatus(notifRes, 200, 'GET /notifications/user/me');

  // No sleep — maximum request rate during spike window
}
