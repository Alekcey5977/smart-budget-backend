import asyncio
import logging
import os

from app.models import Transaction_Base
from dotenv import load_dotenv
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# Загружаем переменные из .env файла
load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

# Создание асинхронного соединения для БД
engine = create_async_engine(DATABASE_URL, echo=True, future=True)

# Создание асинхронных сессий дл БД
AsyncSessionLocal = async_sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False, autoflush=False, autocommit=False
)


# Асинхронное открытие сессии для эндпоинтов при взаимодействии с БД
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
        await conn.run_sync(Transaction_Base.metadata.create_all)
    logger.info("✅ Таблицы созданы")


# Асинхронное закрытие соединений при остановке
async def shutdown():
    await engine.dispose()
