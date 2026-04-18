from unittest.mock import MagicMock, patch

import pytest
from fastapi import status

patch_get_hash = patch("app.routers.users.get_password_hash", return_value="hashed_password")
patch_verify_password = patch("app.routers.users.verify_password", return_value=True)
patch_create_access = patch("app.routers.users.create_access_token", return_value="access_token")
patch_create_refresh = patch("app.routers.users.create_refresh_token", return_value="refresh_token")
patch_jwt_decode = patch("jose.jwt.decode", return_value={"jti": "jti_123"})


class TestRegister:
    """Тесты регистрации пользователя"""

    @pytest.mark.asyncio
    async def test_register_success(self, client, mock_user_repo):
        """Тест: успешная регистрация"""
        mock_user_repo.exists_with_email.return_value = False
        mock_user_repo.create.return_value = MagicMock(
            id=1,
            email="test@example.com",
            first_name="Ivan",
            last_name="Ivanov",
            middle_name="Ivanovich",
            is_active=True,
            created_at="2024-01-01T00:00:00",
            updated_at=None,
        )

        with patch_get_hash:
            response = await client.post(
                "/users/register",
                json={
                    "email": "test@example.com",
                    "first_name": "Ivan",
                    "last_name": "Ivanov",
                    "middle_name": "Ivanovich",
                    "password": "SecurePass123!",
                },
            )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["email"] == "test@example.com"
        mock_user_repo.exists_with_email.assert_called_once_with("test@example.com")
        mock_user_repo.create.assert_called_once()

    @pytest.mark.asyncio
    async def test_register_email_already_exists(self, client, mock_user_repo):
        """Тест: email уже зарегистрирован"""
        mock_user_repo.exists_with_email.return_value = True

        with patch_get_hash:
            response = await client.post(
                "/users/register",
                json={
                    "email": "existing@example.com",
                    "first_name": "Ivan",
                    "last_name": "Ivanov",
                    "password": "SecurePass123!",
                },
            )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "Email already registered" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_register_invalid_email(self, client):
        """Тест: невалидный email"""
        response = await client.post(
            "/users/register",
            json={"email": "invalid-email", "first_name": "Ivan", "last_name": "Ivanov", "password": "SecurePass123!"},
        )
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_register_weak_password(self, client):
        """Тест: слабый пароль"""
        response = await client.post(
            "/users/register",
            json={"email": "test@example.com", "first_name": "Ivan", "last_name": "Ivanov", "password": "short"},
        )
        assert response.status_code == 422


