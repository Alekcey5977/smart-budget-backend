from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from typing import Optional
from shared.event_publisher import EventPublisher
from shared.event_schema import DomainEvent
from datetime import datetime
from uuid import uuid4
import uuid

from app.models import Image, EntityType


class ImageRepository:
    """Репозиторий для работы с изображениями"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_image_by_id(self, image_id: uuid.UUID) -> Optional[Image]:
        """Получить изображение по ID"""
        result = await self.db.execute(
            select(Image).where(Image.id == image_id)
        )
        return result.scalar_one_or_none()

    async def get_default_avatars(self) -> list[Image]:
        """Получить все предустановленные аватарки"""
        result = await self.db.execute(
            select(Image).where(
                and_(
                    Image.entity_type == EntityType.USER_AVATAR,
                    Image.is_default.is_(True)
                )
            ).order_by(Image.created_at)
        )
        return list(result.scalars().all())

    async def get_user_avatar(self, user_id: int) -> Optional[Image]:
        """
        Получить аватарку пользователя.

        Возвращает пользовательскую привязку или None если не установлена.
        """
        result = await self.db.execute(
            select(Image).where(
                and_(
                    Image.entity_type == EntityType.USER_AVATAR,
                    Image.entity_id == str(user_id),
                    Image.is_default.is_(False)
                )
            )
        )
        return result.scalar_one_or_none()

    async def update_user_avatar(self, user_id: int, avatar_id: uuid.UUID) -> Image:
        """
        Обновить аватарку пользователя.

        Создает новую запись-привязку пользователя к дефолтной аватарке.
        Если привязка уже существует - обновляет её.
        """
        # Проверяем что avatar_id существует и является дефолтной аватаркой
        default_avatar = await self.get_image_by_id(avatar_id)
        if not default_avatar or not default_avatar.is_default or default_avatar.entity_type != EntityType.USER_AVATAR:
            raise ValueError("Avatar not found or is not a default avatar")

        # Проверяем существующую привязку
        existing = await self.get_user_avatar(user_id)

        if existing:
            # Удаляем старую привязку
            await self.db.delete(existing)
            await self.db.flush()

        # Создаем новую привязку (копируем дефолтную аватарку для пользователя)
        user_avatar = Image(
            entity_type=EntityType.USER_AVATAR,
            entity_id=str(user_id),
            file_data=default_avatar.file_data,
            mime_type=default_avatar.mime_type,
            file_size=default_avatar.file_size,
            is_default=False  # Это уже пользовательская привязка
        )

        self.db.add(user_avatar)
        await self.db.flush()
        await self.db.refresh(user_avatar)


        # Публикуем событие о смене аватара
        publisher = EventPublisher()
        event = DomainEvent(
            event_id=uuid4(),
            event_type="user.avatar.updated",
            source="images-service",
            timestamp=datetime.now(),
            payload={
                "user_id": user_id,
                "avatar_id": str(avatar_id)
            }
        )
        await publisher.publish(event)

        return user_avatar

    async def get_category_images_mapping(self) -> list[tuple[str, uuid.UUID, str]]:
        """
        Получить маппинг категорий к изображениям.

        Returns:
            list[tuple]: [(entity_id, image_id, mime_type), ...]
        """
        result = await self.db.execute(
            select(
                Image.entity_id,
                Image.id,
                Image.mime_type
            ).where(
                and_(
                    Image.entity_type == EntityType.CATEGORY,
                    Image.entity_id.isnot(None)
                )
            ).order_by(Image.entity_id)
        )
        return list(result.all())

    async def get_merchant_images_mapping(self) -> list[tuple[str, uuid.UUID, str]]:
        """
        Получить маппинг мерчантов к изображениям.

        Returns:
            list[tuple]: [(entity_id, image_id, mime_type), ...]
        """
        result = await self.db.execute(
            select(
                Image.entity_id,
                Image.id,
                Image.mime_type
            ).where(
                and_(
                    Image.entity_type == EntityType.MERCHANT,
                    Image.entity_id.isnot(None)
                )
            ).order_by(Image.entity_id)
        )
        return list(result.all())

    async def get_image_by_entity(
        self,
        entity_type: EntityType,
        entity_id: str
    ) -> Optional[Image]:
        """Получить изображение по типу сущности и её ID"""
        result = await self.db.execute(
            select(Image).where(
                and_(
                    Image.entity_type == entity_type,
                    Image.entity_id == entity_id
                )
            )
        )
        return result.scalar_one_or_none()

    async def create_image(
        self,
        entity_type: EntityType,
        file_data: bytes,
        mime_type: str,
        entity_id: Optional[str] = None,
        is_default: bool = True
    ) -> Image:
        """
        Создать новое изображение.

        Args:
            entity_type: Тип сущности
            file_data: Бинарные данные
            mime_type: MIME-тип
            entity_id: ID сущности (опционально)
            is_default: Предустановленное или нет

        Returns:
            Image: Созданное изображение
        """
        image = Image(
            entity_type=entity_type,
            entity_id=entity_id,
            file_data=file_data,
            mime_type=mime_type,
            file_size=len(file_data),
            is_default=is_default
        )

        self.db.add(image)
        await self.db.flush()
        await self.db.refresh(image)

        return image
