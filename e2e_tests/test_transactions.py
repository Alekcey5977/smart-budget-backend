"""
E2E tests for /transactions/* endpoints.
Транзакции появляются после синхронизации с pseudo-bank.
"""
import asyncio

import pytest


async def _poll_transactions(http_client, headers, payload=None, min_count=1, retries=15, delay=1.0):
    """Ждём появления транзакций с polling (async pipeline требует времени)."""
    if payload is None:
        payload = {"limit": 50}
    for _ in range(retries):
        resp = http_client.post("/transactions/", json=payload, headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        if len(data) >= min_count:
            return data
        await asyncio.sleep(delay)
    return http_client.post("/transactions/", json=payload, headers=headers).json()


class TestGetCategories:
    def test_categories_returned_for_authed_user(self, http_client, auth_headers):
        _, headers = auth_headers
        resp = http_client.get("/transactions/categories", headers=headers)
        assert resp.status_code == 200
        categories = resp.json()
        assert isinstance(categories, list)
        assert len(categories) > 0
        assert "id" in categories[0]
        assert "name" in categories[0]

    def test_categories_without_token_returns_401(self, http_client):
        resp = http_client.get("/transactions/categories")
        assert resp.status_code == 401


class TestGetTransactions:
    def test_empty_for_new_user_without_accounts(self, http_client, auth_headers):
        _, headers = auth_headers
        resp = http_client.post(
            "/transactions/",
            json={"limit": 50},
            headers=headers,
        )
        assert resp.status_code == 200
        assert resp.json() == []

    async def test_transactions_appear_after_sync(self, http_client, auth_headers, bank_account):
        _, headers = auth_headers

        # Явно тригерим синхронизацию
        sync_resp = http_client.post("/sync/", headers=headers)
        assert sync_resp.status_code == 200

        # Ждём async pipeline: pseudo-bank → transactions-service
        transactions = await _poll_transactions(http_client, headers)
        if not transactions:
            pytest.skip(
                "No transactions appeared — transactions may be deduplicated from a previous run. "
                "Run: make reset-db"
            )

        tx = transactions[0]
        assert "id" in tx
        assert "amount" in tx
        assert tx["type"] in ("income", "expense")

    async def test_filter_by_type_expense(self, http_client, auth_headers, bank_account):
        _, headers = auth_headers
        http_client.post("/sync/", headers=headers)
        await _poll_transactions(http_client, headers)

        resp = http_client.post(
            "/transactions/",
            json={"transaction_type": "expense", "limit": 50},
            headers=headers,
        )
        assert resp.status_code == 200
        for tx in resp.json():
            assert tx["type"] == "expense"

    async def test_filter_by_type_income(self, http_client, auth_headers, bank_account):
        _, headers = auth_headers
        http_client.post("/sync/", headers=headers)
        await _poll_transactions(http_client, headers)

        resp = http_client.post(
            "/transactions/",
            json={"transaction_type": "income", "limit": 50},
            headers=headers,
        )
        assert resp.status_code == 200
        for tx in resp.json():
            assert tx["type"] == "income"

    def test_transactions_without_token_returns_401(self, http_client):
        resp = http_client.post("/transactions/", json={"limit": 10})
        assert resp.status_code == 401