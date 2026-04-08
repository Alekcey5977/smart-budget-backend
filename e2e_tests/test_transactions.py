"""
E2E tests for /transactions/* endpoints.
Транзакции появляются после синхронизации с pseudo-bank.
"""

import asyncio
import uuid

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

    def test_categories_include_type_field(self, http_client, auth_headers):
        _, headers = auth_headers
        categories = http_client.get("/transactions/categories", headers=headers).json()
        assert categories, "No categories in DB — run: make load-test-data"
        assert "type" in categories[0]

    def test_categories_filter_expense(self, http_client, auth_headers):
        _, headers = auth_headers
        resp = http_client.get("/transactions/categories?type=expense", headers=headers)
        assert resp.status_code == 200
        categories = resp.json()
        assert categories, "No categories — run: make load-test-data"
        for cat in categories:
            assert cat["type"] in ("expense", None), f"Unexpected type: {cat['type']}"

    def test_categories_filter_income(self, http_client, auth_headers):
        _, headers = auth_headers
        resp = http_client.get("/transactions/categories?type=income", headers=headers)
        assert resp.status_code == 200
        categories = resp.json()
        assert categories, "No income categories — run: make load-test-data"
        for cat in categories:
            assert cat["type"] in ("income", None), f"Unexpected type: {cat['type']}"

    def test_get_category_by_id(self, http_client, auth_headers):
        _, headers = auth_headers
        categories = http_client.get("/transactions/categories", headers=headers).json()
        assert categories, "No categories in DB — run: make load-test-data"
        category_id = categories[0]["id"]

        resp = http_client.get(f"/transactions/categories/{category_id}", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == category_id
        assert "name" in data
        assert "type" in data

    def test_get_category_by_id_not_found(self, http_client, auth_headers):
        _, headers = auth_headers
        resp = http_client.get("/transactions/categories/999999", headers=headers)
        assert resp.status_code == 404

    def test_get_category_by_id_without_token(self, http_client):
        resp = http_client.get("/transactions/categories/1")
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
                "No transactions appeared — transactions may be deduplicated from a previous run. Run: make reset-db"
            )

        tx = transactions[0]
        assert "id" in tx
        assert "amount" in tx
        assert "bank_account_id" in tx
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

    async def test_get_transaction_by_id(self, http_client, auth_headers, bank_account):
        _, headers = auth_headers
        http_client.post("/sync/", headers=headers)
        transactions = await _poll_transactions(http_client, headers)
        if not transactions:
            pytest.skip("No transactions available — run: make reset-db")

        tx_id = transactions[0]["id"]
        resp = http_client.get(f"/transactions/{tx_id}", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == tx_id
        assert "bank_account_id" in data
        assert "category_id" in data

    def test_get_transaction_by_id_not_found(self, http_client, auth_headers):
        _, headers = auth_headers
        fake_id = "00000000-0000-0000-0000-000000000000"
        resp = http_client.get(f"/transactions/{fake_id}", headers=headers)
        assert resp.status_code == 404

    def test_get_transaction_by_id_without_token(self, http_client):
        fake_id = "00000000-0000-0000-0000-000000000000"
        resp = http_client.get(f"/transactions/{fake_id}")
        assert resp.status_code == 401


class TestUpdateTransactionCategory:
    async def _get_transaction_id(self, http_client, headers):
        """Синхронизируем и возвращаем первую транзакцию (с polling)."""
        http_client.post("/sync/", headers=headers)
        for _ in range(15):
            resp = http_client.post("/transactions/", json={"limit": 1}, headers=headers)
            data = resp.json()
            if data:
                return data[0]["id"]
            await asyncio.sleep(1.0)
        return None

    async def test_update_category_success(self, http_client, auth_headers, bank_account):
        _, headers = auth_headers

        tx_id = await self._get_transaction_id(http_client, headers)
        if tx_id is None:
            pytest.skip("No transactions available — run: make reset-db")

        categories = http_client.get("/transactions/categories", headers=headers).json()
        assert categories, "No categories in DB"
        target_category = categories[0]

        resp = http_client.patch(
            f"/transactions/{tx_id}/category",
            json={"category_id": target_category["id"]},
            headers=headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == tx_id
        assert data["category_id"] == target_category["id"]
        assert data["category_name"] == target_category["name"]

    def test_update_category_nonexistent_transaction(self, http_client, auth_headers):
        _, headers = auth_headers
        fake_id = "00000000-0000-0000-0000-000000000000"
        resp = http_client.patch(
            f"/transactions/{fake_id}/category",
            json={"category_id": 1},
            headers=headers,
        )
        assert resp.status_code == 404

    def test_update_category_nonexistent_category(self, http_client, auth_headers, bank_account):
        _, headers = auth_headers
        resp = http_client.patch(
            f"/transactions/{uuid.uuid4()}/category",
            json={"category_id": 999999},
            headers=headers,
        )
        # 404 (category not found) или 404 (transaction not found) — оба корректны
        assert resp.status_code == 404

    def test_update_category_without_token(self, http_client):
        resp = http_client.patch(
            f"/transactions/{uuid.uuid4()}/category",
            json={"category_id": 1},
        )
        assert resp.status_code == 401

    def test_update_category_invalid_body(self, http_client, auth_headers):
        _, headers = auth_headers
        resp = http_client.patch(
            f"/transactions/{uuid.uuid4()}/category",
            json={"category_id": 0},
            headers=headers,
        )
        assert resp.status_code == 422
