import os
import sys
from unittest.mock import AsyncMock, patch

import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# --- Настройка окружения ---
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

os.environ["DATABASE_URL"] = TEST_DATABASE_URL
os.environ["PSEUDO_BANK_SERVICE_URL"] = "http://fake-service"

SERVICE_ROOT = os.path.dirname(os.path.dirname(
    os.path.dirname(os.path.abspath(__file__))))
if SERVICE_ROOT not in sys.path:
    sys.path.insert(0, SERVICE_ROOT)

from app.database import get_db  # noqa: E402
from app.main import app  # noqa: E402
from app.models import Transaction_Base  # noqa: E402


# ---------------------------------------------------------------------------
# Мок CacheClient (тесты не зависят от Redis)
# ---------------------------------------------------------------------------
@pytest_asyncio.fixture(autouse=True)
async def mock_cache_client():
    """
    Подменяет cache_client на AsyncMock.
    Предотвращает попытки подключения к Redis для кэширования.
    """
    with patch("app.routers.pseudo_bank.cache_client") as mock:
        mock.get = AsyncMock(return_value=None)
        mock.set = AsyncMock()
        mock.delete = AsyncMock()
        mock.delete_pattern = AsyncMock(return_value=0)
        yield mock


# --- Фикстуры для БД ---


@pytest_asyncio.fixture(scope="function")
async def db_engine():
    """
    Создаем движок SQLite и таблицы.
    """
    engine = create_async_engine(
        TEST_DATABASE_URL, echo=False, future=True, poolclass=StaticPool, connect_args={"check_same_thread": False}
    )

    # Создаем все таблицы
    async with engine.begin() as conn:
        await conn.execute(text("PRAGMA foreign_keys=ON"))
        await conn.run_sync(Transaction_Base.metadata.create_all)

    yield engine

    async with engine.begin() as conn:
        await conn.run_sync(Transaction_Base.metadata.drop_all)

    await engine.dispose()


@pytest_asyncio.fixture
async def db_session(db_engine):
    """
    Создает сессию.
    Используем вложенную транзакцию (SAVEPOINT), чтобы репозиторий мог делать commit,
    но изменения откатывались в конце теста.
    """
    async_session_maker = sessionmaker(
        db_engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session_maker() as session:
        async with session.begin():
            async with session.begin_nested():
                yield session


@pytest_asyncio.fixture
async def client(db_engine: AsyncSession):
    """
    Асинхронный клиент.
    """
    async_session_maker = sessionmaker(
        db_engine, class_=AsyncSession, expire_on_commit=False)

    async def override_get_db():
        async with async_session_maker() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()
