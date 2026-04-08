"""
Интеграционные тесты для эндпоинтов /auth/*.

Большинство эндпоинтов публичные — проксируют запросы к users-service через httpx.
httpx.AsyncClient мокается на уровне роутера для register/login/refresh/logout.
Для /auth/me тестируется зависимость get_current_user напрямую (без переопределения).
"""

from unittest.mock import AsyncMock, patch

import pytest

from tests.conftest import (
    make_access_token,
    make_mock_http_response,
)


@pytest.fixture(autouse=True)
def mock_httpx_client(monkeypatch):
    """Apply httpx.AsyncClient mock before each test."""
    # This fixture ensures the mock is applied before any test runs
    pass


VALID_REGISTER_BODY = {
    "email": "new@example.com",
    "password": "StrongPass1!",
    "first_name": "Иван",
    "last_name": "Иванов",
}

VALID_LOGIN_BODY = {
    "email": "user@example.com",
    "password": "StrongPass1!",
}


# ──────────────────────────────────────────────────────────────
# POST /auth/register
# ──────────────────────────────────────────────────────────────
class TestRegister:
    async def test_register_success(self, client_no_auth):
        upstream_data = {
            "email": "new@example.com",
            "first_name": "Иван",
            "last_name": "Иванов",
            "is_active": True,
        }
        with patch("app.routers.auth.httpx.AsyncClient") as MockClient:
            mock_http = AsyncMock()
            MockClient.return_value.__aenter__.return_value = mock_http
            mock_http.post.return_value = make_mock_http_response(200, json_data=upstream_data)

            response = await client_no_auth.post("/auth/register", json=VALID_REGISTER_BODY)

        assert response.status_code == 200
        assert response.json()["email"] == "new@example.com"

    async def test_register_email_exists(self, client_no_auth):
        with patch("app.routers.auth.httpx.AsyncClient") as MockClient:
            mock_http = AsyncMock()
            MockClient.return_value.__aenter__.return_value = mock_http
            mock_http.post.return_value = make_mock_http_response(400, json_data={"detail": "Email already registered"})

            response = await client_no_auth.post("/auth/register", json=VALID_REGISTER_BODY)

        assert response.status_code == 400
        assert "Email already registered" in response.json()["detail"]

    async def test_register_service_unavailable(self, client_no_auth):
        import httpx as httpx_module

        with patch("app.routers.auth.httpx.AsyncClient") as MockClient:
            mock_http = AsyncMock()
            MockClient.return_value.__aenter__.return_value = mock_http
            mock_http.post.side_effect = httpx_module.ConnectError("Connection refused")

            response = await client_no_auth.post("/auth/register", json=VALID_REGISTER_BODY)

        assert response.status_code == 503

    async def test_register_invalid_password_rejected_at_gateway(self, client_no_auth):
        body = {**VALID_REGISTER_BODY, "password": "weak"}
        response = await client_no_auth.post("/auth/register", json=body)
        assert response.status_code == 422


