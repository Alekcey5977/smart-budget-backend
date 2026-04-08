"""
E2E tests for /images/* endpoints.
Публичные эндпоинты не требуют авторизации.
Для тестов аватара нужно сначала запустить: make load-test-images
"""

import pytest


class TestPublicEndpoints:
    def test_get_default_avatars_returns_list(self, http_client):
        resp = http_client.get("/images/avatars/default")
        assert resp.status_code == 200
        avatars = resp.json()
        assert isinstance(avatars, list)

    def test_get_categories_mapping(self, http_client):
        resp = http_client.get("/images/mappings/categories")
        assert resp.status_code == 200
        assert isinstance(resp.json(), (dict, list))

    def test_get_merchants_mapping(self, http_client):
        resp = http_client.get("/images/mappings/merchants")
        assert resp.status_code == 200
        assert isinstance(resp.json(), (dict, list))

    def test_get_image_by_valid_id(self, http_client):
        """Получаем image_id из списка аватаров, затем запрашиваем его."""
        avatars_resp = http_client.get("/images/avatars/default")
        assert avatars_resp.status_code == 200
        avatars = avatars_resp.json()

        if not avatars:
            pytest.skip("No avatars loaded — run: make load-test-images")

        # Берём первый avatar и его image_id
        avatar = avatars[0]
        image_id = avatar.get("image_id") or avatar.get("id")

        resp = http_client.get(f"/images/{image_id}")
        assert resp.status_code == 200
        assert len(resp.content) > 0
        assert resp.headers.get("content-type", "").startswith("image/")

    def test_get_image_by_invalid_id_returns_404(self, http_client):
        # Endpoint expects a UUID — use a valid UUID format that doesn't exist
        resp = http_client.get("/images/00000000-0000-0000-0000-000000000000")
        assert resp.status_code == 404


class TestUserAvatar:
    def test_get_my_avatar_without_token_returns_401(self, http_client):
        resp = http_client.get("/images/avatars/me")
        assert resp.status_code == 401

    def test_get_my_avatar_for_new_user(self, http_client, auth_headers):
        _, headers = auth_headers
        resp = http_client.get("/images/avatars/me", headers=headers)
        # Новый пользователь может не иметь аватара — 404 допустим
        assert resp.status_code in (200, 404)

    def test_update_avatar_with_valid_image_id(self, http_client, auth_headers):
        _, headers = auth_headers

        avatars_resp = http_client.get("/images/avatars/default")
        if avatars_resp.status_code != 200 or not avatars_resp.json():
            pytest.skip("No default avatars loaded — run: make load-test-images")

        avatar = avatars_resp.json()[0]
        image_id = avatar.get("image_id") or avatar.get("id")

        resp = http_client.put(
            "/images/avatars/me",
            json={"image_id": image_id},
            headers=headers,
        )
        assert resp.status_code == 200

    def test_update_avatar_without_token_returns_401(self, http_client):
        resp = http_client.put(
            "/images/avatars/me",
            json={"image_id": "some-id"},
        )
        assert resp.status_code == 401
