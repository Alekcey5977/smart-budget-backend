/**
 * Load test — realistic traffic.
 * Ramp: 0→50 VUs over 1 min, hold 50 VUs for 2 min, ramp down 1 min.
 * Total: ~4 min.
 *
 * setup() creates 10 seed users (one per bank account number) before VUs start.
 * VUs pick a slot by (__VU - 1) % 10.
 * Token is cached per VU — no re-login every iteration.
 *
 * Usage:
 *   k6 run k6/load.js
 *   k6 run --env BASE_URL=http://localhost:18000 k6/load.js
 */
import http from 'k6/http';
import { sleep } from 'k6';
import { checkStatus, authHeaders, LOAD_THRESHOLDS } from './lib/helpers.js';
import { register, login, addBankAccount, BANK_ACCOUNT_NUMBERS, BASE } from './lib/auth.js';

export const options = {
  stages: [
    { duration: '1m', target: 50 },
    { duration: '2m', target: 50 },
    { duration: '1m', target: 0 },
  ],
  thresholds: LOAD_THRESHOLDS,
};

// Token cached at VU level — lives for the entire VU lifecycle, no re-login per iteration
let vuToken = null;

export function setup() {
  const users = [];
  for (let i = 0; i < BANK_ACCOUNT_NUMBERS.length; i++) {
    const email = `load_seed_${i}_${Date.now()}@loadtest.example.com`;
    const password = 'StrongPass1!';
    try {
      register(email, password, 'Seed', `User${i}`);
      const token = login(email, password);
      const baRes = addBankAccount(token, BANK_ACCOUNT_NUMBERS[i], `Seed Card ${i}`);
      if (baRes.status !== 200) {
        console.warn(`setup: bank account slot ${i} unavailable (${baRes.status})`);
      }
      users.push({ email, password });
    } catch (e) {
      console.warn(`setup slot ${i} error: ${e}`);
      users.push(null);
    }
  }
  console.log(`setup complete — ${users.filter(Boolean).length}/10 seed users ready`);
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

  let hdrs = authHeaders(vuToken);

  // --- Read-only flow (every iteration) ---

  const meRes = http.get(`${BASE}/auth/me`, { headers: hdrs });
  if (meRes.status === 401) { vuToken = null; sleep(1); return; }
  checkStatus(meRes, 200, 'GET /auth/me');

  const baRes = http.get(`${BASE}/users/me/bank_accounts`, { headers: hdrs });
  checkStatus(baRes, 200, 'GET /users/me/bank_accounts');

  // Категории — кэшируются 12ч, после первого запроса бьют Redis, не БД
  const catRes = http.get(`${BASE}/transactions/categories`, { headers: hdrs });
  checkStatus(catRes, 200, 'GET /transactions/categories');

  const txRes = http.post(
    `${BASE}/transactions/`,
    JSON.stringify({ limit: 50 }),
    { headers: hdrs },
  );
  checkStatus(txRes, 200, 'POST /transactions/');

  // Изображения — публичные, кэшируются 6ч, бьются при каждом открытии приложения
  const avatarsRes = http.get(`${BASE}/images/avatars/default`);
  checkStatus(avatarsRes, 200, 'GET /images/avatars/default');

  const catMappingRes = http.get(`${BASE}/images/mappings/categories`);
  checkStatus(catMappingRes, 200, 'GET /images/mappings/categories');

  const notifRes = http.get(`${BASE}/notifications/user/me`, { headers: hdrs });
  checkStatus(notifRes, 200, 'GET /notifications/user/me');

  const histRes = http.get(`${BASE}/history/user/me`, { headers: hdrs });
  checkStatus(histRes, 200, 'GET /history/user/me');

  // --- Write flow: create + delete purpose every 5th iteration ---
  if (__ITER % 5 === 0) {
    const createRes = http.post(
      `${BASE}/purposes/create`,
      JSON.stringify({
        title: `Load Goal VU${__VU} i${__ITER}`,
        deadline: '2027-01-01T00:00:00',
        total_amount: 5000,
      }),
      { headers: hdrs },
    );
    if (checkStatus(createRes, 200, 'POST /purposes/create')) {
      http.del(`${BASE}/purposes/delete/${createRes.json().id}`, null, { headers: hdrs });
    }
  } else {
    const myRes = http.get(`${BASE}/purposes/my`, { headers: hdrs });
    checkStatus(myRes, 200, 'GET /purposes/my');
  }

  sleep(Math.random() * 2 + 1); // 1–3s think time
}
