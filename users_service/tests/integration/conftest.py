from typing import AsyncGenerator
from unittest.mock import AsyncMock

import pytest
import pytest_asyncio

# Импорты вашего приложения
from app.database import User_Base, get_db
from app.main import app
from app.repository.user_repository import UserRepository
from fastapi import Depends

# <--- 1. Добавлен импорт ASGITransport
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool
from app.routers.users import get_user_repository

from shared.event_publisher import EventPublisher

# Настройка тестовой БД (SQLite in-memory)
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

engine = create_async_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)

TestingSessionLocal = async_sessionmaker(
    autocommit=False, autoflush=False, bind=engine, class_=AsyncSession
)


@pytest_asyncio.fixture(scope="function")
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    async with engine.begin() as conn:
        await conn.run_sync(User_Base.metadata.create_all)

    async with TestingSessionLocal() as session:
        yield session

    async with engine.begin() as conn:
        await conn.run_sync(User_Base.metadata.drop_all)


@pytest.fixture
def mock_event_publisher():
    publisher = EventPublisher()
    publisher.publish = AsyncMock()
    return publisher


@pytest_asyncio.fixture(scope="function")
async def client(db_session: AsyncSession, mock_event_publisher) -> AsyncGenerator[AsyncClient, None]:

    async def override_get_db():
        yield db_session

    async def override_get_user_repository(db: AsyncSession = Depends(override_get_db)):
        return UserRepository(db, event_publisher=mock_event_publisher)

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_user_repository] = override_get_user_repository

    # 2. Используем transport вместо app
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test"
    ) as ac:
        yield ac

    app.dependency_overrides.clear()