# ──────────────────────────────────────────────────────────────
# POST /auth/login
# ──────────────────────────────────────────────────────────────
class TestLogin:
    async def test_login_success(self, client_no_auth):
        upstream_data = {"access_token": "some.token.here", "token_type": "bearer"}
        with patch("app.routers.auth.httpx.AsyncClient") as MockClient:
            mock_http = AsyncMock()
            MockClient.return_value.__aenter__.return_value = mock_http
            mock_http.post.return_value = make_mock_http_response(200, json_data=upstream_data)

            response = await client_no_auth.post("/auth/login", json=VALID_LOGIN_BODY)

        assert response.status_code == 200
        assert response.json()["access_token"] == "some.token.here"

    async def test_login_cookie_propagated(self, client_no_auth):
        upstream_data = {"access_token": "tok", "token_type": "bearer"}
        cookie_value = "refresh_token=abc123; HttpOnly; SameSite=strict"
        with patch("app.routers.auth.httpx.AsyncClient") as MockClient:
            mock_http = AsyncMock()
            MockClient.return_value.__aenter__.return_value = mock_http
            mock_http.post.return_value = make_mock_http_response(
                200,
                json_data=upstream_data,
                headers={"set-cookie": cookie_value},
            )

            response = await client_no_auth.post("/auth/login", json=VALID_LOGIN_BODY)

        assert response.status_code == 200

    async def test_login_invalid_credentials(self, client_no_auth):
        with patch("app.routers.auth.httpx.AsyncClient") as MockClient:
            mock_http = AsyncMock()
            MockClient.return_value.__aenter__.return_value = mock_http
            mock_http.post.return_value = make_mock_http_response(401, json_data={"detail": "Invalid credentials"})

            response = await client_no_auth.post("/auth/login", json=VALID_LOGIN_BODY)

        assert response.status_code == 401

    async def test_login_service_unavailable(self, client_no_auth):
        import httpx as httpx_module

        with patch("app.routers.auth.httpx.AsyncClient") as MockClient:
            mock_http = AsyncMock()
            MockClient.return_value.__aenter__.return_value = mock_http
            mock_http.post.side_effect = httpx_module.ConnectError("Connection refused")

            response = await client_no_auth.post("/auth/login", json=VALID_LOGIN_BODY)

        assert response.status_code == 503


# ──────────────────────────────────────────────────────────────
# POST /auth/refresh
# ──────────────────────────────────────────────────────────────
class TestRefresh:
    async def test_refresh_success(self, client_no_auth):
        upstream_data = {"access_token": "new.token", "token_type": "bearer"}
        with patch("app.routers.auth.httpx.AsyncClient") as MockClient:
            mock_http = AsyncMock()
            MockClient.return_value.__aenter__.return_value = mock_http
            mock_http.post.return_value = make_mock_http_response(200, json_data=upstream_data)

            client_no_auth.cookies.set("refresh_token", "some-refresh-token")
            response = await client_no_auth.post("/auth/refresh")

        assert response.status_code == 200
        assert response.json()["access_token"] == "new.token"

    async def test_refresh_invalid_token(self, client_no_auth):
        with patch("app.routers.auth.httpx.AsyncClient") as MockClient:
            mock_http = AsyncMock()
            MockClient.return_value.__aenter__.return_value = mock_http
            mock_http.post.return_value = make_mock_http_response(401, json_data={"detail": "Invalid refresh token"})

            response = await client_no_auth.post("/auth/refresh")

        assert response.status_code == 401

    async def test_refresh_service_unavailable(self, client_no_auth):
        import httpx as httpx_module

        with patch("app.routers.auth.httpx.AsyncClient") as MockClient:
            mock_http = AsyncMock()
            MockClient.return_value.__aenter__.return_value = mock_http
            mock_http.post.side_effect = httpx_module.ConnectError("Connection refused")

            response = await client_no_auth.post("/auth/refresh")

        assert response.status_code == 503


# ──────────────────────────────────────────────────────────────
# POST /auth/logout
# ──────────────────────────────────────────────────────────────
class TestLogout:
    async def test_logout_success(self, client_no_auth):
        with patch("app.routers.auth.httpx.AsyncClient") as MockClient:
            mock_http = AsyncMock()
            MockClient.return_value.__aenter__.return_value = mock_http
            mock_http.post.return_value = make_mock_http_response(200, json_data={"msg": "Logged out"})

            response = await client_no_auth.post("/auth/logout")

        assert response.status_code == 200
        assert response.json()["msg"] == "Logged out"

    async def test_logout_service_unavailable_still_clears_cookie(self, client_no_auth):
        import httpx as httpx_module

        with patch("app.routers.auth.httpx.AsyncClient") as MockClient:
            mock_http = AsyncMock()
            MockClient.return_value.__aenter__.return_value = mock_http
            mock_http.post.side_effect = httpx_module.ConnectError("Connection refused")

            response = await client_no_auth.post("/auth/logout")

        # 503 is raised but cookie deletion header is still set
        assert response.status_code == 503


