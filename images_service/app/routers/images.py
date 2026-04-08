import uuid
from typing import List

from app.cache import (
    CATEGORIES_MAP_KEY,
    CATEGORIES_MAP_TTL,
    DEFAULT_AVATARS_KEY,
    DEFAULT_AVATARS_TTL,
    MERCHANTS_MAP_KEY,
    MERCHANTS_MAP_TTL,
    cache_client,
)
from app.database import get_db
from app.dependencies import get_user_id_from_header
from app.models import EntityType
from app.repository.image_repository import ImageRepository
from app.schemas import ErrorResponse, ImageMappingItem, ImageMappingResponse, ImageMetadata, UpdateUserAvatarRequest
from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/images", tags=["images"])


@router.get(
    "/avatars/default",
    response_model=List[ImageMetadata],
    summary="Получить предустановленные аватарки",
    description="""
Получить список всех предустановленных аватарок для выбора пользователем.

**Публичный эндпоинт** - не требует авторизации.

Возвращает метаданные без бинарных данных для быстрой загрузки списка.
Для получения самого изображения используйте GET /images/{image_id}
""",
    responses={
        200: {
            "description": "Список предустановленных аватарок",
        },
        500: {"description": "Ошибка сервера", "model": ErrorResponse},
    },
)
async def get_default_avatars(db: AsyncSession = Depends(get_db)):
    """
    Получить все предустановленные аватарки.

    Возвращает метаданные изображений (без file_data) для оптимизации.
    """
    # Cache-Aside: пробуем получить из кэша
    cached = await cache_client.get(DEFAULT_AVATARS_KEY)
    if cached is not None:
        return cached

    try:
        repo = ImageRepository(db)
        avatars = await repo.get_default_avatars()

        # Возвращаем только метаданные без бинарных данных
        result = [ImageMetadata.model_validate(avatar) for avatar in avatars]

        # Сохраняем в кэш
        await cache_client.set(DEFAULT_AVATARS_KEY, result, ttl=DEFAULT_AVATARS_TTL)

        return result

    except Exception as e:
        raise HTTPException(500, f"Internal server error: {str(e)}")


@router.get(
    "/avatars/me",
    response_model=ImageMetadata,
    summary="Получить аватарку текущего пользователя",
    description="""
Получить метаданные аватарки текущего пользователя.

**Требует авторизации:** Gateway прокидывает X-User-ID.

Возвращает None (404), если пользователь не выбрал аватарку.
""",
    responses={
        200: {"description": "Метаданные аватарки пользователя"},
        404: {"description": "Аватарка не найдена", "model": ErrorResponse},
        500: {"description": "Ошибка сервера", "model": ErrorResponse},
    },
)
async def get_my_avatar(user_id: int = Depends(get_user_id_from_header), db: AsyncSession = Depends(get_db)):
    """
    Получить аватарку текущего пользователя.
    """
    try:
        repo = ImageRepository(db)
        avatar = await repo.get_user_avatar(user_id)

        if not avatar:
            raise HTTPException(404, "User avatar not found")

        return ImageMetadata.model_validate(avatar)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"Internal server error: {str(e)}")


@router.put(
    "/avatars/me",
    response_model=ImageMetadata,
    summary="Обновить аватарку пользователя",
    description="""
Обновить аватарку пользователя, выбрав одну из предустановленных.

**Требует авторизации:** Gateway прокидывает X-User-ID.

Пользователь может выбрать только из предустановленных аватарок,
полученных через GET /avatars/default.
""",
    responses={
        200: {"description": "Аватарка успешно обновлена"},
        400: {"description": "Невалидный ID аватарки", "model": ErrorResponse},
        404: {"description": "Аватарка не найдена", "model": ErrorResponse},
        500: {"description": "Ошибка сервера", "model": ErrorResponse},
    },
)
async def update_my_avatar(
    request: UpdateUserAvatarRequest,
    user_id: int = Depends(get_user_id_from_header),
    db: AsyncSession = Depends(get_db),
):
    """
    Обновить аватарку пользователя.

    Создает или обновляет привязку пользователя к выбранной аватарке.
    """
    try:
        repo = ImageRepository(db)
        avatar = await repo.update_user_avatar(user_id, request.image_id)

        return ImageMetadata.model_validate(avatar)

    except ValueError as e:
        raise HTTPException(400, str(e))
    except Exception as e:
        raise HTTPException(500, f"Internal server error: {str(e)}")