class TestLogin:
    """Тесты авторизации пользователя"""

    @pytest.mark.asyncio
    async def test_login_success(self, client, mock_user_repo):
        """Тест: успешный вход"""
        mock_user = MagicMock(id=1, email="test@example.com", hashed_password="$2b$12$hashed", is_active=True)
        mock_user_repo.get_by_email.return_value = mock_user

        with patch_verify_password, patch_create_access, patch_create_refresh, patch_jwt_decode:
            response = await client.post(
                "/users/login", json={"email": "test@example.com", "password": "SecurePass123!"}
            )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "access_token" in data
        assert response.cookies.get("refresh_token") is not None

    @pytest.mark.asyncio
    async def test_login_wrong_password(self, client, mock_user_repo):
        """Тест: неверный пароль"""
        mock_user = MagicMock(id=1, email="test@example.com", hashed_password="$2b$12$hashed", is_active=True)
        mock_user_repo.get_by_email.return_value = mock_user

        # Патчим проверку пароля, чтобы вернуть False
        with patch("app.routers.users.verify_password", return_value=False):
            response = await client.post(
                "/users/login", json={"email": "test@example.com", "password": "WrongPassword123!"}
            )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    @pytest.mark.asyncio
    async def test_login_user_not_found(self, client, mock_user_repo):
        """Тест: пользователь не найден"""
        mock_user_repo.get_by_email.return_value = None
        response = await client.post(
            "/users/login", json={"email": "notfound@example.com", "password": "SecurePass123!"}
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    @pytest.mark.asyncio
    async def test_login_inactive_user(self, client, mock_user_repo):
        """Тест: неактивный пользователь"""
        mock_user = MagicMock(id=1, email="test@example.com", hashed_password="$2b$12$hashed", is_active=False)
        mock_user_repo.get_by_email.return_value = mock_user

        with patch_verify_password:
            response = await client.post(
                "/users/login", json={"email": "test@example.com", "password": "SecurePass123!"}
            )

        assert response.status_code == status.HTTP_400_BAD_REQUEST


class TestRefreshToken:
    """Тесты обновления refresh токена"""

    @pytest.mark.asyncio
    async def test_refresh_token_success(self, client, mock_user_repo):
        """Тест: успешное обновление токена"""
        mock_user = MagicMock(id=1, is_active=True)
        client.cookies.set("refresh_token", "valid_refresh_token")
        mock_user_repo.get_by_id.return_value = mock_user

        with (
            patch("jose.jwt.decode", return_value={"sub": "1", "type": "refresh", "jti": "jti_123"}),
            patch("app.routers.users.create_refresh_token", return_value="new_refresh_token"),
            patch("app.routers.users.create_access_token", return_value="new_access_token"),
        ):
            response = await client.post("/users/refresh")

            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert "access_token" in data
            assert data["access_token"] == "new_access_token"
            assert "refresh_token" in response.cookies
            assert response.cookies["refresh_token"] == "new_refresh_token"

    @pytest.mark.asyncio
    async def test_refresh_token_missing(self, client):
        """Тест: отсутствует refresh токен"""
        response = await client.post("/users/refresh")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert "Refresh token missing" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_refresh_token_invalid_type(self, client):
        """Тест: неверный тип токена"""
        client.cookies.set("refresh_token", "wrong_type_token")

        with patch("jose.jwt.decode", return_value={"type": "access", "sub": "1", "jti": "jti"}):
            response = await client.post("/users/refresh")

            assert response.status_code == status.HTTP_401_UNAUTHORIZED
            assert "Invalid token type" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_refresh_token_expired(self, client):
        """Тест: истёкший refresh токен"""
        from jose import jwt

        client.cookies.set("refresh_token", "expired_token")

        with patch("jose.jwt.decode", side_effect=jwt.ExpiredSignatureError()):
            response = await client.post("/users/refresh")

            assert response.status_code == status.HTTP_401_UNAUTHORIZED
            assert "Refresh token expired" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_refresh_token_user_not_found(self, client, mock_user_repo):
        """Тест: пользователь не найден при обновлении"""
        client.cookies.set("refresh_token", "valid_token")
        mock_user_repo.get_by_id.return_value = None

        with patch("jose.jwt.decode", return_value={"sub": "999", "type": "refresh", "jti": "jti"}):
            response = await client.post("/users/refresh")

            assert response.status_code == status.HTTP_401_UNAUTHORIZED


class TestLogout:
    """Тесты выхода из системы"""

    @pytest.mark.asyncio
    async def test_logout_success(self, client):
        """Тест: успешный выход"""
        response = await client.post("/users/logout")
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["msg"] == "Logged out"


class TestGetCurrentUser:
    """Тесты получения текущего пользователя"""

    @pytest.mark.asyncio
    async def test_get_current_user_success(self, client, mock_user_repo):
        """Тест: успешное получение профиля"""
        mock_user = MagicMock(
            id=1,
            email="test@example.com",
            first_name="Ivan",
            last_name="Ivanov",
            middle_name="Ivanovich",
            is_active=True,
            created_at="2024-01-01T00:00:00",
            updated_at=None,
        )
        mock_user_repo.get_by_id.return_value = mock_user

        with patch("app.routers.users.verify_token", return_value={"sub": "1"}):
            response = await client.get("/users/me", headers={"Authorization": "Bearer valid_access_token"})

        assert response.status_code == status.HTTP_200_OK
        assert response.json()["email"] == "test@example.com"

    @pytest.mark.asyncio
    async def test_get_current_user_not_found(self, client, mock_user_repo, app):
        """Тест: пользователь не найден"""
        from app.dependencies import get_current_user

        async def mock_get_current_user_not_found():
            return MagicMock(id=999, email="notfound@example.com")

        # Используем app из фикстуры
        app.dependency_overrides[get_current_user] = mock_get_current_user_not_found
        mock_user_repo.get_by_id.return_value = None

        with patch("app.routers.users.verify_token", return_value={"sub": "999"}):
            response = await client.get("/users/me", headers={"Authorization": "Bearer valid_token"})

        assert response.status_code == status.HTTP_404_NOT_FOUND
        app.dependency_overrides.pop(get_current_user, None)


class TestUpdateCurrentUser:
    """Тесты обновления профиля пользователя"""

    @pytest.mark.asyncio
    async def test_update_profile_success(self, client, mock_user_repo):
        """Тест: успешное обновление профиля"""
        mock_user = MagicMock(
            id=1,
            email="test@example.com",
            first_name="NewName",
            last_name="NewLast",
            middle_name="Ivanovich",
            is_active=True,
        )
        mock_user_repo.update.return_value = mock_user

        with patch("app.routers.users.verify_token", return_value={"sub": "1"}):
            response = await client.put(
                "/users/me", json={"first_name": "NewName"}, headers={"Authorization": "Bearer valid_token"}
            )

        assert response.status_code == status.HTTP_200_OK
        assert response.json()["first_name"] == "NewName"

    @pytest.mark.asyncio
    async def test_update_profile_not_found(self, client, mock_user_repo, app):
        """Тест: пользователь не найден при обновлении"""
        from app.dependencies import get_current_user

        async def mock_get_current_user_not_found():
            return MagicMock(id=999, email="notfound@example.com")

        app.dependency_overrides[get_current_user] = mock_get_current_user_not_found
        mock_user_repo.update.return_value = None

        with patch("app.routers.users.verify_token", return_value={"sub": "999"}):
            response = await client.put(
                "/users/me", json={"first_name": "NewName"}, headers={"Authorization": "Bearer valid_token"}
            )

        assert response.status_code == status.HTTP_404_NOT_FOUND
        app.dependency_overrides.pop(get_current_user, None)

    @pytest.mark.asyncio
    async def test_update_profile_empty_body(self, client):
        """Тест: пустое тело запроса"""
        with patch("app.routers.users.verify_token", return_value={"sub": "1"}):
            response = await client.put("/users/me", json={}, headers={"Authorization": "Bearer valid_token"})
        assert response.status_code == 422


class TestUserFlow:
    """Тесты полного цикла"""

    @pytest.mark.asyncio
    async def test_full_user_flow(self, client, mock_user_repo):
        # 1. Регистрация
        mock_user_repo.exists_with_email.return_value = False
        mock_user_repo.create.return_value = MagicMock(
            id=1,
            email="test@example.com",
            first_name="Ivan",
            last_name="Ivanov",
            middle_name=None,
            is_active=True,
            created_at="2024-01-01T00:00:00",
            updated_at=None,
        )

        with patch_get_hash:
            reg_response = await client.post(
                "/users/register",
                json={
                    "email": "test@example.com",
                    "first_name": "Ivan",
                    "last_name": "Ivanov",
                    "password": "SecurePass123!",
                },
            )
        assert reg_response.status_code == status.HTTP_200_OK

        # 2. Логин
        mock_user_repo.get_by_email.return_value = MagicMock(
            id=1, email="test@example.com", hashed_password="$2b$12$hashed", is_active=True
        )
        with patch_verify_password, patch_create_access, patch_create_refresh, patch_jwt_decode:
            login_response = await client.post(
                "/users/login", json={"email": "test@example.com", "password": "SecurePass123!"}
            )
            assert login_response.status_code == status.HTTP_200_OK

        # 3. Выход
        logout_response = await client.post("/users/logout")
        assert logout_response.status_code == status.HTTP_200_OK
