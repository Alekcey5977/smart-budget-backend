/**
 * Smoke test — 1 VU, 30s.
 * Verifies that every critical endpoint responds correctly before
 * running heavier scenarios. Aborts on first threshold breach.
 *
 * Usage:
 *   k6 run k6/smoke.js
 *   k6 run --env BASE_URL=http://localhost:18000 k6/smoke.js
 */
import http from 'k6/http';
import { sleep } from 'k6';
import { checkStatus, authHeaders, SMOKE_THRESHOLDS } from './lib/helpers.js';
import { register, login, addBankAccount, BANK_ACCOUNT_NUMBERS, BASE } from './lib/auth.js';

export const options = {
  vus: 1,
  duration: '30s',
  thresholds: SMOKE_THRESHOLDS,
};

// Token cached at VU level — lives for the entire VU lifecycle
let vuToken = null;

// Register user + add bank account once before iterations start
export function setup() {
  const email = `smoke_${Date.now()}@loadtest.example.com`;
  const password = 'StrongPass1!';
  register(email, password, 'Smoke', 'Test');
  const token = login(email, password);
  for (const num of BANK_ACCOUNT_NUMBERS) {
    const res = addBankAccount(token, num, 'Smoke Card');
    if (res.status === 200) break;
  }
  return { email, password };
}

export default function (data) {
  // Login once per VU, reuse token across iterations
  if (!vuToken) {
    vuToken = login(data.email, data.password);
  }
  const hdrs = authHeaders(vuToken);

  // 1. GET /auth/me
  const meRes = http.get(`${BASE}/auth/me`, { headers: hdrs });
  if (meRes.status === 401) { vuToken = null; return; }
  checkStatus(meRes, 200, 'GET /auth/me');

  // 2. GET /users/me/bank_accounts
  const baRes = http.get(`${BASE}/users/me/bank_accounts`, { headers: hdrs });
  checkStatus(baRes, 200, 'GET /users/me/bank_accounts');

  // 3. GET /transactions/categories (cached, 12h TTL)
  const catRes = http.get(`${BASE}/transactions/categories`, { headers: hdrs });
  checkStatus(catRes, 200, 'GET /transactions/categories');

  // 3b. POST /transactions/categories/summary — агрегация по категориям
  const sumRes = http.post(
    `${BASE}/transactions/categories/summary`,
    JSON.stringify({ transaction_type: 'expense' }),
    { headers: hdrs },
  );
  checkStatus(sumRes, 200, 'POST /transactions/categories/summary');

  // 4. POST /transactions/ — основной список транзакций
  const txRes = http.post(
    `${BASE}/transactions/`,
    JSON.stringify({ limit: 10 }),
    { headers: hdrs },
  );
  checkStatus(txRes, 200, 'POST /transactions/');

  // 5. GET /images/avatars/default — публичный, кэшируется 6ч, бьётся при каждом открытии приложения
  const avatarsRes = http.get(`${BASE}/images/avatars/default`);
  checkStatus(avatarsRes, 200, 'GET /images/avatars/default');

  // 6. GET /images/mappings/categories — публичный, кэшируется 6ч
  const catMappingRes = http.get(`${BASE}/images/mappings/categories`);
  checkStatus(catMappingRes, 200, 'GET /images/mappings/categories');

  // 7. GET /images/mappings/merchants — публичный, кэшируется 6ч
  const merMappingRes = http.get(`${BASE}/images/mappings/merchants`);
  checkStatus(merMappingRes, 200, 'GET /images/mappings/merchants');

  // 8. Create purpose → read → delete
  const createRes = http.post(
    `${BASE}/purposes/create`,
    JSON.stringify({ title: 'Smoke Purpose', deadline: '2027-01-01T00:00:00', total_amount: 1000 }),
    { headers: hdrs },
  );
  if (checkStatus(createRes, 200, 'POST /purposes/create')) {
    const purposeId = createRes.json().id;

    const myRes = http.get(`${BASE}/purposes/my`, { headers: hdrs });
    checkStatus(myRes, 200, 'GET /purposes/my');

    http.del(`${BASE}/purposes/delete/${purposeId}`, null, { headers: hdrs });
  }

  // 9. GET /notifications/user/me
  const notifRes = http.get(`${BASE}/notifications/user/me`, { headers: hdrs });
  checkStatus(notifRes, 200, 'GET /notifications/user/me');

  // 10. GET /history/user/me
  const histRes = http.get(`${BASE}/history/user/me`, { headers: hdrs });
  checkStatus(histRes, 200, 'GET /history/user/me');

  sleep(1);
}
