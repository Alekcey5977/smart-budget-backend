import os
from unittest.mock import AsyncMock, MagicMock

import pytest
import pytest_asyncio
from app.repository.user_repository import UserRepository
from httpx import ASGITransport, AsyncClient

from shared.event_publisher import EventPublisher

os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"
os.environ["JWT_SECRET_KEY"] = "test_secret_key_for_testing_only"
os.environ["JWT_REFRESH_SECRET_KEY"] = "test_refresh_secret_key_for_testing"


@pytest.fixture
def mock_event_publisher():
    publisher = AsyncMock(spec=EventPublisher)
    publisher.publish = AsyncMock()
    return publisher


@pytest.fixture
def mock_user_repo():
    repo = MagicMock(spec=UserRepository)
    repo.get_by_id = AsyncMock(return_value=None)
    repo.get_by_email = AsyncMock(return_value=None)
    repo.create = AsyncMock(return_value=MagicMock(
        id=1, email="test@example.com"))
    repo.update = AsyncMock(return_value=None)
    repo.exists_with_email = AsyncMock(return_value=False)
    repo.deactivate_refresh_token = AsyncMock(return_value=None)
    return repo

@pytest.fixture
def mock_db_session():
    """Мок сессии БД для unit-тестов репозитория"""
    session = MagicMock()
    session.execute = AsyncMock()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()
    session.add = MagicMock()
    return session


@pytest.fixture
def user_repo(mock_db_session, mock_event_publisher):
    """Реальный экземпляр репозитория с мокнутой сессией БД"""
    from app.repository.user_repository import UserRepository
    return UserRepository(db=mock_db_session, event_publisher=mock_event_publisher)

# --- Фикстуры для тестов ---

@pytest.fixture
def app():
    """Фикстура, возвращающая экземпляр приложения"""
    from app.main import app as fastapi_app
    return fastapi_app


@pytest_asyncio.fixture(scope="function")
async def client(app, mock_user_repo):
    """Асинхронный клиент с переопределением зависимостей"""
    from app.routers.users import get_user_repository

    async def override_get_user_repo():
        return mock_user_repo

    app.dependency_overrides[get_user_repository] = override_get_user_repo

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        follow_redirects=True,
    ) as ac:
        yield ac

    app.dependency_overrides.clear()


@pytest.fixture
def mock_get_current_user(app):
    """Фикстура для подмены зависимости аутентификации"""
    from app.dependencies import get_current_user

    async def _mock_get_current_user():
        return MagicMock(
            id=1, email="test@example.com", first_name="Ivan",
            last_name="Ivanov", is_active=True
        )

    app.dependency_overrides[get_current_user] = _mock_get_current_user
    yield
    app.dependency_overrides.pop(get_current_user, None)
