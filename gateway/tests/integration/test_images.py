"""
Интеграционные тесты для эндпоинтов /images/*.

Публичные эндпоинты (без авторизации): avatars/default, images/{id}, mappings/*
Защищённые эндпоинты: avatars/me (GET и PUT)

Downstream images-service мокается через patch("app.routers.images.httpx.AsyncClient").
"""
from unittest.mock import AsyncMock, patch

from tests.conftest import USER_ID, make_mock_http_response

IMAGE_ID = "550e8400-e29b-41d4-a716-446655440000"

MOCK_AVATAR_METADATA = {
    "id": IMAGE_ID,
    "entity_type": "user_avatar",
    "entity_id": None,
    "mime_type": "image/jpeg",
    "file_size": 12345,
    "is_default": True,
    "created_at": "2026-01-15T10:30:00",
    "updated_at": None,
}


# ──────────────────────────────────────────────────────────────
# GET /images/avatars/default  (public)
# ──────────────────────────────────────────────────────────────
class TestGetDefaultAvatars:
    async def test_get_default_avatars_success(self, client_no_auth):
        with patch("app.routers.images.httpx.AsyncClient") as MockClient:
            mock_http = AsyncMock()
            MockClient.return_value.__aenter__.return_value = mock_http
            mock_http.get.return_value = make_mock_http_response(
                200, json_data=[MOCK_AVATAR_METADATA]
            )

            response = await client_no_auth.get("/images/avatars/default")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert data[0]["is_default"] is True

    async def test_get_default_avatars_service_unavailable(self, client_no_auth):
        import httpx as httpx_module

        with patch("app.routers.images.httpx.AsyncClient") as MockClient:
            mock_http = AsyncMock()
            MockClient.return_value.__aenter__.return_value = mock_http
            mock_http.get.side_effect = httpx_module.ConnectError("Connection refused")

            response = await client_no_auth.get("/images/avatars/default")

        assert response.status_code == 503

    async def test_get_default_avatars_no_auth_required(self, client_no_auth):
        with patch("app.routers.images.httpx.AsyncClient") as MockClient:
            mock_http = AsyncMock()
            MockClient.return_value.__aenter__.return_value = mock_http
            mock_http.get.return_value = make_mock_http_response(200, json_data=[])

            response = await client_no_auth.get("/images/avatars/default")

        assert response.status_code == 200


# ──────────────────────────────────────────────────────────────
# GET /images/avatars/me  (auth)
# ──────────────────────────────────────────────────────────────
class TestGetMyAvatar:
    async def test_get_my_avatar_success(self, client):
        user_avatar = {**MOCK_AVATAR_METADATA, "entity_id": "1", "is_default": False}
        with patch("app.routers.images.httpx.AsyncClient") as MockClient:
            mock_http = AsyncMock()
            MockClient.return_value.__aenter__.return_value = mock_http
            mock_http.get.return_value = make_mock_http_response(200, json_data=user_avatar)

            response = await client.get("/images/avatars/me")

        assert response.status_code == 200
        assert response.json()["entity_id"] == "1"

    async def test_get_my_avatar_passes_user_id(self, client):
        user_avatar = {**MOCK_AVATAR_METADATA, "entity_id": "1", "is_default": False}
        with patch("app.routers.images.httpx.AsyncClient") as MockClient:
            mock_http = AsyncMock()
            MockClient.return_value.__aenter__.return_value = mock_http
            mock_http.get.return_value = make_mock_http_response(200, json_data=user_avatar)

            await client.get("/images/avatars/me")

        call_kwargs = mock_http.get.call_args.kwargs
        assert call_kwargs["headers"]["X-User-ID"] == str(USER_ID)

    async def test_get_my_avatar_not_found(self, client):
        with patch("app.routers.images.httpx.AsyncClient") as MockClient:
            mock_http = AsyncMock()
            MockClient.return_value.__aenter__.return_value = mock_http
            mock_http.get.return_value = make_mock_http_response(
                404, json_data={"detail": "Avatar not found"}
            )

            response = await client.get("/images/avatars/me")

        assert response.status_code == 404

    async def test_get_my_avatar_requires_auth(self, client_no_auth):
        response = await client_no_auth.get("/images/avatars/me")
        assert response.status_code == 401


# ──────────────────────────────────────────────────────────────
# PUT /images/avatars/me  (auth)
# ──────────────────────────────────────────────────────────────
class TestUpdateMyAvatar:
    async def test_update_avatar_success(self, client):
        updated_avatar = {**MOCK_AVATAR_METADATA, "entity_id": "1", "is_default": False}
        with patch("app.routers.images.httpx.AsyncClient") as MockClient:
            mock_http = AsyncMock()
            MockClient.return_value.__aenter__.return_value = mock_http
            mock_http.put.return_value = make_mock_http_response(200, json_data=updated_avatar)

            response = await client.put(
                "/images/avatars/me", json={"image_id": IMAGE_ID}
            )

        assert response.status_code == 200

    async def test_update_avatar_requires_auth(self, client_no_auth):
        response = await client_no_auth.put(
            "/images/avatars/me", json={"image_id": IMAGE_ID}
        )
        assert response.status_code == 401

    async def test_update_avatar_upstream_error(self, client):
        with patch("app.routers.images.httpx.AsyncClient") as MockClient:
            mock_http = AsyncMock()
            MockClient.return_value.__aenter__.return_value = mock_http
            mock_http.put.return_value = make_mock_http_response(
                400, json_data={"detail": "Invalid avatar ID"}
            )

            response = await client.put(
                "/images/avatars/me", json={"image_id": IMAGE_ID}
            )

        assert response.status_code == 400


# ──────────────────────────────────────────────────────────────
# GET /images/{id}  (public, binary)
# ──────────────────────────────────────────────────────────────
class TestGetImageBinary:
    async def test_get_image_success(self, client_no_auth):
        image_bytes = b"\xff\xd8\xff"  # Fake JPEG header
        with patch("app.routers.images.httpx.AsyncClient") as MockClient:
            mock_http = AsyncMock()
            MockClient.return_value.__aenter__.return_value = mock_http
            mock_http.get.return_value = make_mock_http_response(
                200,
                content=image_bytes,
                headers={
                    "content-type": "image/jpeg",
                    "cache-control": "public, max-age=31536000",
                    "content-length": str(len(image_bytes)),
                },
            )

            response = await client_no_auth.get(f"/images/{IMAGE_ID}")

        assert response.status_code == 200
        assert response.content == image_bytes
        assert "image/jpeg" in response.headers.get("content-type", "")

    async def test_get_image_not_found(self, client_no_auth):
        with patch("app.routers.images.httpx.AsyncClient") as MockClient:
            mock_http = AsyncMock()
            MockClient.return_value.__aenter__.return_value = mock_http
            mock_http.get.return_value = make_mock_http_response(
                404, json_data={"detail": "Image not found"}
            )

            response = await client_no_auth.get(f"/images/{IMAGE_ID}")

        assert response.status_code == 404

    async def test_get_image_no_auth_required(self, client_no_auth):
        image_bytes = b"\x89PNG"
        with patch("app.routers.images.httpx.AsyncClient") as MockClient:
            mock_http = AsyncMock()
            MockClient.return_value.__aenter__.return_value = mock_http
            mock_http.get.return_value = make_mock_http_response(
                200,
                content=image_bytes,
                headers={"content-type": "image/png", "content-length": str(len(image_bytes))},
            )

            response = await client_no_auth.get(f"/images/{IMAGE_ID}")

        assert response.status_code == 200


# ──────────────────────────────────────────────────────────────
# GET /images/mappings/categories  (public)
# ──────────────────────────────────────────────────────────────
class TestGetCategoriesMapping:
    async def test_get_categories_mapping_success(self, client_no_auth):
        upstream_data = {
            "entity_type": "category",
            "mappings": [
                {"entity_id": "cat-1", "image_id": IMAGE_ID, "mime_type": "image/jpeg"}
            ],
        }
        with patch("app.routers.images.httpx.AsyncClient") as MockClient:
            mock_http = AsyncMock()
            MockClient.return_value.__aenter__.return_value = mock_http
            mock_http.get.return_value = make_mock_http_response(200, json_data=upstream_data)

            response = await client_no_auth.get("/images/mappings/categories")

        assert response.status_code == 200
        assert response.json()["entity_type"] == "category"

    async def test_get_categories_mapping_no_auth_required(self, client_no_auth):
        with patch("app.routers.images.httpx.AsyncClient") as MockClient:
            mock_http = AsyncMock()
            MockClient.return_value.__aenter__.return_value = mock_http
            mock_http.get.return_value = make_mock_http_response(
                200, json_data={"entity_type": "category", "mappings": []}
            )

            response = await client_no_auth.get("/images/mappings/categories")

        assert response.status_code == 200


# ──────────────────────────────────────────────────────────────
# GET /images/mappings/merchants  (public)
# ──────────────────────────────────────────────────────────────
class TestGetMerchantsMapping:
    async def test_get_merchants_mapping_success(self, client_no_auth):
        upstream_data = {
            "entity_type": "merchant",
            "mappings": [
                {"entity_id": "merch-1", "image_id": IMAGE_ID, "mime_type": "image/jpeg"}
            ],
        }
        with patch("app.routers.images.httpx.AsyncClient") as MockClient:
            mock_http = AsyncMock()
            MockClient.return_value.__aenter__.return_value = mock_http
            mock_http.get.return_value = make_mock_http_response(200, json_data=upstream_data)

            response = await client_no_auth.get("/images/mappings/merchants")

        assert response.status_code == 200
        assert response.json()["entity_type"] == "merchant"

    async def test_get_merchants_mapping_service_unavailable(self, client_no_auth):
        import httpx as httpx_module

        with patch("app.routers.images.httpx.AsyncClient") as MockClient:
            mock_http = AsyncMock()
            MockClient.return_value.__aenter__.return_value = mock_http
            mock_http.get.side_effect = httpx_module.ConnectError("Connection refused")

            response = await client_no_auth.get("/images/mappings/merchants")

        assert response.status_code == 503
