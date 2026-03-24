import enum
import uuid
from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, Index, Integer, LargeBinary, String
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class EntityType(str, enum.Enum):
    """Типы сущностей для изображений"""
    USER_AVATAR = "user_avatar"
    CATEGORY = "category"
    MERCHANT = "merchant"


class Image(Base):
    """
    Модель для хранения изображений.

    Универсальная таблица для хранения:
    - Аватарок пользователей
    - Иконок категорий
    - Логотипов мерчантов
    """
    __tablename__ = "images"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    entity_type = Column(
        SQLEnum(EntityType, name="entity_type_enum"),
        nullable=False,
        comment="Тип сущности: user_avatar, category, merchant"
    )
    entity_id = Column(
        String,
        nullable=True,
        comment="ID сущности (user_id, category_id, merchant_id). NULL для дефолтных изображений"
    )
    file_data = Column(
        LargeBinary,
        nullable=False,
        comment="Бинарные данные изображения"
    )
    mime_type = Column(
        String(50),
        nullable=False,
        comment="MIME-тип файла (image/jpeg, image/png, etc.)"
    )
    file_size = Column(
        Integer,
        nullable=False,
        comment="Размер файла в байтах"
    )
    is_default = Column(
        Boolean,
        nullable=False,
        default=False,
        comment="Предустановленное изображение (True) или пользовательская привязка (False)"
    )
    created_at = Column(
        DateTime,
        nullable=False,
        default=datetime.utcnow
    )
    updated_at = Column(
        DateTime,
        nullable=True,
        onupdate=datetime.utcnow
    )

    # Индексы для оптимизации запросов
    __table_args__ = (
        # Быстрый поиск по типу сущности и ID
        Index('ix_images_entity_type_id', 'entity_type', 'entity_id'),
        # Быстрый поиск предустановленных изображений по типу
        Index('ix_images_entity_type_default', 'entity_type', 'is_default'),
        # Уникальность: один пользователь может иметь только одну активную аватарку
        Index(
            'ix_images_unique_user_avatar',
            'entity_type', 'entity_id',
            unique=True,
            postgresql_where=(entity_type == EntityType.USER_AVATAR) & (is_default.is_(False))
        ),
    )

    def __repr__(self):
        return f"<Image(id={self.id}, entity_type={self.entity_type}, entity_id={self.entity_id}, is_default={self.is_default})>"
