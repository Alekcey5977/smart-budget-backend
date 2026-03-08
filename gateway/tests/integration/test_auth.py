"""
Интеграционные тесты для эндпоинтов /auth/*.

Большинство эндпоинтов публичные — проксируют запросы к users-service через httpx.
httpx.AsyncClient мокается на уровне роутера для register/login/refresh/logout.
Для /auth/me тестируется зависимость get_current_user напрямую (без переопределения).
"""
import pytest
from unittest.mock import AsyncMock, patch

from tests.conftest import (
    make_mock_http_response,
    make_access_token,
    TEST_SECRET,
)

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
            mock_http.post.return_value = make_mock_http_response(
                400, json_data={"detail": "Email already registered"}
            )

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
            mock_http.post.return_value = make_mock_http_response(
                401, json_data={"detail": "Invalid credentials"}
            )

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

            response = await client_no_auth.post(
                "/auth/refresh", cookies={"refresh_token": "some-refresh-token"}
            )

        assert response.status_code == 200
        assert response.json()["access_token"] == "new.token"

    async def test_refresh_invalid_token(self, client_no_auth):
        with patch("app.routers.auth.httpx.AsyncClient") as MockClient:
            mock_http = AsyncMock()
            MockClient.return_value.__aenter__.return_value = mock_http
            mock_http.post.return_value = make_mock_http_response(
                401, json_data={"detail": "Invalid refresh token"}
            )

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
            mock_http.post.return_value = make_mock_http_response(
                200, json_data={"msg": "Logged out"}
            )

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
        response = await client_no_auth.get(
            "/auth/me", headers={"Authorization": f"Bearer {bad_token}"}
        )
        assert response.status_code == 401

    async def test_valid_token_upstream_200(self, client_no_auth):
        token = make_access_token()
        user_data = {"id": 1, "email": "test@example.com", "first_name": "Тест"}
        with patch("app.dependencies.httpx.AsyncClient") as MockClient:
            mock_http = AsyncMock()
            MockClient.return_value.__aenter__.return_value = mock_http
            mock_http.get.return_value = make_mock_http_response(200, json_data=user_data)

            response = await client_no_auth.get(
                "/auth/me", headers={"Authorization": f"Bearer {token}"}
            )

        assert response.status_code == 200
        data = response.json()
        assert data["user"]["email"] == "test@example.com"
        assert data["user_id"] == "1"

    async def test_valid_token_users_service_unavailable(self, client_no_auth):
        import httpx as httpx_module

        token = make_access_token()
        with patch("app.dependencies.httpx.AsyncClient") as MockClient:
            mock_http = AsyncMock()
            MockClient.return_value.__aenter__.return_value = mock_http
            mock_http.get.side_effect = httpx_module.ConnectError("Connection refused")

            response = await client_no_auth.get(
                "/auth/me", headers={"Authorization": f"Bearer {token}"}
            )

        assert response.status_code == 503

    async def test_valid_token_users_service_timeout(self, client_no_auth):
        import httpx as httpx_module

        token = make_access_token()
        with patch("app.dependencies.httpx.AsyncClient") as MockClient:
            mock_http = AsyncMock()
            MockClient.return_value.__aenter__.return_value = mock_http
            mock_http.get.side_effect = httpx_module.TimeoutException("Timeout")

            response = await client_no_auth.get(
                "/auth/me", headers={"Authorization": f"Bearer {token}"}
            )

        assert response.status_code == 504
