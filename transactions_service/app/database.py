import os
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.exc import SQLAlchemyError
from dotenv import load_dotenv
from .models import Transaction_Base, Transaction, Category


# Загружаем переменные из .env файла
load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

# Создание асинхронного соединения для БД
engine = create_async_engine(
    DATABASE_URL,
    echo=True,
    future=True
)

# Создание асинхронных сессий дл БД
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False
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


# Асинхронное создание теаблиц в БД
async def create_tables():
    async with engine.begin() as conn:
        await conn.run_sync(Transaction_Base.metadata.create_all)


# Асинхронное закрытие соединений при остановке
async def shutdown():
    await engine.dispose()
