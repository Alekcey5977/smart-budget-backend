"""
Скрипт для загрузки тестовых изображений в базу данных images_service.

ВАЖНО: Этот скрипт запускается ВНУТРИ Docker контейнера images-service!
Используйте команду: make load-test-images
"""

import asyncio
import json
import os
import sys

# Внутри контейнера модули находятся в /app
sys.path.insert(0, "/app")

from app.models import Base, EntityType, Image
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine


async def load_test_data(database_url: str, json_path: str):
    """
    Загрузка тестовых данных из JSON в базу данных.

    Args:
        database_url: URL подключения к БД
        json_path: Путь к JSON файлу с данными
    """
    print("Connecting to database...")

    # Создание engine и session maker
    engine = create_async_engine(database_url, echo=False)
    async_session_maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    # Создание таблиц если они не существуют
    async with engine.begin() as conn:
        print("Creating tables if not exist...")
        await conn.run_sync(Base.metadata.create_all)

    # Чтение JSON файла
    print(f"Reading test data from: {json_path}")

    with open(json_path, "r", encoding="utf-8") as f:
        test_data = json.load(f)

    print(f"Loaded {len(test_data)} records from JSON")

    # Вставка данных
    async with async_session_maker() as session:
        try:
            # Очистка существующих данных перед загрузкой
            deleted = await session.execute(delete(Image))
            await session.commit()
            print(f"Cleared {deleted.rowcount} existing records")

            inserted_count = 0

            for item in test_data:
                # Конвертация SVG текста в байты
                svg_text = item["file_data_svg"]
                file_data = svg_text.encode("utf-8")

                # Создание объекта Image
                image = Image(
                    entity_type=EntityType[item["entity_type"].upper()],
                    entity_id=item["entity_id"],
                    file_data=file_data,
                    mime_type=item["mime_type"],
                    file_size=len(file_data),
                    is_default=item["is_default"],
                )

                session.add(image)
                inserted_count += 1

            # Коммит всех изменений
            await session.commit()

            print(f"\n[SUCCESS] Inserted {inserted_count} images into database")
            print("\nDistribution:")
            print("  - Avatars: 10 (default presets)")
            print("  - Categories: 20 (with icons)")
            print("  - Merchants: 20 (with logos)")

        except Exception as e:
            await session.rollback()
            print(f"\n[ERROR] Failed to insert data: {e}")
            raise
        finally:
            await session.close()

    # Закрытие engine
    await engine.dispose()


async def main():
    """Главная функция"""
    # URL базы данных внутри Docker сети
    database_url = os.getenv("DATABASE_URL", "postgresql+asyncpg://img_user:img_password@images-db:5432/images_db")

    # Путь к JSON файлу (примонтирован в /testData)
    json_path = "/testData/images_data.json"

    print("=" * 60)
    print("Images Service - Test Data Loader")
    print("=" * 60)

    try:
        await load_test_data(database_url, json_path)
        print("\n" + "=" * 60)
        print("[DONE] Test data loaded successfully!")
        print("=" * 60)
    except Exception as e:
        print("\n" + "=" * 60)
        print(f"[FAILED] Error: {e}")
        print("=" * 60)
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
