import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
from app.repository.bank_account_repository import Bank_AccountRepository
from app.repository.user_repository import UserRepository
from httpx import ASGITransport, AsyncClient

from shared.event_publisher import EventPublisher

# Настройка переменных окружения перед импортом приложения
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"
os.environ["JWT_SECRET_KEY"] = "test_secret_key_for_testing_only"
os.environ["JWT_REFRESH_SECRET_KEY"] = "test_refresh_secret_key_for_testing"
os.environ["PSEUDO_BANK_SERVICE_URL"] = "http://fake-bank-url"
os.environ["TRANSACTIONS_SERVICE_URL"] = "http://fake-transactions-url"
os.environ["REDIS_URL"] = "redis://localhost:6379"


@pytest.fixture
def mock_cache_client():
    """Мокирует cache_client для всех тестов."""
    with patch("app.cache.cache_client") as mock_cache:
        mock_cache.get = AsyncMock(return_value=None)
        mock_cache.set = AsyncMock()
        mock_cache.delete = AsyncMock()
        mock_cache.delete_pattern = AsyncMock(return_value=0)
        yield mock_cache


@pytest.fixture
def mock_bank_account_cache_client():
    """Мокирует cache_client в модуле bank_account."""
    with patch("app.routers.bank_account.cache_client") as mock_cache:
        mock_cache.get = AsyncMock(return_value=None)
        mock_cache.set = AsyncMock()
        mock_cache.delete = AsyncMock()
        mock_cache.delete_pattern = AsyncMock(return_value=0)
        yield mock_cache


@pytest.fixture
def mock_users_cache_client():
    """Мокирует cache_client в модуле users."""
    with patch("app.routers.users.cache_client") as mock_cache:
        mock_cache.get = AsyncMock(return_value=None)
        mock_cache.set = AsyncMock()
        mock_cache.delete = AsyncMock()
        mock_cache.delete_pattern = AsyncMock(return_value=0)
        yield mock_cache


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
def mock_bank_account_repo():
    """
    Мок репозитория банковских счетов.
    """
    repo = AsyncMock(spec=Bank_AccountRepository)

    # Мок создания счета (возвращает объект счета и хэш)
    mock_account = MagicMock()
    mock_account.bank_account_id = 1
    mock_account.bank_account_name = "Test Account"
    mock_account.currency = "RUB"
    mock_account.balance = "100.00"

    # Мок для поля bank
    mock_bank = MagicMock()
    mock_bank.name = "Сбербанк"
    mock_account.bank = mock_bank

    repo.create.return_value = (mock_account, "test_hash")
    repo.get_all_by_user_id.return_value = [mock_account]
    repo.delete.return_value = mock_account

    return repo


@pytest.fixture
def mock_db_session():
    """Мок сессии БД для unit-тестов репозитория"""
    session = MagicMock()
    session.execute = AsyncMock()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()
    session.add = MagicMock()
    session.flush = AsyncMock()
    session.delete = AsyncMock()
    return session


@pytest.fixture
def mock_hash_function():
    """
    Патчит функцию хеширования в модуле репозитория.
    """
    with patch("app.repository.bank_account_repository.get_bank_account_number_hash") as mock_func:
        yield mock_func


@pytest.fixture
def bank_account_create_schema():
    """Схема создания счёта для тестов"""
    from app.schemas import Bank_AccountCreate
    return Bank_AccountCreate(
        bank_account_number="40817810099910004312",
        bank_account_name="Test Account",
        bank="Сбербанк"
    )


@pytest.fixture(autouse=True)
def mock_httpx_async_client():
    """
    Автоматически мокает httpx.AsyncClient во всех тестах.
    Предотвращает реальные сетевые вызовы.
    """
    with patch("app.repository.bank_account_repository.httpx.AsyncClient") as mock_client:
        instance = AsyncMock()
        response = MagicMock()
        response.status_code = 200
        response.json.return_value = {"balance": "1000.00", "currency": "RUB"}
        instance.post.return_value = response

        # Настройка контекстного менеджера (async with ... as client)
        mock_client.return_value.__aenter__.return_value = instance
        yield mock_client


@pytest.fixture
def user_repo(mock_db_session, mock_event_publisher):
    """Реальный экземпляр репозитория с мокнутой сессией БД"""
    from app.repository.user_repository import UserRepository
    return UserRepository(db=mock_db_session, event_publisher=mock_event_publisher)


@pytest.fixture
def app():
    """Фикстура, возвращающая экземпляр приложения"""
    from app.main import app as fastapi_app
    return fastapi_app


@pytest_asyncio.fixture(scope="function")
async def client(app, mock_user_repo, mock_bank_account_cache_client, mock_users_cache_client):
    """Асинхронный клиент с переопределением зависимостей"""
    from app.routers.bank_account import router as bank_router
    from app.routers.users import get_user_repository

    # Подключаем роутер
    app.include_router(bank_router)

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


@pytest.fixture
def bank_account_repo(mock_db_session, mock_event_publisher):
    """Экземпляр Bank_AccountRepository с мокнутыми зависимостями"""
    from app.repository.bank_account_repository import Bank_AccountRepository
    return Bank_AccountRepository(db=mock_db_session)