@router.get(
    "/images/{image_id}",
    summary="Получить изображение по ID",
    description="""
Получить бинарные данные изображения по его ID.

**Публичный эндпоинт** - не требует авторизации.

Возвращает изображение в оригинальном формате с правильным Content-Type.
Может использоваться напрямую в теге <img src="/images/{id}">
""",
    responses={
        200: {
            "description": "Изображение",
            "content": {"image/jpeg": {}, "image/png": {}, "image/gif": {}, "image/webp": {}},
        },
        404: {"description": "Изображение не найдено", "model": ErrorResponse},
        500: {"description": "Ошибка сервера", "model": ErrorResponse},
    },
)
async def get_image(image_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    """
    Получить изображение по ID.

    Возвращает бинарные данные с правильным Content-Type.
    """
    try:
        repo = ImageRepository(db)
        image = await repo.get_image_by_id(image_id)

        if not image:
            raise HTTPException(404, "Image not found")

        # Возвращаем изображение с правильным MIME-типом
        return Response(
            content=image.file_data,
            media_type=image.mime_type,
            headers={
                "Cache-Control": "public, max-age=31536000, immutable",  # Кэш на год
                "Content-Length": str(image.file_size),
            },
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"Internal server error: {str(e)}")


@router.get(
    "/mappings/categories",
    response_model=ImageMappingResponse,
    summary="Получить маппинг категорий к изображениям",
    description="""
Получить маппинг ID категорий к ID изображений для кэширования на фронтенде.

**Публичный эндпоинт** - не требует авторизации.

Фронтенд может закэшировать этот список и затем при получении транзакций
использовать category_id для получения соответствующего изображения из кэша.

Если у мерчанта нет своего изображения, используется изображение его категории.
""",
    responses={
        200: {"description": "Маппинг категорий к изображениям"},
        500: {"description": "Ошибка сервера", "model": ErrorResponse},
    },
)
async def get_categories_mapping(db: AsyncSession = Depends(get_db)):
    """
    Получить маппинг категорий к изображениям.

    Возвращает список пар (category_id, image_id, mime_type).
    """
    # Cache-Aside: пробуем получить из кэша
    cached = await cache_client.get(CATEGORIES_MAP_KEY)
    if cached is not None:
        return ImageMappingResponse(
            entity_type=EntityType.CATEGORY, mappings=[ImageMappingItem(**item) for item in cached]
        )

    try:
        repo = ImageRepository(db)
        mappings = await repo.get_category_images_mapping()

        result = ImageMappingResponse(
            entity_type=EntityType.CATEGORY,
            mappings=[
                ImageMappingItem(entity_id=entity_id, image_id=image_id, mime_type=mime_type)
                for entity_id, image_id, mime_type in mappings
            ],
        )

        # Сохраняем в кэш
        await cache_client.set(CATEGORIES_MAP_KEY, [m.model_dump() for m in result.mappings], ttl=CATEGORIES_MAP_TTL)

        return result

    except Exception as e:
        raise HTTPException(500, f"Internal server error: {str(e)}")


@router.get(
    "/mappings/merchants",
    response_model=ImageMappingResponse,
    summary="Получить маппинг мерчантов к изображениям",
    description="""
Получить маппинг ID мерчантов к ID изображений для кэширования на фронтенде.

**Публичный эндпоинт** - не требует авторизации.

Фронтенд может закэшировать этот список и затем при получении транзакций
использовать merchant_id для получения соответствующего изображения из кэша.

Приоритет: изображение мерчанта > изображение категории.
""",
    responses={
        200: {"description": "Маппинг мерчантов к изображениям"},
        500: {"description": "Ошибка сервера", "model": ErrorResponse},
    },
)
async def get_merchants_mapping(db: AsyncSession = Depends(get_db)):
    """
    Получить маппинг мерчантов к изображениям.

    Возвращает список пар (merchant_id, image_id, mime_type).
    """
    # Cache-Aside: пробуем получить из кэша
    cached = await cache_client.get(MERCHANTS_MAP_KEY)
    if cached is not None:
        return ImageMappingResponse(
            entity_type=EntityType.MERCHANT, mappings=[ImageMappingItem(**item) for item in cached]
        )

    try:
        repo = ImageRepository(db)
        mappings = await repo.get_merchant_images_mapping()

        result = ImageMappingResponse(
            entity_type=EntityType.MERCHANT,
            mappings=[
                ImageMappingItem(entity_id=entity_id, image_id=image_id, mime_type=mime_type)
                for entity_id, image_id, mime_type in mappings
            ],
        )

        # Сохраняем в кэш
        await cache_client.set(MERCHANTS_MAP_KEY, [m.model_dump() for m in result.mappings], ttl=MERCHANTS_MAP_TTL)

        return result

    except Exception as e:
        raise HTTPException(500, f"Internal server error: {str(e)}")
