"""
Интеграционные тесты для эндпоинтов /sync/*.

Роутер использует get_http_client() (shared singleton) для обоих вызовов:
  1. GET users-service → список счетов
  2. POST transactions-service → синхронизация

Поэтому мокируем один shared клиент с настройкой .get и .post раздельно.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import httpx

from tests.conftest import make_mock_http_response

ACCOUNTS_LIST = [
    {"bank_account_id": 1, "bank_account_name": "Основная карта"},
    {"bank_account_id": 2, "bank_account_name": "Накопительная"},
]

SYNC_RESULT = {"synced": True, "new_transactions": 10}


# ──────────────────────────────────────────────────────────────
# POST /sync  — синхронизировать все счета
# ──────────────────────────────────────────────────────────────
class TestSyncAllAccounts:
    async def test_success(self, client):
        mock_http = AsyncMock()
        accounts_resp = make_mock_http_response(200, json_data=ACCOUNTS_LIST)
        accounts_resp.raise_for_status = MagicMock()
        mock_http.get.return_value = accounts_resp
        mock_http.post.return_value = make_mock_http_response(200, json_data=SYNC_RESULT)

        with patch("app.routers.sync.get_http_client", return_value=mock_http):
            response = await client.post("/sync")

        assert response.status_code == 200
        data = response.json()
        assert data["synced_accounts"] == 2
        assert data["total_accounts"] == 2
        assert len(data["details"]) == 2
        assert all(d["status"] == "success" for d in data["details"])

    async def test_no_accounts_returns_empty_result(self, client):
        mock_http = AsyncMock()
        accounts_resp = make_mock_http_response(200, json_data=[])
        accounts_resp.raise_for_status = MagicMock()
        mock_http.get.return_value = accounts_resp

        with patch("app.routers.sync.get_http_client", return_value=mock_http):
            response = await client.post("/sync")

        assert response.status_code == 200
        data = response.json()
        assert data["synced_accounts"] == 0
        assert data["total_transactions"] == 0
        assert data["details"] == []

    async def test_sync_upstream_error_marks_accounts_as_failed(self, client):
        mock_http = AsyncMock()
        accounts_resp = make_mock_http_response(200, json_data=ACCOUNTS_LIST)
        accounts_resp.raise_for_status = MagicMock()
        mock_http.get.return_value = accounts_resp
        mock_http.post.return_value = make_mock_http_response(500, json_data={"detail": "error"})

        with patch("app.routers.sync.get_http_client", return_value=mock_http):
            response = await client.post("/sync")

        assert response.status_code == 200
        data = response.json()
        assert data["synced_accounts"] == 0
        assert all(d["status"] == "failed" for d in data["details"])

    async def test_users_service_timeout_returns_504(self, client):
        mock_http = AsyncMock()
        mock_http.get.side_effect = httpx.TimeoutException("Timeout")

        with patch("app.routers.sync.get_http_client", return_value=mock_http):
            response = await client.post("/sync")

        assert response.status_code == 504

    async def test_users_service_http_status_error(self, client):
        mock_http = AsyncMock()
        err_resp = MagicMock()
        err_resp.status_code = 401
        err_resp.text = "Unauthorized"
        mock_users_resp = make_mock_http_response(401, json_data={"detail": "Unauthorized"})
        mock_users_resp.raise_for_status = MagicMock(
            side_effect=httpx.HTTPStatusError("error", request=MagicMock(), response=err_resp)
        )
        mock_http.get.return_value = mock_users_resp

        with patch("app.routers.sync.get_http_client", return_value=mock_http):
            response = await client.post("/sync")

        assert response.status_code == 401

    async def test_no_token_returns_401(self, client_no_auth):
        response = await client_no_auth.post("/sync")
        assert response.status_code == 401


# ──────────────────────────────────────────────────────────────
# POST /sync/{bank_account_id}  — синхронизировать один счёт
# ──────────────────────────────────────────────────────────────
class TestSyncSingleAccount:
    async def test_success(self, client):
        mock_http = AsyncMock()
        accounts_resp = make_mock_http_response(200, json_data=ACCOUNTS_LIST)
        accounts_resp.raise_for_status = MagicMock()
        mock_http.get.return_value = accounts_resp
        sync_resp = make_mock_http_response(200, json_data=SYNC_RESULT)
        sync_resp.raise_for_status = MagicMock()
        mock_http.post.return_value = sync_resp

        with patch("app.routers.sync.get_http_client", return_value=mock_http):
            response = await client.post("/sync/1")

        assert response.status_code == 200
        data = response.json()
        assert data["account_name"] == "Основная карта"
        assert data["status"] == "success"

    async def test_account_not_found_returns_404(self, client):
        mock_http = AsyncMock()
        accounts_resp = make_mock_http_response(200, json_data=ACCOUNTS_LIST)
        accounts_resp.raise_for_status = MagicMock()
        mock_http.get.return_value = accounts_resp

        with patch("app.routers.sync.get_http_client", return_value=mock_http):
            response = await client.post("/sync/999")

        assert response.status_code == 404
        assert "не найден" in response.json()["detail"]

    async def test_timeout_returns_504(self, client):
        mock_http = AsyncMock()
        mock_http.get.side_effect = httpx.TimeoutException("Timeout")

        with patch("app.routers.sync.get_http_client", return_value=mock_http):
            response = await client.post("/sync/1")

        assert response.status_code == 504

    async def test_transactions_service_http_error(self, client):
        mock_http = AsyncMock()
        accounts_resp = make_mock_http_response(200, json_data=ACCOUNTS_LIST)
        accounts_resp.raise_for_status = MagicMock()
        mock_http.get.return_value = accounts_resp

        err_resp = MagicMock()
        err_resp.status_code = 503
        err_resp.text = "Service Unavailable"
        sync_resp = make_mock_http_response(503, json_data={"detail": "unavailable"})
        sync_resp.raise_for_status = MagicMock(
            side_effect=httpx.HTTPStatusError("error", request=MagicMock(), response=err_resp)
        )
        mock_http.post.return_value = sync_resp

        with patch("app.routers.sync.get_http_client", return_value=mock_http):
            response = await client.post("/sync/1")

        assert response.status_code == 503

    async def test_no_token_returns_401(self, client_no_auth):
        response = await client_no_auth.post("/sync/1")
        assert response.status_code == 401
