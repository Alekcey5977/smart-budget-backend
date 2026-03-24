import os
import sys
from pathlib import Path
from unittest.mock import AsyncMock, patch

# Задаём переменные окружения ДО импорта app
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

# Добавляем корень проекта в sys.path чтобы shared/ был доступен
PROJECT_ROOT = Path(__file__).parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.database import get_db  # noqa: E402
from app.main import app  # noqa: E402
from app.models import Base  # noqa: E402

# ---------------------------------------------------------------------------
# 1) Тестовый движок — SQLite in-memory (не нужен PostgreSQL)
# ---------------------------------------------------------------------------
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

engine_test = create_async_engine(TEST_DATABASE_URL, echo=False)


# ---------------------------------------------------------------------------
# 2) Фикстура: создание/удаление таблиц на каждый тестовый модуль
# ---------------------------------------------------------------------------
@pytest.fixture(autouse=True, scope="module")
async def setup_database():
    """Создаёт таблицы перед тестами модуля, удаляет после."""
    async with engine_test.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine_test.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


# ---------------------------------------------------------------------------
# 3) Фикстура: тестовая сессия (изолирована для каждого теста)
# ---------------------------------------------------------------------------
TestSessionLocal = async_sessionmaker(
    engine_test,
    class_=AsyncSession,
    expire_on_commit=False,
)


@pytest.fixture
async def db_session():
    """
    Отдельная сессия для каждого теста.
    После теста откатывает все изменения — тесты не влияют друг на друга.
    """
    async with engine_test.connect() as conn:
        await conn.begin()

        session = AsyncSession(bind=conn, expire_on_commit=False)

        @event.listens_for(session.sync_session, "after_transaction_end")
        def restart_savepoint(session_sync, transaction):
            if transaction.nested and not transaction._parent.nested:
                session_sync.begin_nested()

        await conn.begin_nested()  # SAVEPOINT

        yield session

        await session.close()
        await conn.rollback()


# ---------------------------------------------------------------------------
# 4) Фикстура: мок EventPublisher (тесты не зависят от Redis)
# ---------------------------------------------------------------------------
@pytest.fixture(autouse=True)
def mock_event_publisher():
    """
    Подменяет EventPublisher на AsyncMock.
    Предотвращает попытки подключения к Redis при обновлении аватара.
    """
    with patch("app.repository.image_repository.EventPublisher") as MockPub:
        mock_instance = MockPub.return_value
        mock_instance.publish = AsyncMock(return_value=None)
        yield mock_instance


# ---------------------------------------------------------------------------
# 5) Фикстура: тестовый HTTP-клиент FastAPI
# ---------------------------------------------------------------------------
@pytest.fixture
async def client(db_session: AsyncSession):
    """
    AsyncClient для тестирования API endpoints.
    Подменяет get_db на тестовую сессию.
    """

    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()
