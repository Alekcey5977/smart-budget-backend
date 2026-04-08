import os

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+asyncpg://postgres:postgres@images-db:5432/images_db")

# Создание async engine
engine = create_async_engine(
    DATABASE_URL,
    echo=True,  # Логирование SQL запросов (отключить в production)
    poolclass=NullPool,  # Отключение пула соединений для асинхронных операций
    future=True,
)

# Создание фабрики сессий
async_session_maker = async_sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False, autocommit=False, autoflush=False
)


async def get_db() -> AsyncSession:
    """
    Dependency для получения сессии базы данных.

    Usage:
        @router.get("/")
        async def endpoint(db: AsyncSession = Depends(get_db)):
            # работа с БД
    """
    async with async_session_maker() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
