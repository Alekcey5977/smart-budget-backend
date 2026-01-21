import os
from typing import Any, Dict, List
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
import httpx

from app.dependencies import get_current_user
from app.schemas.purpose_schema import PurposeCreate, PurposeResponse, PurposeUpdate


router = APIRouter(
    prefix="/purposes",
    tags=["purposes"]
)

PURPOSES_SERVICE_URL = os.getenv(
    "PURPOSES_SERVICE_URL",
    "http://purposes-service:8005"
)


@router.post(
    "/create",
    response_model=PurposeResponse,
    summary="Создать цель",
    description="""
Создать новую цель для текущего пользователя.

**Требует авторизации:** JWT токен в заголовке Authorization.

Gateway автоматически передает user_id в сервис через заголовок X-User-ID.

## Пример запроса
```json
{
    "title": "Отпуск в Турции",
    "deadline": "2026-07-01T00:00:00",
    "amount": 15000.00,
    "total_amount": 100000.00
}
```
""",
    responses={
        200: {"description": "Цель успешно создана"},
        401: {"description": "Не авторизован"},
        503: {"description": "Сервис целей недоступен"},
        504: {"description": "Таймаут сервиса целей"}
    }
)
async def create_purpose(
    purpose: PurposeCreate,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Проксирует запрос на создание цели к purposes-service.

    Gateway извлекает user_id из JWT токена и передает его в микросервис
    через заголовок X-User-ID для идентификации пользователя.
    """
    user_id = current_user["user_id"]

    async with httpx.AsyncClient() as client:
        try:
            headers = {"X-User-ID": str(user_id)}

            response = await client.post(
                f"{PURPOSES_SERVICE_URL}/purpose/create",
                headers=headers,
                json=purpose.model_dump(mode='json'),
                timeout=10.0
            )

            if response.status_code == 200:
                return response.json()

            error_detail = response.json().get("detail", "Failed to create purpose")
            raise HTTPException(
                status_code=response.status_code,
                detail=error_detail
            )

        except httpx.ConnectError:
            raise HTTPException(503, "Purposes service is unavailable")
        except httpx.TimeoutException:
            raise HTTPException(504, "Purposes service timeout")


@router.get(
    "/my",
    response_model=List[PurposeResponse],
    summary="Получить цели пользователя",
    description="""
Получить все цели, связанные с текущим пользователем.

**Требует авторизации:** JWT токен в заголовке Authorization.

Возвращает список всех целей пользователя с информацией о накопленных и целевых суммах.
""",
    responses={
        200: {
            "description": "Список целей пользователя",
            "content": {
                "application/json": {
                    "example": [
                        {
                            "id": "550e8400-e29b-41d4-a716-446655440000",
                            "user_id": 1,
                            "title": "Отпуск в Турции",
                            "deadline": "2026-07-01T00:00:00",
                            "amount": 15000.00,
                            "total_amount": 100000.00,
                            "created_at": "2026-01-15T10:30:00",
                            "updated_at": "2026-01-20T14:20:00"
                        }
                    ]
                }
            }
        },
        401: {"description": "Не авторизован"},
        503: {"description": "Сервис целей недоступен"}
    }
)
async def get_purposes_by_user(
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Проксирует запрос на получение целей к purposes-service.

    Получает все цели пользователя из микросервиса purposes-service.
    """
    user_id = current_user["user_id"]

    async with httpx.AsyncClient() as client:
        try:
            headers = {"X-User-ID": str(user_id)}

            response = await client.get(
                f"{PURPOSES_SERVICE_URL}/purpose/my",
                headers=headers,
                timeout=10.0
            )

            if response.status_code == 200:
                return response.json()

            error_detail = response.json().get("detail", "Failed to get purposes")
            raise HTTPException(
                status_code=response.status_code,
                detail=error_detail
            )

        except httpx.ConnectError:
            raise HTTPException(503, "Purposes service is unavailable")
        except httpx.TimeoutException:
            raise HTTPException(504, "Purposes service timeout")


@router.put(
    "/update/{purpose_id}",
    response_model=PurposeResponse,
    summary="Обновить цель",
    description="""
Обновить существующую цель пользователя.

**Требует авторизации:** JWT токен в заголовке Authorization.

Можно обновить любое поле: название, дедлайн, накопленную сумму или целевую сумму.
Передавайте только те поля, которые нужно обновить.

## Пример запроса
```json
{
    "title": "Отпуск в Греции",
    "amount": 25000.00
}
```
""",
    responses={
        200: {"description": "Цель успешно обновлена"},
        400: {"description": "Нет полей для обновления"},
        401: {"description": "Не авторизован"},
        404: {"description": "Цель не найдена"},
        503: {"description": "Сервис целей недоступен"}
    }
)
async def update_purpose(
    purpose_id: UUID,
    purpose_update: PurposeUpdate,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Проксирует запрос на обновление цели к purposes-service.

    Purposes-service проверит, что цель принадлежит пользователю перед обновлением.
    """
    user_id = current_user["user_id"]

    async with httpx.AsyncClient() as client:
        try:
            headers = {"X-User-ID": str(user_id)}

            response = await client.put(
                f"{PURPOSES_SERVICE_URL}/purpose/update/{purpose_id}",
                headers=headers,
                json=purpose_update.model_dump(exclude_none=True, mode='json'),
                timeout=10.0
            )

            if response.status_code == 200:
                return response.json()

            error_detail = response.json().get("detail", "Failed to update purpose")
            raise HTTPException(
                status_code=response.status_code,
                detail=error_detail
            )

        except httpx.ConnectError:
            raise HTTPException(503, "Purposes service is unavailable")
        except httpx.TimeoutException:
            raise HTTPException(504, "Purposes service timeout")


@router.delete(
    "/delete/{purpose_id}",
    summary="Удалить цель",
    description="""
Удалить существующую цель пользователя.

**Требует авторизации:** JWT токен в заголовке Authorization.

Purposes-service проверит, что цель принадлежит пользователю перед удалением.
""",
    responses={
        200: {"description": "Цель успешно удалена"},
        401: {"description": "Не авторизован"},
        404: {"description": "Цель не найдена или доступ запрещен"},
        503: {"description": "Сервис целей недоступен"}
    }
)
async def delete_purpose(
    purpose_id: UUID,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Проксирует запрос на удаление цели к purposes-service.

    Purposes-service проверит, что цель принадлежит пользователю перед удалением.
    """
    user_id = current_user["user_id"]

    async with httpx.AsyncClient() as client:
        try:
            headers = {"X-User-ID": str(user_id)}

            response = await client.delete(
                f"{PURPOSES_SERVICE_URL}/purpose/delete/{purpose_id}",
                headers=headers,
                timeout=10.0
            )

            if response.status_code == 200:
                return response.json()

            error_detail = response.json().get("detail", "Failed to delete purpose")
            raise HTTPException(
                status_code=response.status_code,
                detail=error_detail
            )

        except httpx.ConnectError:
            raise HTTPException(503, "Purposes service is unavailable")
        except httpx.TimeoutException:
            raise HTTPException(504, "Purposes service timeout")
