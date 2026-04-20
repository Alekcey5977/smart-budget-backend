"""
Интеграционные тесты для эндпоинтов /purposes/*.

Downstream purposes-service мокается через patch("app.routers.purposes.get_http_client").
"""

from unittest.mock import AsyncMock, patch

import httpx as httpx_module

from tests.conftest import USER_ID, make_mock_http_response

PURPOSE_ID = "550e8400-e29b-41d4-a716-446655440000"

VALID_PURPOSE_BODY = {
    "title": "Test Goal",
    "deadline": "2027-01-01T00:00:00",
    "total_amount": 10000,
}

MOCK_PURPOSE_RESPONSE = {
    "id": PURPOSE_ID,
    "user_id": 1,
    "title": "Test Goal",
    "deadline": "2027-01-01T00:00:00",
    "amount": 0,
    "total_amount": 10000,
    "created_at": "2026-01-15T10:30:00",
    "updated_at": None,
}


# ──────────────────────────────────────────────────────────────
# POST /purposes/create
# ──────────────────────────────────────────────────────────────
class TestCreatePurpose:
    async def test_create_success(self, client):
        mock_http = AsyncMock()
        mock_http.post.return_value = make_mock_http_response(200, json_data=MOCK_PURPOSE_RESPONSE)
        with patch("app.routers.purposes.get_http_client", return_value=mock_http):
            response = await client.post("/purposes/create", json=VALID_PURPOSE_BODY)

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == PURPOSE_ID
        assert data["title"] == "Test Goal"

    async def test_create_passes_user_id_header(self, client):
        mock_http = AsyncMock()
        mock_http.post.return_value = make_mock_http_response(200, json_data=MOCK_PURPOSE_RESPONSE)
        with patch("app.routers.purposes.get_http_client", return_value=mock_http):
            await client.post("/purposes/create", json=VALID_PURPOSE_BODY)

        call_kwargs = mock_http.post.call_args.kwargs
        assert call_kwargs["headers"]["X-User-ID"] == str(USER_ID)

    async def test_create_service_unavailable(self, client):
        mock_http = AsyncMock()
        mock_http.post.side_effect = httpx_module.ConnectError("Connection refused")
        with patch("app.routers.purposes.get_http_client", return_value=mock_http):
            response = await client.post("/purposes/create", json=VALID_PURPOSE_BODY)

        assert response.status_code == 503

    async def test_create_service_timeout(self, client):
        mock_http = AsyncMock()
        mock_http.post.side_effect = httpx_module.TimeoutException("Timeout")
        with patch("app.routers.purposes.get_http_client", return_value=mock_http):
            response = await client.post("/purposes/create", json=VALID_PURPOSE_BODY)

        assert response.status_code == 504

    async def test_create_requires_auth(self, client_no_auth):
        response = await client_no_auth.post("/purposes/create", json=VALID_PURPOSE_BODY)
        assert response.status_code == 401


# ──────────────────────────────────────────────────────────────
# GET /purposes/my
# ──────────────────────────────────────────────────────────────
class TestGetMyPurposes:
    async def test_get_purposes_success(self, client):
        upstream_list = [MOCK_PURPOSE_RESPONSE]
        mock_http = AsyncMock()
        mock_http.get.return_value = make_mock_http_response(200, json_data=upstream_list)
        with patch("app.routers.purposes.get_http_client", return_value=mock_http):
            response = await client.get("/purposes/my")

        assert response.status_code == 200
        assert isinstance(response.json(), list)
        assert len(response.json()) == 1

    async def test_get_purposes_requires_auth(self, client_no_auth):
        response = await client_no_auth.get("/purposes/my")
        assert response.status_code == 401


# ──────────────────────────────────────────────────────────────
# PUT /purposes/update/{id}
# ──────────────────────────────────────────────────────────────
class TestUpdatePurpose:
    async def test_update_success(self, client):
        updated = {**MOCK_PURPOSE_RESPONSE, "title": "Updated Goal"}
        mock_http = AsyncMock()
        mock_http.put.return_value = make_mock_http_response(200, json_data=updated)
        with patch("app.routers.purposes.get_http_client", return_value=mock_http):
            response = await client.put(f"/purposes/update/{PURPOSE_ID}", json={"title": "Updated Goal"})

        assert response.status_code == 200
        assert response.json()["title"] == "Updated Goal"

    async def test_update_not_found(self, client):
        mock_http = AsyncMock()
        mock_http.put.return_value = make_mock_http_response(404, json_data={"detail": "Purpose not found"})
        with patch("app.routers.purposes.get_http_client", return_value=mock_http):
            response = await client.put(f"/purposes/update/{PURPOSE_ID}", json={"title": "Updated Goal"})

        assert response.status_code == 404


# ──────────────────────────────────────────────────────────────
# DELETE /purposes/delete/{id}
# ──────────────────────────────────────────────────────────────
class TestDeletePurpose:
    async def test_delete_success(self, client):
        mock_http = AsyncMock()
        mock_http.delete.return_value = make_mock_http_response(200, json_data={"status": "deleted"})
        with patch("app.routers.purposes.get_http_client", return_value=mock_http):
            response = await client.delete(f"/purposes/delete/{PURPOSE_ID}")

        assert response.status_code == 200

    async def test_delete_not_found(self, client):
        mock_http = AsyncMock()
        mock_http.delete.return_value = make_mock_http_response(404, json_data={"detail": "Purpose not found"})
        with patch("app.routers.purposes.get_http_client", return_value=mock_http):
            response = await client.delete(f"/purposes/delete/{PURPOSE_ID}")

        assert response.status_code == 404

    async def test_delete_requires_auth(self, client_no_auth):
        response = await client_no_auth.delete(f"/purposes/delete/{PURPOSE_ID}")
        assert response.status_code == 401
