import os
from typing import Any, Dict

import httpx
from app.dependencies import get_current_user
from fastapi import APIRouter, Depends, HTTPException, Response

router = APIRouter(prefix="/images", tags=["images"])

IMAGES_SERVICE_URL = os.getenv("IMAGES_SERVICE_URL", "http://images-service:8003")


@router.get(
    "/avatars/default",
    summary="Получить предустановленные аватарки",
    description="""
Получить список всех предустановленных аватарок для выбора.

**Публичный эндпоинт** - не требует авторизации.
""",
    responses={
        200: {"description": "Список предустановленных аватарок"},
        503: {"description": "Сервис изображений недоступен"},
    },
)
async def get_default_avatars():
    """
    Получить все предустановленные аватарки.

    Проксирует запрос к images-service.
    """
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(f"{IMAGES_SERVICE_URL}/images/avatars/default", timeout=10.0)

            if response.status_code == 200:
                return response.json()

            error_detail = response.json().get("detail", "Failed to get default avatars")
            raise HTTPException(status_code=response.status_code, detail=error_detail)

        except httpx.ConnectError:
            raise HTTPException(503, "Images service is unavailable")
        except httpx.TimeoutException:
            raise HTTPException(504, "Images service timeout")


@router.get(
    "/avatars/me",
    summary="Получить аватарку текущего пользователя",
    description="""
Получить метаданные аватарки текущего пользователя.

**Требует авторизации:** JWT токен в заголовке Authorization.
""",
    responses={
        200: {"description": "Метаданные аватарки пользователя"},
        401: {"description": "Не авторизован"},
        404: {"description": "Аватарка не найдена"},
        503: {"description": "Сервис изображений недоступен"},
    },
)
async def get_my_avatar(current_user: Dict[str, Any] = Depends(get_current_user)):
    """
    Получить аватарку текущего пользователя.

    Проверяет JWT токен и проксирует запрос к images-service.
    """
    user_id = current_user["user_id"]

    async with httpx.AsyncClient() as client:
        try:
            headers = {"X-User-ID": str(user_id)}

            response = await client.get(f"{IMAGES_SERVICE_URL}/images/avatars/me", headers=headers, timeout=10.0)

            if response.status_code == 200:
                return response.json()

            error_detail = response.json().get("detail", "Failed to get user avatar")
            raise HTTPException(status_code=response.status_code, detail=error_detail)

        except httpx.ConnectError:
            raise HTTPException(503, "Images service is unavailable")
        except httpx.TimeoutException:
            raise HTTPException(504, "Images service timeout")


@router.put(
    "/avatars/me",
    summary="Обновить аватарку пользователя",
    description="""
Обновить аватарку пользователя, выбрав одну из предустановленных.

**Требует авторизации:** JWT токен в заголовке Authorization.

Пример тела запроса:
```json
{
    "image_id": "550e8400-e29b-41d4-a716-446655440000"
}
```
""",
    responses={
        200: {"description": "Аватарка успешно обновлена"},
        400: {"description": "Невалидный ID аватарки"},
        401: {"description": "Не авторизован"},
        404: {"description": "Аватарка не найдена"},
        503: {"description": "Сервис изображений недоступен"},
    },
)
async def update_my_avatar(request: Dict[str, Any], current_user: Dict[str, Any] = Depends(get_current_user)):
    """
    Обновить аватарку пользователя.

    Проверяет JWT токен и проксирует запрос к images-service.
    """
    user_id = current_user["user_id"]

    async with httpx.AsyncClient() as client:
        try:
            headers = {"X-User-ID": str(user_id)}

            response = await client.put(
                f"{IMAGES_SERVICE_URL}/images/avatars/me", headers=headers, json=request, timeout=10.0
            )

            if response.status_code == 200:
                return response.json()

            error_detail = response.json().get("detail", "Failed to update user avatar")
            raise HTTPException(status_code=response.status_code, detail=error_detail)

        except httpx.ConnectError:
            raise HTTPException(503, "Images service is unavailable")
        except httpx.TimeoutException:
            raise HTTPException(504, "Images service timeout")


@router.get(
    "/{image_id}",
    summary="Получить изображение по ID",
    description="""
Получить бинарные данные изображения по его ID.

**Публичный эндпоинт** - не требует авторизации.

Возвращает изображение в оригинальном формате с правильным Content-Type.
""",
    responses={
        200: {"description": "Изображение"},
        404: {"description": "Изображение не найдено"},
        503: {"description": "Сервис изображений недоступен"},
    },
)
async def get_image(image_id: str):
    """
    Получить изображение по ID.

    Проксирует запрос к images-service.
    """
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(
                f"{IMAGES_SERVICE_URL}/images/{image_id}",
                timeout=30.0,  # Больше таймаут для загрузки изображений
            )

            if response.status_code == 200:
                # Возвращаем изображение с правильными заголовками
                return Response(
                    content=response.content,
                    media_type=response.headers.get("content-type", "image/jpeg"),
                    headers={
                        "Cache-Control": response.headers.get("cache-control", "public, max-age=31536000"),
                        "Content-Length": response.headers.get("content-length", str(len(response.content))),
                    },
                )

            error_detail = response.json().get("detail", "Image not found")
            raise HTTPException(status_code=response.status_code, detail=error_detail)

        except httpx.ConnectError:
            raise HTTPException(503, "Images service is unavailable")
        except httpx.TimeoutException:
            raise HTTPException(504, "Images service timeout")


@router.get(
    "/mappings/categories",
    summary="Получить маппинг категорий к изображениям",
    description="""
Получить маппинг ID категорий к ID изображений для кэширования на фронтенде.

**Публичный эндпоинт** - не требует авторизации.
""",
    responses={
        200: {"description": "Маппинг категорий к изображениям"},
        503: {"description": "Сервис изображений недоступен"},
    },
)
async def get_categories_mapping():
    """
    Получить маппинг категорий к изображениям.

    Проксирует запрос к images-service.
    """
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(f"{IMAGES_SERVICE_URL}/images/mappings/categories", timeout=10.0)

            if response.status_code == 200:
                return response.json()

            error_detail = response.json().get("detail", "Failed to get categories mapping")
            raise HTTPException(status_code=response.status_code, detail=error_detail)

        except httpx.ConnectError:
            raise HTTPException(503, "Images service is unavailable")
        except httpx.TimeoutException:
            raise HTTPException(504, "Images service timeout")


@router.get(
    "/mappings/merchants",
    summary="Получить маппинг мерчантов к изображениям",
    description="""
Получить маппинг ID мерчантов к ID изображений для кэширования на фронтенде.

**Публичный эндпоинт** - не требует авторизации.
""",
    responses={
        200: {"description": "Маппинг мерчантов к изображениям"},
        503: {"description": "Сервис изображений недоступен"},
    },
)
async def get_merchants_mapping():
    """
    Получить маппинг мерчантов к изображениям.

    Проксирует запрос к images-service.
    """
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(f"{IMAGES_SERVICE_URL}/images/mappings/merchants", timeout=10.0)

            if response.status_code == 200:
                return response.json()

            error_detail = response.json().get("detail", "Failed to get merchants mapping")
            raise HTTPException(status_code=response.status_code, detail=error_detail)

        except httpx.ConnectError:
            raise HTTPException(503, "Images service is unavailable")
        except httpx.TimeoutException:
            raise HTTPException(504, "Images service timeout")
