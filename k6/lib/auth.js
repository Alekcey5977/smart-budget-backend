import http from 'k6/http';
import { JSON_HEADERS, authHeaders } from './helpers.js';

const BASE_URL = __ENV.BASE_URL || 'http://localhost:8000';

export const BASE = BASE_URL;

// 10 test account numbers loaded by `make load-test-data`
export const BANK_ACCOUNT_NUMBERS = [
  '40817810099910004312',
  '40817810099910004313',
  '40817810099910004314',
  '40817810099910004315',
  '40817810099910004316',
  '40817810099910004317',
  '40817810099910004318',
  '40817810099910004319',
  '40817810099910004320',
  '40817810099910004321',
];

/**
 * Register a new user. Throws on failure.
 */
export function register(email, password = 'StrongPass1!', firstName = 'Load', lastName = 'Test') {
  const res = http.post(
    `${BASE_URL}/auth/register`,
    JSON.stringify({ email, password, first_name: firstName, last_name: lastName }),
    { headers: JSON_HEADERS },
  );
  if (res.status === 0) {
    throw new Error(`register failed: cannot connect to ${BASE_URL} — is the test stack running? (make test-e2e-start)`);
  }
  if (res.status !== 200) {
    throw new Error(`register failed for ${email}: HTTP ${res.status} — ${res.body}`);
  }
  return res.json();
}

/**
 * Log in and return { accessToken, refreshToken }.
 * k6 does not store HttpOnly cookies for localhost automatically,
 * so we extract refresh_token from the Set-Cookie header manually.
 * Throws on failure.
 */
export function login(email, password = 'StrongPass1!') {
  const res = http.post(
    `${BASE_URL}/auth/login`,
    JSON.stringify({ email, password }),
    { headers: JSON_HEADERS },
  );
  if (res.status === 0) {
    throw new Error(`login failed: cannot connect to ${BASE_URL} — is the test stack running? (make test-e2e-start)`);
  }
  if (res.status !== 200) {
    throw new Error(`login failed for ${email}: HTTP ${res.status} — ${res.body}`);
  }

  // Extract refresh_token from Set-Cookie manually (k6 jar ignores HttpOnly for localhost)
  let refreshToken = null;
  const setCookie = res.headers['Set-Cookie'] || res.headers['set-cookie'] || '';
  const match = setCookie.match(/refresh_token=([^;]+)/);
  if (match) {
    refreshToken = match[1];
  }

  return {
    accessToken: res.json().access_token,
    refreshToken,
  };
}

/**
 * Register + login in one call. Returns { email, password, token }.
 */
export function registerAndLogin(email, password = 'StrongPass1!') {
  register(email, password);
  const token = login(email, password);
  return { email, password, token };
}

/**
 * Add a bank account. Returns the k6 response object.
 */
export function addBankAccount(token, accountNumber, name = 'Load Test Card') {
  return http.post(
    `${BASE_URL}/users/me/bank_account`,
    JSON.stringify({
      bank_account_number: accountNumber,
      bank_account_name: name,
      bank: 'TestBank',
    }),
    {
      headers: authHeaders(token),
      // 400 = account already taken — expected outcome, not a failure
      responseCallback: http.expectedStatuses(200, 400),
    },
  );
}

export { authHeaders };
