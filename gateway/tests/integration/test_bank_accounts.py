"""
Интеграционные тесты для эндпоинтов /users/me/bank_account*.

Downstream (users-service) мокается через patch("app.routers.bank_accounts.get_http_client").
Зависимость get_current_user переопределяется через dependency_overrides.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import httpx

from tests.conftest import make_mock_http_response

BANK_ACCOUNT_REQUEST = {
    "bank_account_number": "40817810099910004312",
    "bank_account_name": "Основная карта",
    "bank": "Сбербанк",
}

BANK_ACCOUNT_RESPONSE = {
    "bank_account_id": 1,
    "bank_account_name": "Основная карта",
    "currency": "RUB",
    "bank": "Сбербанк",
    "balance": "125450.75",
}

BANK_ACCOUNTS_LIST = [
    {
        "bank_account_id": 1,
        "bank_account_name": "Основная карта",
        "currency": "RUB",
        "bank": "Сбербанк",
        "balance": "125450.75",
    },
    {
        "bank_account_id": 2,
        "bank_account_name": "Накопительная",
        "currency": "RUB",
        "bank": "Тинькофф",
        "balance": "50000.00",
    },
]


# ──────────────────────────────────────────────────────────────
# POST /users/me/bank_account  — добавить банковский счёт
# ──────────────────────────────────────────────────────────────
class TestAddBankAccount:
    async def test_success(self, client):
        mock_http = AsyncMock()
        mock_resp = make_mock_http_response(200, json_data=BANK_ACCOUNT_RESPONSE)
        mock_resp.raise_for_status = MagicMock()
        mock_http.post.return_value = mock_resp
        with patch("app.routers.bank_accounts.get_http_client", return_value=mock_http):
            response = await client.post("/users/me/bank_account", json=BANK_ACCOUNT_REQUEST)

        assert response.status_code == 200
        data = response.json()
        assert data["bank_account_id"] == 1
        assert data["bank"] == "Сбербанк"

    async def test_duplicate_account_returns_400(self, client):
        mock_http = AsyncMock()
        mock_http.post.return_value = make_mock_http_response(
            400, json_data={"detail": "Bank account with this number already exists"}
        )
        with patch("app.routers.bank_accounts.get_http_client", return_value=mock_http):
            response = await client.post("/users/me/bank_account", json=BANK_ACCOUNT_REQUEST)

        assert response.status_code == 400
        assert "already exists" in response.json()["detail"]

    async def test_account_not_in_bank_returns_404(self, client):
        mock_http = AsyncMock()
        mock_http.post.return_value = make_mock_http_response(404, json_data={"detail": "Not found"})
        with patch("app.routers.bank_accounts.get_http_client", return_value=mock_http):
            response = await client.post("/users/me/bank_account", json=BANK_ACCOUNT_REQUEST)

        assert response.status_code == 404

    async def test_upstream_5xx_raises_http_status_error(self, client):
        mock_http = AsyncMock()
        mock_resp = make_mock_http_response(500, json_data={"detail": "Internal"})
        mock_resp.text = "Internal Server Error"
        err_resp = MagicMock()
        err_resp.status_code = 500
        err_resp.text = "Internal Server Error"
        mock_resp.raise_for_status = MagicMock(
            side_effect=httpx.HTTPStatusError("error", request=MagicMock(), response=err_resp)
        )
        mock_http.post.return_value = mock_resp
        with patch("app.routers.bank_accounts.get_http_client", return_value=mock_http):
            response = await client.post("/users/me/bank_account", json=BANK_ACCOUNT_REQUEST)

        assert response.status_code == 500

    async def test_timeout_returns_504(self, client):
        mock_http = AsyncMock()
        mock_http.post.side_effect = httpx.TimeoutException("Timeout")
        with patch("app.routers.bank_accounts.get_http_client", return_value=mock_http):
            response = await client.post("/users/me/bank_account", json=BANK_ACCOUNT_REQUEST)

        assert response.status_code == 504

    async def test_no_token_returns_401(self, client_no_auth):
        response = await client_no_auth.post("/users/me/bank_account", json=BANK_ACCOUNT_REQUEST)
        assert response.status_code == 401


# ──────────────────────────────────────────────────────────────
# GET /users/me/bank_accounts  — получить все банковские счета
# ──────────────────────────────────────────────────────────────
class TestGetBankAccounts:
    async def test_success_returns_list(self, client):
        mock_http = AsyncMock()
        mock_resp = make_mock_http_response(200, json_data=BANK_ACCOUNTS_LIST)
        mock_resp.raise_for_status = MagicMock()
        mock_http.get.return_value = mock_resp
        with patch("app.routers.bank_accounts.get_http_client", return_value=mock_http):
            response = await client.get("/users/me/bank_accounts")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        assert data[0]["bank_account_name"] == "Основная карта"

    async def test_empty_list(self, client):
        mock_http = AsyncMock()
        mock_resp = make_mock_http_response(200, json_data=[])
        mock_resp.raise_for_status = MagicMock()
        mock_http.get.return_value = mock_resp
        with patch("app.routers.bank_accounts.get_http_client", return_value=mock_http):
            response = await client.get("/users/me/bank_accounts")

        assert response.status_code == 200
        assert response.json() == []

    async def test_timeout_returns_504(self, client):
        mock_http = AsyncMock()
        mock_http.get.side_effect = httpx.TimeoutException("Timeout")
        with patch("app.routers.bank_accounts.get_http_client", return_value=mock_http):
            response = await client.get("/users/me/bank_accounts")

        assert response.status_code == 504

    async def test_no_token_returns_401(self, client_no_auth):
        response = await client_no_auth.get("/users/me/bank_accounts")
        assert response.status_code == 401


# ──────────────────────────────────────────────────────────────
# DELETE /users/me/bank_account/{id}  — удалить банковский счёт
# ──────────────────────────────────────────────────────────────
class TestDeleteBankAccount:
    async def test_success_returns_204(self, client):
        mock_http = AsyncMock()
        mock_resp = make_mock_http_response(204)
        mock_resp.raise_for_status = MagicMock()
        mock_http.delete.return_value = mock_resp
        with patch("app.routers.bank_accounts.get_http_client", return_value=mock_http):
            response = await client.delete("/users/me/bank_account/1")

        assert response.status_code == 204

    async def test_not_found_returns_404(self, client):
        mock_http = AsyncMock()
        mock_http.delete.return_value = make_mock_http_response(404, json_data={"detail": "Not found"})
        with patch("app.routers.bank_accounts.get_http_client", return_value=mock_http):
            response = await client.delete("/users/me/bank_account/999")

        assert response.status_code == 404
        assert "не найден" in response.json()["detail"]

    async def test_timeout_returns_504(self, client):
        mock_http = AsyncMock()
        mock_http.delete.side_effect = httpx.TimeoutException("Timeout")
        with patch("app.routers.bank_accounts.get_http_client", return_value=mock_http):
            response = await client.delete("/users/me/bank_account/1")

        assert response.status_code == 504

    async def test_no_token_returns_401(self, client_no_auth):
        response = await client_no_auth.delete("/users/me/bank_account/1")
        assert response.status_code == 401
