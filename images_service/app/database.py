import asyncio
import logging
import os

from app.models import Base
from dotenv import load_dotenv
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Загружаем переменные из .env файла
load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

# Создание асинхронного соединения для БД
# pool_size/max_overflow not supported by SQLite (used in tests)
_pool_kwargs = {} if (DATABASE_URL or "").startswith("sqlite") else {"pool_size": 20, "max_overflow": 40, "pool_pre_ping": True}
engine = create_async_engine(DATABASE_URL, echo=False, future=True, **_pool_kwargs)

# Создание асинхронных сессий для БД
AsyncSessionLocal = async_sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False, autoflush=False, autocommit=False
)


# Асинхронное открытие сессии для эндпоинтов при взаимодействии с БД
async def get_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()

        except Exception:
            await session.rollback()
            raise

        finally:
            await session.close()


# Ожидание готовности базы данных
async def await_db_ready(retries=30, delay=2):
    """
    Пытается подключиться к БД, повторяя попытки при отказе.
    """
    for i in range(retries):
        try:
            async with engine.begin() as conn:
                await conn.execute(text("SELECT 1"))
            logger.info("✅ Подключение к базе данных установлено")
            return
        except Exception as e:
            logger.warning(
                f"❌ Не удалось подключиться к БД, попытка {i+1}/{retries}: {e}")
            await asyncio.sleep(delay)
    raise Exception(
        "❌ Не удалось подключиться к базе данных после всех попыток")


# Асинхронное создание таблиц в БД
async def create_tables():
    await await_db_ready()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("✅ Таблицы созданы")


# Асинхронное закрытие соединений при остановке
async def shutdown():
    await engine.dispose()
