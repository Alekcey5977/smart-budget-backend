"""
Интеграционные тесты для эндпоинтов /transactions/*.

Downstream (transactions-service) мокается через patch("app.routers.transactions.get_http_client").
"""

from unittest.mock import AsyncMock, patch

import httpx as httpx_module

from tests.conftest import make_mock_http_response

TRANSACTION_LIST = [
    {
        "id": "550e8400-e29b-41d4-a716-446655440000",
        "user_id": 1,
        "bank_account_id": 1,
        "category_id": 5,
        "category_name": "Продукты",
        "amount": 1500.50,
        "created_at": "2024-01-15T14:30:00",
        "type": "expense",
        "description": "Покупка в супермаркете",
        "merchant_id": 10,
        "merchant_name": "Пятёрочка",
    }
]

CATEGORY_LIST = [
    {"id": 1, "name": "Продукты"},
    {"id": 2, "name": "Транспорт"},
    {"id": 3, "name": "Развлечения"},
]


# ──────────────────────────────────────────────────────────────
# POST /transactions/  — получить транзакции с фильтрацией
# ──────────────────────────────────────────────────────────────
class TestGetTransactions:
    async def test_success_returns_list(self, client):
        mock_http = AsyncMock()
        mock_http.post.return_value = make_mock_http_response(200, json_data=TRANSACTION_LIST)
        with patch("app.routers.transactions.get_http_client", return_value=mock_http):
            response = await client.post("/transactions/", json={"limit": 50})

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert data[0]["type"] == "expense"

    async def test_x_user_id_header_passed_to_downstream(self, client):
        mock_http = AsyncMock()
        mock_http.post.return_value = make_mock_http_response(200, json_data=TRANSACTION_LIST)
        with patch("app.routers.transactions.get_http_client", return_value=mock_http):
            await client.post("/transactions/", json={"limit": 10})

        call_kwargs = mock_http.post.call_args.kwargs
        assert call_kwargs["headers"]["X-User-ID"] == "1"

    async def test_with_filters(self, client):
        mock_http = AsyncMock()
        mock_http.post.return_value = make_mock_http_response(200, json_data=[])
        with patch("app.routers.transactions.get_http_client", return_value=mock_http):
            response = await client.post(
                "/transactions/",
                json={
                    "transaction_type": "expense",
                    "limit": 20,
                    "offset": 0,
                },
            )

        assert response.status_code == 200

    async def test_invalid_transaction_type_rejected_at_gateway(self, client):
        response = await client.post(
            "/transactions/",
            json={"transaction_type": "unknown", "limit": 10},
        )
        assert response.status_code == 422

    async def test_missing_limit_returns_422(self, client):
        response = await client.post("/transactions/", json={})
        assert response.status_code == 422

    async def test_connect_error_returns_503(self, client):
        mock_http = AsyncMock()
        mock_http.post.side_effect = httpx_module.ConnectError("Connection refused")
        with patch("app.routers.transactions.get_http_client", return_value=mock_http):
            response = await client.post("/transactions/", json={"limit": 10})

        assert response.status_code == 503

    async def test_timeout_returns_504(self, client):
        mock_http = AsyncMock()
        mock_http.post.side_effect = httpx_module.TimeoutException("Timeout")
        with patch("app.routers.transactions.get_http_client", return_value=mock_http):
            response = await client.post("/transactions/", json={"limit": 10})

        assert response.status_code == 504

    async def test_no_token_returns_401(self, client_no_auth):
        response = await client_no_auth.post("/transactions/", json={"limit": 10})
        assert response.status_code == 401


# ──────────────────────────────────────────────────────────────
# GET /transactions/categories  — получить категории
# ──────────────────────────────────────────────────────────────
class TestGetCategories:
    async def test_success_returns_list(self, client):
        mock_http = AsyncMock()
        mock_http.get.return_value = make_mock_http_response(200, json_data=CATEGORY_LIST)
        with patch("app.routers.transactions.get_http_client", return_value=mock_http):
            response = await client.get("/transactions/categories")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 3
        assert data[0]["name"] == "Продукты"

    async def test_connect_error_returns_503(self, client):
        mock_http = AsyncMock()
        mock_http.get.side_effect = httpx_module.ConnectError("Connection refused")
        with patch("app.routers.transactions.get_http_client", return_value=mock_http):
            response = await client.get("/transactions/categories")

        assert response.status_code == 503

    async def test_timeout_returns_504(self, client):
        mock_http = AsyncMock()
        mock_http.get.side_effect = httpx_module.TimeoutException("Timeout")
        with patch("app.routers.transactions.get_http_client", return_value=mock_http):
            response = await client.get("/transactions/categories")

        assert response.status_code == 504

    async def test_no_token_returns_401(self, client_no_auth):
        response = await client_no_auth.get("/transactions/categories")
        assert response.status_code == 401
