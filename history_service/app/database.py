import os

from app.models import History_Base
from dotenv import load_dotenv
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

engine = create_async_engine(DATABASE_URL, echo=True, future=True)

AsyncSessionLocal = async_sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False, autoflush=False, autocommit=False
)


async def get_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()

        except SQLAlchemyError:
            await session.rollback()
            raise

        finally:
            await session.close()


async def create_tables():
    async with engine.begin() as conn:
        await conn.run_sync(History_Base.metadata.create_all)


async def shutdown():
    await engine.dispose()


def get_db_session() -> AsyncSession:
    """Создаёт и возвращает новую сессию БД (для фоновых задач)"""
    return AsyncSessionLocal()
