"""
Интеграционные тесты для эндпоинтов /sync/*.

Особенность: каждый эндпоинт делает ДВА последовательных httpx.AsyncClient вызова:
  1. GET users-service → список счетов
  2. POST transactions-service → синхронизация

Для этого используется side_effect со списком мок-контекстных менеджеров.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import httpx

from tests.conftest import make_mock_http_response

ACCOUNTS_LIST = [
    {"bank_account_id": 1, "bank_account_name": "Основная карта"},
    {"bank_account_id": 2, "bank_account_name": "Накопительная"},
]

SYNC_RESULT = {"synced": True, "new_transactions": 10}


def make_dual_mock(
    first_http: AsyncMock,
    second_http: AsyncMock,
) -> list:
    """Создаёт два контекстных менеджера для двух последовательных AsyncClient вызовов."""
    cm1 = MagicMock()
    cm1.__aenter__ = AsyncMock(return_value=first_http)
    cm1.__aexit__ = AsyncMock(return_value=False)

    cm2 = MagicMock()
    cm2.__aenter__ = AsyncMock(return_value=second_http)
    cm2.__aexit__ = AsyncMock(return_value=False)

    return [cm1, cm2]


# ──────────────────────────────────────────────────────────────
# POST /sync  — синхронизировать все счета
# ──────────────────────────────────────────────────────────────
class TestSyncAllAccounts:
    async def test_success(self, client):
        mock_users = AsyncMock()
        mock_transactions = AsyncMock()

        mock_users.get.return_value = make_mock_http_response(200, json_data=ACCOUNTS_LIST)
        mock_users.get.return_value.raise_for_status = MagicMock()

        mock_transactions.post.return_value = make_mock_http_response(200, json_data=SYNC_RESULT)

        with patch("app.routers.sync.httpx.AsyncClient") as MockClient:
            MockClient.side_effect = make_dual_mock(mock_users, mock_transactions)

            response = await client.post("/sync")

        assert response.status_code == 200
        data = response.json()
        assert data["synced_accounts"] == 2
        assert data["total_accounts"] == 2
        assert len(data["details"]) == 2
        assert all(d["status"] == "success" for d in data["details"])

    async def test_no_accounts_returns_empty_result(self, client):
        """У пользователя нет счетов → возвращаем пустой результат."""
        mock_users = AsyncMock()
        mock_users.get.return_value = make_mock_http_response(200, json_data=[])
        mock_users.get.return_value.raise_for_status = MagicMock()

        cm = MagicMock()
        cm.__aenter__ = AsyncMock(return_value=mock_users)
        cm.__aexit__ = AsyncMock(return_value=False)

        with patch("app.routers.sync.httpx.AsyncClient") as MockClient:
            MockClient.return_value = cm

            response = await client.post("/sync")

        assert response.status_code == 200
        data = response.json()
        assert data["synced_accounts"] == 0
        assert data["total_transactions"] == 0
        assert data["details"] == []

    async def test_sync_upstream_error_marks_accounts_as_failed(self, client):
        """Transactions-service вернул ошибку → все счета в статусе failed."""
        mock_users = AsyncMock()
        mock_transactions = AsyncMock()

        mock_users.get.return_value = make_mock_http_response(200, json_data=ACCOUNTS_LIST)
        mock_users.get.return_value.raise_for_status = MagicMock()

        mock_transactions.post.return_value = make_mock_http_response(500, json_data={"detail": "error"})

        with patch("app.routers.sync.httpx.AsyncClient") as MockClient:
            MockClient.side_effect = make_dual_mock(mock_users, mock_transactions)

            response = await client.post("/sync")

        assert response.status_code == 200
        data = response.json()
        assert data["synced_accounts"] == 0
        assert all(d["status"] == "failed" for d in data["details"])

    async def test_users_service_timeout_returns_504(self, client):
        """Таймаут при получении счетов из users-service → 504."""
        mock_users = AsyncMock()
        mock_users.get.side_effect = httpx.TimeoutException("Timeout")

        cm = MagicMock()
        cm.__aenter__ = AsyncMock(return_value=mock_users)
        cm.__aexit__ = AsyncMock(return_value=False)

        with patch("app.routers.sync.httpx.AsyncClient") as MockClient:
            MockClient.return_value = cm

            response = await client.post("/sync")

        assert response.status_code == 504

    async def test_users_service_http_status_error(self, client):
        """users-service вернул 401 → raise_for_status бросает HTTPStatusError."""
        mock_users = AsyncMock()

        err_resp = MagicMock()
        err_resp.status_code = 401
        err_resp.text = "Unauthorized"

        mock_users_resp = make_mock_http_response(401, json_data={"detail": "Unauthorized"})
        mock_users_resp.raise_for_status = MagicMock(
            side_effect=httpx.HTTPStatusError("error", request=MagicMock(), response=err_resp)
        )
        mock_users.get.return_value = mock_users_resp

        cm = MagicMock()
        cm.__aenter__ = AsyncMock(return_value=mock_users)
        cm.__aexit__ = AsyncMock(return_value=False)

        with patch("app.routers.sync.httpx.AsyncClient") as MockClient:
            MockClient.return_value = cm

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
        mock_users = AsyncMock()
        mock_transactions = AsyncMock()

        mock_users_resp = make_mock_http_response(200, json_data=ACCOUNTS_LIST)
        mock_users_resp.raise_for_status = MagicMock()
        mock_users.get.return_value = mock_users_resp

        mock_sync_resp = make_mock_http_response(200, json_data=SYNC_RESULT)
        mock_sync_resp.raise_for_status = MagicMock()
        mock_transactions.post.return_value = mock_sync_resp

        with patch("app.routers.sync.httpx.AsyncClient") as MockClient:
            MockClient.side_effect = make_dual_mock(mock_users, mock_transactions)

            response = await client.post("/sync/1")

        assert response.status_code == 200
        data = response.json()
        assert data["account_name"] == "Основная карта"
        assert data["status"] == "success"

    async def test_account_not_found_returns_404(self, client):
        """Счёт с указанным ID не принадлежит пользователю → 404."""
        mock_users = AsyncMock()
        mock_users_resp = make_mock_http_response(200, json_data=ACCOUNTS_LIST)
        mock_users_resp.raise_for_status = MagicMock()
        mock_users.get.return_value = mock_users_resp

        cm = MagicMock()
        cm.__aenter__ = AsyncMock(return_value=mock_users)
        cm.__aexit__ = AsyncMock(return_value=False)

        with patch("app.routers.sync.httpx.AsyncClient") as MockClient:
            MockClient.return_value = cm

            response = await client.post("/sync/999")

        assert response.status_code == 404
        assert "не найден" in response.json()["detail"]

    async def test_timeout_returns_504(self, client):
        mock_users = AsyncMock()
        mock_users.get.side_effect = httpx.TimeoutException("Timeout")

        cm = MagicMock()
        cm.__aenter__ = AsyncMock(return_value=mock_users)
        cm.__aexit__ = AsyncMock(return_value=False)

        with patch("app.routers.sync.httpx.AsyncClient") as MockClient:
            MockClient.return_value = cm

            response = await client.post("/sync/1")

        assert response.status_code == 504

    async def test_transactions_service_http_error(self, client):
        """transactions-service вернул ошибку → raise_for_status бросает HTTPStatusError."""
        mock_users = AsyncMock()
        mock_transactions = AsyncMock()

        mock_users_resp = make_mock_http_response(200, json_data=ACCOUNTS_LIST)
        mock_users_resp.raise_for_status = MagicMock()
        mock_users.get.return_value = mock_users_resp

        err_resp = MagicMock()
        err_resp.status_code = 503
        err_resp.text = "Service Unavailable"

        mock_sync_resp = make_mock_http_response(503, json_data={"detail": "unavailable"})
        mock_sync_resp.raise_for_status = MagicMock(
            side_effect=httpx.HTTPStatusError("error", request=MagicMock(), response=err_resp)
        )
        mock_transactions.post.return_value = mock_sync_resp

        with patch("app.routers.sync.httpx.AsyncClient") as MockClient:
            MockClient.side_effect = make_dual_mock(mock_users, mock_transactions)

            response = await client.post("/sync/1")

        assert response.status_code == 503

    async def test_no_token_returns_401(self, client_no_auth):
        response = await client_no_auth.post("/sync/1")
        assert response.status_code == 401
