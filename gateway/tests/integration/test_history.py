"""
Интеграционные тесты для эндпоинтов /history/*.

Все эндпоинты требуют JWT — get_current_user переопределяется через фикстуру `client`.
Downstream history-service мокается через patch("app.routers.history.httpx.AsyncClient").
"""

from unittest.mock import AsyncMock, patch

from tests.conftest import USER_ID, make_mock_http_response

ENTRY_ID = "550e8400-e29b-41d4-a716-446655440000"

MOCK_ENTRY = {
    "id": ENTRY_ID,
    "user_id": 1,
    "title": "Цель создана",
    "body": "Цель «Отпуск» на сумму 100000 руб. создана",
    "created_at": "2026-01-21T10:30:00",
}


# ──────────────────────────────────────────────────────────────
# GET /history/user/me
# ──────────────────────────────────────────────────────────────
class TestGetUserHistory:
    async def test_get_history_success(self, client):
        with patch("app.routers.history.httpx.AsyncClient") as MockClient:
            mock_http = AsyncMock()
            MockClient.return_value.__aenter__.return_value = mock_http
            mock_http.get.return_value = make_mock_http_response(200, json_data=[MOCK_ENTRY])

            response = await client.get("/history/user/me")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert data[0]["id"] == ENTRY_ID

    async def test_get_history_passes_user_id(self, client):
        with patch("app.routers.history.httpx.AsyncClient") as MockClient:
            mock_http = AsyncMock()
            MockClient.return_value.__aenter__.return_value = mock_http
            mock_http.get.return_value = make_mock_http_response(200, json_data=[])

            await client.get("/history/user/me")

        call_kwargs = mock_http.get.call_args.kwargs
        assert call_kwargs["headers"]["X-User-ID"] == str(USER_ID)

    async def test_get_history_service_unavailable(self, client):
        import httpx as httpx_module

        with patch("app.routers.history.httpx.AsyncClient") as MockClient:
            mock_http = AsyncMock()
            MockClient.return_value.__aenter__.return_value = mock_http
            mock_http.get.side_effect = httpx_module.ConnectError("Connection refused")

            response = await client.get("/history/user/me")

        assert response.status_code == 503

    async def test_get_history_requires_auth(self, client_no_auth):
        response = await client_no_auth.get("/history/user/me")
        assert response.status_code == 401


# ──────────────────────────────────────────────────────────────
# GET /history/{entry_id}
# ──────────────────────────────────────────────────────────────
class TestGetHistoryEntry:
    async def test_get_entry_success(self, client):
        with patch("app.routers.history.httpx.AsyncClient") as MockClient:
            mock_http = AsyncMock()
            MockClient.return_value.__aenter__.return_value = mock_http
            mock_http.get.return_value = make_mock_http_response(200, json_data=MOCK_ENTRY)

            response = await client.get(f"/history/{ENTRY_ID}")

        assert response.status_code == 200
        assert response.json()["id"] == ENTRY_ID

    async def test_get_entry_not_found(self, client):
        with patch("app.routers.history.httpx.AsyncClient") as MockClient:
            mock_http = AsyncMock()
            MockClient.return_value.__aenter__.return_value = mock_http
            mock_http.get.return_value = make_mock_http_response(404, json_data={"detail": "Not found"})

            response = await client.get(f"/history/{ENTRY_ID}")

        assert response.status_code == 404

    async def test_get_entry_service_unavailable(self, client):
        import httpx as httpx_module

        with patch("app.routers.history.httpx.AsyncClient") as MockClient:
            mock_http = AsyncMock()
            MockClient.return_value.__aenter__.return_value = mock_http
            mock_http.get.side_effect = httpx_module.ConnectError("Connection refused")

            response = await client.get(f"/history/{ENTRY_ID}")

        assert response.status_code == 503

    async def test_get_entry_requires_auth(self, client_no_auth):
        response = await client_no_auth.get(f"/history/{ENTRY_ID}")
        assert response.status_code == 401


# ──────────────────────────────────────────────────────────────
# DELETE /history/{entry_id}
# ──────────────────────────────────────────────────────────────
class TestDeleteHistoryEntry:
    async def test_delete_success(self, client):
        upstream_data = {"status": "success", "message": "History entry deleted"}
        with patch("app.routers.history.httpx.AsyncClient") as MockClient:
            mock_http = AsyncMock()
            MockClient.return_value.__aenter__.return_value = mock_http
            mock_http.delete.return_value = make_mock_http_response(200, json_data=upstream_data)

            response = await client.delete(f"/history/{ENTRY_ID}")

        assert response.status_code == 200
        assert response.json()["status"] == "success"

    async def test_delete_passes_user_id(self, client):
        upstream_data = {"status": "success", "message": "History entry deleted"}
        with patch("app.routers.history.httpx.AsyncClient") as MockClient:
            mock_http = AsyncMock()
            MockClient.return_value.__aenter__.return_value = mock_http
            mock_http.delete.return_value = make_mock_http_response(200, json_data=upstream_data)

            await client.delete(f"/history/{ENTRY_ID}")

        call_kwargs = mock_http.delete.call_args.kwargs
        assert call_kwargs["headers"]["X-User-ID"] == str(USER_ID)

    async def test_delete_not_found(self, client):
        with patch("app.routers.history.httpx.AsyncClient") as MockClient:
            mock_http = AsyncMock()
            MockClient.return_value.__aenter__.return_value = mock_http
            mock_http.delete.return_value = make_mock_http_response(404, json_data={"detail": "Not found"})

            response = await client.delete(f"/history/{ENTRY_ID}")

        assert response.status_code == 404

    async def test_delete_requires_auth(self, client_no_auth):
        response = await client_no_auth.delete(f"/history/{ENTRY_ID}")
        assert response.status_code == 401
