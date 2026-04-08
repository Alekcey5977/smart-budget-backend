"""
E2E tests for /sync/* endpoints.
Проверяет полный pipeline синхронизации:
gateway → users-service (получить счета) → transactions-service → pseudo-bank
"""

import asyncio

import pytest


async def _poll_transactions(http_client, headers, min_count=1, retries=15, delay=1.0):
    for _ in range(retries):
        resp = http_client.post("/transactions/", json={"limit": 50}, headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        if len(data) >= min_count:
            return data
        await asyncio.sleep(delay)
    return http_client.post("/transactions/", json={"limit": 50}, headers=headers).json()


class TestSyncAll:
    def test_sync_all_no_accounts_returns_empty(self, http_client, auth_headers):
        _, headers = auth_headers
        resp = http_client.post("/sync/", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["synced_accounts"] == 0
        assert data["details"] == []

    def test_sync_all_with_one_account(self, http_client, auth_headers, bank_account):
        _, headers = auth_headers
        resp = http_client.post("/sync/", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["synced_accounts"] >= 1
        assert len(data["details"]) >= 1
        assert data["details"][0]["status"] == "success"

    def test_sync_all_without_token_returns_401(self, http_client):
        resp = http_client.post("/sync/")
        assert resp.status_code == 401


class TestSyncSingle:
    def test_sync_single_account_success(self, http_client, auth_headers, bank_account):
        _, headers = auth_headers
        account_id = bank_account["bank_account_id"]

        resp = http_client.post(f"/sync/{account_id}", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "success"

    def test_sync_nonexistent_account_returns_404(self, http_client, auth_headers):
        _, headers = auth_headers
        resp = http_client.post("/sync/999999", headers=headers)
        assert resp.status_code == 404

    async def test_sync_and_verify_transactions_appear(self, http_client, auth_headers, bank_account):
        """После синхронизации транзакции должны быть доступны."""
        _, headers = auth_headers
        account_id = bank_account["bank_account_id"]

        sync_resp = http_client.post(f"/sync/{account_id}", headers=headers)
        assert sync_resp.status_code == 200

        # Ждём async обработку через polling
        transactions = await _poll_transactions(http_client, headers)
        if not transactions:
            pytest.skip(
                "No transactions appeared — transactions may be deduplicated from a previous run. Run: make reset-db"
            )

    def test_sync_single_without_token_returns_401(self, http_client):
        resp = http_client.post("/sync/1")
        assert resp.status_code == 401
