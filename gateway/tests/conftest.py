import os
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock

# Устанавливаем переменные окружения ДО импорта модулей приложения (они читаются на уровне модуля)
os.environ.setdefault("ACCESS_SECRET_KEY", "test-secret-key-for-gateway")
os.environ.setdefault("USERS_SERVICE_URL", "http://users-service-test")
os.environ.setdefault("PURPOSES_SERVICE_URL", "http://purposes-service-test")
os.environ.setdefault("NOTIFICATION_SERVICE_URL", "http://notification-service-test")
os.environ.setdefault("HISTORY_SERVICE_URL", "http://history-service-test")
os.environ.setdefault("IMAGES_SERVICE_URL", "http://images-service-test")
os.environ.setdefault("TRANSACTIONS_SERVICE_URL", "http://transactions-service-test")
os.environ.setdefault("PSEUDO_BANK_SERVICE_URL", "http://pseudo-bank-service-test")

from unittest.mock import AsyncMock

import pytest
from app.dependencies import get_current_user, get_current_user_with_profile
from app.main import app
from httpx import ASGITransport, AsyncClient
from jose import jwt

TEST_SECRET = "test-secret-key-for-gateway"
USER_ID = "1"
FAKE_USER = {"id": 1, "email": "test@example.com", "first_name": "Тест"}


def make_access_token(user_id: str = USER_ID, secret: str = TEST_SECRET) -> str:
    """Создаёт валидный JWT access-токен для тестов."""
    payload = {
        "sub": str(user_id),
        "type": "access",
        "exp": datetime.now(tz=timezone.utc) + timedelta(hours=1),
    }
    return jwt.encode(payload, secret, algorithm="HS256")


def auth_headers(user_id: str = USER_ID) -> dict:
    """Возвращает заголовок Authorization: Bearer <token>."""
    return {"Authorization": f"Bearer {make_access_token(user_id)}"}


async def mock_get_current_user():
    """Обходит JWT-валидацию и вызов users-service для большинства роутерных тестов."""
    return {
        "token": make_access_token(),
        "user": FAKE_USER,
        "user_id": USER_ID,
    }


def make_mock_http_response(
    status_code: int,
    json_data=None,
    content: bytes = None,
    headers: dict = None,
):
    """Создаёт MagicMock, имитирующий httpx.Response."""
    mock_resp = MagicMock()
    mock_resp.status_code = status_code
    if json_data is not None:
        mock_resp.json = MagicMock(return_value=json_data)
    if content is not None:
        mock_resp.content = content
    mock_resp.headers = headers or {}
    return mock_resp


@pytest.fixture(autouse=True)
def mock_cache(monkeypatch):
    """Мокируем cache_client глобально, чтобы тесты не обращались к Redis."""
    mock = AsyncMock()
    mock.connect = AsyncMock()
    mock.close = AsyncMock()
    mock.get = AsyncMock(return_value=None)
    mock.set = AsyncMock()
    mock.delete = AsyncMock()
    mock.delete_pattern = AsyncMock()
    monkeypatch.setattr("app.main.cache_client", mock)
    monkeypatch.setattr("app.dependencies.cache_client", mock)
    return mock


@pytest.fixture
async def client():
    """HTTP-клиент с переопределёнными зависимостями аутентификации."""
    app.dependency_overrides[get_current_user] = mock_get_current_user
    app.dependency_overrides[get_current_user_with_profile] = mock_get_current_user
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


@pytest.fixture
async def client_no_auth():
    """HTTP-клиент без переопределения get_current_user (для тестов на 401)."""
    app.dependency_overrides.clear()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac
