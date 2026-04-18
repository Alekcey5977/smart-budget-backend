/**
 * Stress test — find the breaking point.
 * Ramp: 0→50→100→150 VUs in steps, then cool down.
 * Total: ~5 min.
 *
 * Token cached per VU — no re-login every iteration.
 *
 * Usage:
 *   k6 run k6/stress.js
 *   k6 run --env BASE_URL=http://localhost:18000 k6/stress.js
 */
import http from 'k6/http';
import { sleep } from 'k6';
import { checkStatus, authHeaders, STRESS_THRESHOLDS } from './lib/helpers.js';
import { register, login, addBankAccount, BANK_ACCOUNT_NUMBERS, BASE } from './lib/auth.js';

export const options = {
  stages: [
    { duration: '30s', target: 50 },
    { duration: '1m', target: 50 },
    { duration: '30s', target: 100 },
    { duration: '1m', target: 100 },
    { duration: '30s', target: 150 },
    { duration: '1m', target: 150 },
    { duration: '30s', target: 0 },
  ],
  thresholds: STRESS_THRESHOLDS,
};

// Token cached at VU level — lives for the entire VU lifecycle
let vuToken = null;

export function setup() {
  const users = [];
  for (let i = 0; i < BANK_ACCOUNT_NUMBERS.length; i++) {
    const email = `stress_seed_${i}_${Date.now()}@loadtest.example.com`;
    const password = 'StrongPass1!';
    try {
      register(email, password, 'Stress', `Seed${i}`);
      const token = login(email, password);
      const baRes = addBankAccount(token, BANK_ACCOUNT_NUMBERS[i], `Stress Card ${i}`);
      if (baRes.status !== 200) {
        console.warn(`stress setup: bank account slot ${i} unavailable (${baRes.status})`);
      }
      users.push({ email, password });
    } catch (e) {
      console.warn(`stress setup slot ${i}: ${e}`);
      users.push(null);
    }
  }
  return users;
}

export default function (users) {
  const slot = (__VU - 1) % users.length;
  const user = users[slot];
  if (!user) {
    sleep(1);
    return;
  }

  // Login once per VU, reuse token for all iterations
  if (!vuToken) {
    try {
      vuToken = login(user.email, user.password);
    } catch (e) {
      console.warn(`VU ${__VU}: login failed — ${e}`);
      sleep(1);
      return;
    }
  }

  const hdrs = authHeaders(vuToken);

  // Read-heavy — самые нагруженные эндпоинты под давлением
  const meRes = http.get(`${BASE}/auth/me`, { headers: hdrs });
  if (meRes.status === 401) { vuToken = null; sleep(1); return; }
  checkStatus(meRes, 200, 'GET /auth/me');

  const txRes = http.post(
    `${BASE}/transactions/`,
    JSON.stringify({ limit: 50 }),
    { headers: hdrs },
  );
  checkStatus(txRes, 200, 'POST /transactions/');

  // Кэшируемые эндпоинты — проверяем что под нагрузкой кэш работает и не бьём БД
  const catRes = http.get(`${BASE}/transactions/categories`, { headers: hdrs });
  checkStatus(catRes, 200, 'GET /transactions/categories');

  const catMappingRes = http.get(`${BASE}/images/mappings/categories`);
  checkStatus(catMappingRes, 200, 'GET /images/mappings/categories');

  const myRes = http.get(`${BASE}/purposes/my`, { headers: hdrs });
  checkStatus(myRes, 200, 'GET /purposes/my');

  const notifRes = http.get(`${BASE}/notifications/user/me`, { headers: hdrs });
  checkStatus(notifRes, 200, 'GET /notifications/user/me');

  const histRes = http.get(`${BASE}/history/user/me`, { headers: hdrs });
  checkStatus(histRes, 200, 'GET /history/user/me');

  // Light write every 10th iteration
  if (__ITER % 10 === 0) {
    const cRes = http.post(
      `${BASE}/purposes/create`,
      JSON.stringify({
        title: `Stress Goal VU${__VU} i${__ITER}`,
        deadline: '2028-06-01T00:00:00',
        total_amount: 9999,
      }),
      { headers: hdrs },
    );
    if (cRes.status === 200) {
      http.del(`${BASE}/purposes/delete/${cRes.json().id}`, null, { headers: hdrs });
    }
  }

  sleep(Math.random() + 0.5); // 0.5–1.5s — tighter think time
}
