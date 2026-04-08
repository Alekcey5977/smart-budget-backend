import os
import pathlib
import sys
import uuid
from unittest.mock import AsyncMock, patch

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import String, TypeDecorator
from sqlalchemy.dialects.sqlite import JSON
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

SERVICE_ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
PROJECT_ROOT = SERVICE_ROOT.parent
if str(SERVICE_ROOT) not in sys.path:
    sys.path.insert(0, str(SERVICE_ROOT))
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Создаем универсальный тип, который умеет работать и со строками, и с объектами uuid.UUID.


class UniversalUUID(TypeDecorator):
    impl = String(36)
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if isinstance(value, uuid.UUID):
            return str(value)
        return value

    def process_result_value(self, value, dialect):
        return value


import sqlalchemy as sa  # noqa: E402

sa.UUID = UniversalUUID

# Настройка окружения для тестов
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"
os.environ["PSEUDO_BANK_SERVICE_URL"] = "http://fake-bank-service"

from app.database import Transaction_Base, get_db  # noqa: E402
from app.dependencies import get_user_id_from_header  # noqa: E402
from app.main import app  # noqa: E402

# Создаем асинхронный engine для SQLite
engine = create_async_engine(
    os.environ["DATABASE_URL"], echo=False, future=True, connect_args={"check_same_thread": False}
)


TestingSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

# --- ФИКСТУРЫ ---


@pytest.fixture(autouse=True)
def mock_event_publisher():
    with patch("app.routers.transactions.EventPublisher") as mock:
        mock.return_value.publish = AsyncMock()
        yield mock


@pytest.fixture(autouse=True)
def mock_cache_client():
    """Мокируем cache_client для всех интеграционных тестов"""
    with patch("app.routers.transactions.cache_client") as mock:
        mock.get = AsyncMock(return_value=None)
        mock.set = AsyncMock()
        mock.delete = AsyncMock()
        mock.delete_pattern = AsyncMock()
        yield mock


@pytest_asyncio.fixture(scope="function")
async def db_session():
    """
    Создает чистую схему БД для каждого теста.
    Адаптирует типы Postgres (JSONB) под SQLite (JSON).
    """
    # Адаптация типов под SQLite перед созданием таблиц
    for table in Transaction_Base.metadata.tables.values():
        for column in table.columns:
            if hasattr(column.type, "name") and column.type.name == "jsonb":
                column.type = JSON()

    async with engine.begin() as conn:
        await conn.run_sync(Transaction_Base.metadata.create_all)

    async with TestingSessionLocal() as session:
        yield session

    async with engine.begin() as conn:
        await conn.run_sync(Transaction_Base.metadata.drop_all)


@pytest_asyncio.fixture
async def client(db_session):
    """
    Создает асинхронный клиент, внедряя тестовую сессию БД.
    """

    async def override_get_db():
        yield db_session

    def override_get_user_id():
        return 123

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_user_id_from_header] = override_get_user_id

    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()