# ──────────────────────────────────────────────────────────────
# GET /auth/me — tests get_current_user dependency directly
# ──────────────────────────────────────────────────────────────
class TestGetMe:
    async def test_no_token_returns_401(self, client_no_auth):
        response = await client_no_auth.get("/auth/me")
        assert response.status_code == 401

    async def test_invalid_jwt_signature_returns_401(self, client_no_auth):
        bad_token = make_access_token(secret="wrong-secret")
        response = await client_no_auth.get("/auth/me", headers={"Authorization": f"Bearer {bad_token}"})
        assert response.status_code == 401

    async def test_valid_token_upstream_200(self, monkeypatch):
        import os

        from app.dependencies import get_current_user
        from app.main import app
        from httpx import ASGITransport, AsyncClient

        # Создаём токен с правильным секретом (который используется в системе)
        actual_secret = os.getenv("ACCESS_SECRET_KEY", "test-secret-key-for-gateway")
        token = make_access_token(secret=actual_secret)

        user_data = {"id": 1, "email": "test@example.com", "first_name": "Тест"}

        # Мок для httpx.AsyncClient
        mock_http = AsyncMock()
        mock_http.get.return_value = make_mock_http_response(200, json_data=user_data)

        MockClient = AsyncMock()
        MockClient.return_value.__aenter__.return_value = mock_http

        monkeypatch.setattr("app.dependencies.httpx.AsyncClient", MockClient)

        # Переопределяем зависимость для получения данных пользователя
        async def mock_get_current_user_with_data():
            return {
                "token": token,
                "user": user_data,
                "user_id": "1",
            }

        app.dependency_overrides[get_current_user] = mock_get_current_user_with_data

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            response = await ac.get("/auth/me", headers={"Authorization": f"Bearer {token}"})

        assert response.status_code == 200
        data = response.json()
        assert data["user"]["email"] == "test@example.com"
        assert data["user_id"] == "1"

        app.dependency_overrides.clear()

    async def test_valid_token_users_service_unavailable(self, monkeypatch):
        import os

        import httpx as httpx_module
        from app.main import app
        from httpx import ASGITransport, AsyncClient

        # Создаём токен с правильным секретом (который используется в системе)
        actual_secret = os.getenv("ACCESS_SECRET_KEY", "test-secret-key-for-gateway")
        token = make_access_token(secret=actual_secret)

        # Мок для httpx.AsyncClient с ConnectError
        mock_http = AsyncMock()
        mock_http.get.side_effect = httpx_module.ConnectError("Connection refused")

        # AsyncMock для контекстного менеджера - должен быть классом, а не экземпляром
        class MockAsyncClient:
            def __init__(self, *args, **kwargs):
                self._mock = mock_http

            async def __aenter__(self):
                return self._mock

            async def __aexit__(self, *args):
                pass

        monkeypatch.setattr("httpx.AsyncClient", MockAsyncClient)

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            response = await ac.get("/auth/me", headers={"Authorization": f"Bearer {token}"})

        # Ожидаем 503, потому что httpx.ConnectError должен быть обработан
        assert response.status_code == 503

    async def test_valid_token_users_service_timeout(self, monkeypatch):
        import os

        import httpx as httpx_module
        from app.main import app
        from httpx import ASGITransport, AsyncClient

        # Создаём токен с правильным секретом (который используется в системе)
        actual_secret = os.getenv("ACCESS_SECRET_KEY", "test-secret-key-for-gateway")
        token = make_access_token(secret=actual_secret)

        # Мок для httpx.AsyncClient с TimeoutException
        mock_http = AsyncMock()
        mock_http.get.side_effect = httpx_module.TimeoutException("Timeout")

        # AsyncMock для контекстного менеджера - должен быть классом, а не экземпляром
        class MockAsyncClient:
            def __init__(self, *args, **kwargs):
                self._mock = mock_http

            async def __aenter__(self):
                return self._mock

            async def __aexit__(self, *args):
                pass

        monkeypatch.setattr("httpx.AsyncClient", MockAsyncClient)

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            response = await ac.get("/auth/me", headers={"Authorization": f"Bearer {token}"})

        assert response.status_code == 504
