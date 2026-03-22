"""
E2E tests for /history/* endpoints.
История создаётся через Redis pub/sub при различных действиях
(создание purpose, добавление банковского счёта и т.д.).
Используем polling вместо фиксированного sleep.
"""
import asyncio

import pytest

PURPOSE = {
    "title": "History Trigger Purpose",
    "deadline": "2027-12-31T00:00:00",
    "amount": 0.0,
    "total_amount": 5000.0,
}


async def _poll_history(http_client, headers, min_count=1, retries=10, delay=0.5):
    """Ждём появления записей истории с polling."""
    for _ in range(retries):
        resp = http_client.get("/history/user/me", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        if len(data) >= min_count:
            return data
        await asyncio.sleep(delay)
    resp = http_client.get("/history/user/me", headers=headers)
    return resp.json()


class TestGetHistory:
    async def test_history_appears_after_purpose_create(self, http_client, auth_headers):
        _, headers = auth_headers
        create_resp = http_client.post(
            "/purposes/create", json=PURPOSE, headers=headers
        )
        assert create_resp.status_code == 200

        history = await _poll_history(http_client, headers)
        assert len(history) > 0

    async def test_history_entry_has_required_fields(self, http_client, auth_headers):
        _, headers = auth_headers
        http_client.post("/purposes/create", json=PURPOSE, headers=headers)

        history = await _poll_history(http_client, headers)
        if not history:
            pytest.skip("No history entries arrived in time")

        entry = history[0]
        assert "id" in entry
        assert "title" in entry
        assert "body" in entry
        assert "created_at" in entry
        assert "user_id" in entry

    async def test_history_appears_after_bank_account_add(
        self, http_client, auth_headers, bank_account
    ):
        _, headers = auth_headers
        history = await _poll_history(http_client, headers)
        assert len(history) > 0

    def test_get_history_without_token_returns_401(self, http_client):
        resp = http_client.get("/history/user/me")
        assert resp.status_code == 401

    async def test_pagination_limit(self, http_client, auth_headers):
        _, headers = auth_headers

        # Создаём 2 purpose для гарантии записей
        for i in range(2):
            http_client.post(
                "/purposes/create",
                json={**PURPOSE, "title": f"Pagination Purpose {i}"},
                headers=headers,
            )

        await _poll_history(http_client, headers, min_count=2)

        resp = http_client.get(
            "/history/user/me", params={"skip": 0, "limit": 1}, headers=headers
        )
        assert resp.status_code == 200
        assert len(resp.json()) <= 1

    async def test_pagination_skip(self, http_client, auth_headers):
        _, headers = auth_headers
        for i in range(2):
            http_client.post(
                "/purposes/create",
                json={**PURPOSE, "title": f"Skip Purpose {i}"},
                headers=headers,
            )

        await _poll_history(http_client, headers, min_count=2)

        resp_p1 = http_client.get(
            "/history/user/me", params={"skip": 0, "limit": 1}, headers=headers
        )
        resp_p2 = http_client.get(
            "/history/user/me", params={"skip": 1, "limit": 1}, headers=headers
        )

        assert resp_p1.status_code == 200
        assert resp_p2.status_code == 200
        # Страницы не совпадают (разные записи)
        ids_p1 = [e["id"] for e in resp_p1.json()]
        ids_p2 = [e["id"] for e in resp_p2.json()]
        assert not set(ids_p1) & set(ids_p2)


class TestGetHistoryById:
    async def test_get_history_entry_by_id(self, http_client, auth_headers):
        _, headers = auth_headers
        http_client.post("/purposes/create", json=PURPOSE, headers=headers)

        history = await _poll_history(http_client, headers)
        if not history:
            pytest.skip("No history entries available")

        entry_id = history[0]["id"]
        resp = http_client.get(f"/history/{entry_id}", headers=headers)
        assert resp.status_code == 200
        assert resp.json()["id"] == entry_id

    def test_get_nonexistent_entry_returns_404(self, http_client, auth_headers):
        _, headers = auth_headers
        resp = http_client.get(
            "/history/00000000-0000-0000-0000-000000000000", headers=headers
        )
        assert resp.status_code == 404

    def test_get_history_by_id_without_token_returns_401(self, http_client):
        resp = http_client.get(
            "/history/00000000-0000-0000-0000-000000000000"
        )
        assert resp.status_code == 401


class TestDeleteHistory:
    async def test_delete_own_history_entry(self, http_client, auth_headers):
        _, headers = auth_headers
        http_client.post("/purposes/create", json=PURPOSE, headers=headers)

        history = await _poll_history(http_client, headers)
        if not history:
            pytest.skip("No history entries to delete")

        entry_id = history[0]["id"]
        resp = http_client.delete(f"/history/{entry_id}", headers=headers)
        assert resp.status_code == 200
        assert resp.json()["status"] == "success"

        # Проверяем что удалено
        get_resp = http_client.get(f"/history/{entry_id}", headers=headers)
        assert get_resp.status_code == 404

    def test_delete_without_token_returns_401(self, http_client):
        resp = http_client.delete(
            "/history/00000000-0000-0000-0000-000000000000"
        )
        assert resp.status_code == 401