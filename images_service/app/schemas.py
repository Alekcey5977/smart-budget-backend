import uuid
from datetime import datetime
from typing import Optional

from app.models import EntityType
from pydantic import BaseModel, ConfigDict, Field

# ===========================
# Response Schemas
# ===========================

class ImageMetadata(BaseModel):
    """
    Метаданные изображения без бинарных данных.
    Используется для списков изображений.
    """
    id: uuid.UUID
    entity_type: EntityType
    entity_id: Optional[str] = None
    mime_type: str
    file_size: int
    is_default: bool
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class ImageResponse(ImageMetadata):
    """
    Полный ответ с изображением (включая бинарные данные в base64).
    Используется при запросе конкретного изображения.
    """
    file_data: bytes

    model_config = ConfigDict(from_attributes=True)


class ImageMappingItem(BaseModel):
    """
    Маппинг ID сущности к ID изображения.
    Для кэширования на фронтенде.
    """
    entity_id: str = Field(description="ID категории или мерчанта")
    image_id: uuid.UUID = Field(description="ID изображения")
    mime_type: str = Field(description="MIME-тип для оптимизации загрузки")


class ImageMappingResponse(BaseModel):
    """
    Ответ со списком маппингов для кэширования.
    """
    entity_type: EntityType
    mappings: list[ImageMappingItem]


# ===========================
# Request Schemas
# ===========================

class UpdateUserAvatarRequest(BaseModel):
    """
    Запрос на обновление аватарки пользователя.
    Пользователь выбирает из предустановленных.
    """
    image_id: uuid.UUID = Field(description="ID предустановленной аватарки")


class UploadImageRequest(BaseModel):
    """
    Запрос на загрузку нового предустановленного изображения.
    (Для админ-панели в будущем)
    """
    entity_type: EntityType
    file_data: bytes
    mime_type: str = Field(pattern=r"^image/(jpeg|png|gif|webp)$")


# ===========================
# Error Schemas
# ===========================

class ErrorResponse(BaseModel):
    """Схема ошибки"""
    detail: str
