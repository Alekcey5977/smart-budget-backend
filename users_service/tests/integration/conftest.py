import os
from typing import AsyncGenerator
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
from app.auth import ALGORITHM
from app.database import User_Base, get_db
from app.models import User
from fastapi import Depends, FastAPI, Header, HTTPException
from httpx import ASGITransport, AsyncClient
from jose import jwt
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

# ============================================================================
# 1. НАСТРОЙКА ПЕРЕМЕННЫХ ОКРУЖЕНИЯ (до импортов app.*)
# ============================================================================
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"
os.environ["ACCESS_SECRET_KEY"] = "test_access_secret_key_integ"
os.environ["REFRESH_SECRET_KEY"] = "test_refresh_secret_key_integ"
os.environ["BANK_SECRET_KEY"] = "test_bank_secret_key_integ"
os.environ["PSEUDO_BANK_SERVICE_URL"] = "http://fake-bank-service"
os.environ["TRANSACTIONS_SERVICE_URL"] = "http://fake-transactions-service"
os.environ["REDIS_URL"] = "redis://localhost:6379"


TEST_SECRET_KEY = os.environ.get("ACCESS_SECRET_KEY")

# ============================================================================
# БАЗА ДАННЫХ
# ============================================================================
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"
engine = create_async_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False}, poolclass=StaticPool)
TestingSessionLocal = async_sessionmaker(autocommit=False, autoflush=False, bind=engine, class_=AsyncSession)


@pytest_asyncio.fixture(scope="function")
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    async with engine.begin() as conn:
        await conn.run_sync(User_Base.metadata.create_all)
    async with TestingSessionLocal() as session:
        yield session
    async with engine.begin() as conn:
        await conn.run_sync(User_Base.metadata.drop_all)


# ============================================================================
# ФИКСТУРЫ ДАННЫХ
# ============================================================================


@pytest_asyncio.fixture(scope="function")
async def test_user(db_session: AsyncSession) -> User:
    from passlib.context import CryptContext

    pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")
    user = User(
        email="integration@test.com",
        hashed_password=pwd_context.hash("password123"),
        first_name="Integration",
        last_name="Test",
        is_active=True,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.fixture(scope="function")
def auth_headers(test_user: User) -> dict:

    to_encode = {"sub": str(test_user.id), "type": "access"}
    # Ручное создание токена для тестов
    encoded_jwt = jwt.encode(to_encode, TEST_SECRET_KEY, algorithm=ALGORITHM)

    return {"Authorization": f"Bearer {encoded_jwt}"}


@pytest.fixture(scope="function")
def mock_bank_service():
    with patch("app.repository.bank_account_repository.httpx.AsyncClient") as mock_client:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"balance": "10000.00", "currency": "RUB"}
        mock_instance = AsyncMock()
        mock_instance.post.return_value = mock_response
        mock_client.return_value.__aenter__.return_value = mock_instance
        yield mock_instance


@pytest.fixture(scope="function")
def mock_event_publisher():
    with (
        patch("app.repository.bank_account_repository.EventPublisher") as mock_pub,
        patch("app.repository.user_repository.EventPublisher"),
    ):
        mock_instance = AsyncMock()
        mock_pub.return_value = mock_instance
        yield mock_instance


@pytest.fixture(scope="function")
def mock_bank_account_cache_client():
    """Мокирует cache_client в модуле bank_account."""
    with patch("app.routers.bank_account.cache_client") as mock_cache:
        mock_cache.get = AsyncMock(return_value=None)
        mock_cache.set = AsyncMock()
        mock_cache.delete = AsyncMock()
        mock_cache.delete_pattern = AsyncMock(return_value=0)
        yield mock_cache


@pytest.fixture(scope="function")
def mock_users_cache_client():
    """Мокирует cache_client в модуле users."""
    with patch("app.routers.users.cache_client") as mock_cache:
        mock_cache.get = AsyncMock(return_value=None)
        mock_cache.set = AsyncMock()
        mock_cache.delete = AsyncMock()
        mock_cache.delete_pattern = AsyncMock(return_value=0)
        yield mock_cache


# ============================================================================
# КЛИЕНТ (FIXTURE)
# ============================================================================


@pytest_asyncio.fixture(scope="function")
async def client(
    db_session: AsyncSession, mock_event_publisher: AsyncMock, mock_bank_account_cache_client, mock_users_cache_client
) -> AsyncGenerator[AsyncClient, None]:
    # Импортируем роутеры
    from app.repository.bank_account_repository import Bank_AccountRepository
    from app.repository.user_repository import UserRepository
    from app.routers import bank_account, users
    from app.routers.users import get_user_repository

    test_app = FastAPI()

    # 1. Переопределение БД
    async def override_get_db():
        yield db_session

    async def override_get_user_repository(db: AsyncSession = Depends(override_get_db)):
        return UserRepository(db, event_publisher=mock_event_publisher)

    async def override_get_bank_account_repository(db: AsyncSession = Depends(override_get_db)):
        return Bank_AccountRepository(db)

    test_app.dependency_overrides[get_db] = override_get_db
    test_app.dependency_overrides[get_user_repository] = override_get_user_repository

    if hasattr(bank_account, "get_bank_account_repository"):
        test_app.dependency_overrides[bank_account.get_bank_account_repository] = override_get_bank_account_repository

    # 2. Переопределение АВТОРИЗАЦИИ
    async def override_get_current_user(authorization: str = Header(None, alias="Authorization")):
        if not authorization:
            raise HTTPException(status_code=401, detail="Not authenticated")

        token = authorization.replace("Bearer ", "")

        try:
            payload = jwt.decode(token, TEST_SECRET_KEY, algorithms=[ALGORITHM])
            user_id = int(payload.get("sub"))
        except Exception:
            raise HTTPException(status_code=401, detail="Invalid token")

        # Находим пользователя в БД
        user_repo = UserRepository(db_session)
        user = await user_repo.get_by_id(user_id)

        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        return user

    test_app.dependency_overrides[bank_account.get_current_user] = override_get_current_user

    # 3. Подключение роутеров
    test_app.include_router(users.router)
    test_app.include_router(bank_account.router)

    async with AsyncClient(transport=ASGITransport(app=test_app), base_url="http://test") as ac:
        yield ac
