import os
from typing import Any, Dict, List
from uuid import UUID

import httpx
from app.dependencies import get_current_user
from app.schemas.history_schema import DeleteResponse, HistoryEntryResponse
from fastapi import APIRouter, Depends, HTTPException, Query

router = APIRouter(prefix="/history", tags=["history"])

HISTORY_SERVICE_URL = os.getenv("HISTORY_SERVICE_URL", "http://history-service:8007")


@router.get(
    "/user/me",
    response_model=List[HistoryEntryResponse],
    summary="Получить историю действий пользователя",
    description="""
Получить список записей истории текущего авторизованного пользователя с поддержкой пагинации.

**Требует авторизации:** JWT токен в заголовке Authorization.

Gateway автоматически передаёт user_id в сервис через заголовок X-User-ID.

## Параметры пагинации
- `skip`: Пропустить N первых записей (по умолчанию 0)
- `limit`: Максимальное количество возвращаемых записей (по умолчанию 20, макс 100)

Записи возвращаются отсортированными от новых к старым (по дате создания).

## Источник записей
Записи создаются автоматически при наступлении доменных событий:
- Создание / изменение / удаление цели
- Добавление / удаление банковского счёта
- Изменение профиля или аватара пользователя

## Примеры использования пагинации
- Первая страница (20 записей): `skip=0&limit=20`
- Вторая страница (20 записей): `skip=20&limit=20`
""",
    responses={
        200: {
            "description": "Список записей истории пользователя",
            "content": {
                "application/json": {
                    "example": [
                        {
                            "id": "550e8400-e29b-41d4-a716-446655440000",
                            "user_id": 1,
                            "title": "Цель создана",
                            "body": "Цель «Отпуск в Турции» на сумму 150000 руб. создана",
                            "created_at": "2026-01-21T10:30:00",
                        },
                        {
                            "id": "660f9511-f30c-52e5-b827-55766541b001",
                            "user_id": 1,
                            "title": "Банковский счёт добавлен",
                            "body": "Добавлен счёт «Сбербанк» с балансом 50000 руб.",
                            "created_at": "2026-01-20T15:20:00",
                        },
                    ]
                }
            },
        },
        401: {"description": "Не авторизован"},
        503: {"description": "Сервис истории недоступен"},
        504: {"description": "Таймаут сервиса истории"},
    },
)
async def get_user_history(
    skip: int = Query(0, ge=0, description="Пропустить N записей (для пагинации)"),
    limit: int = Query(20, ge=1, le=100, description="Максимум записей на страницу"),
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """Проксирует запрос на получение истории к history-service."""
    user_id = current_user["user_id"]

    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(
                f"{HISTORY_SERVICE_URL}/history/user/me",
                headers={"X-User-ID": str(user_id)},
                params={"skip": skip, "limit": limit},
                timeout=10.0,
            )

            if response.status_code == 200:
                return response.json()

            error_detail = response.json().get("detail", "Failed to get history")
            raise HTTPException(status_code=response.status_code, detail=error_detail)

        except httpx.ConnectError:
            raise HTTPException(503, "History service is unavailable")
        except httpx.TimeoutException:
            raise HTTPException(504, "History service timeout")


@router.get(
    "/{entry_id}",
    response_model=HistoryEntryResponse,
    summary="Получить запись истории по ID",
    description="""
Получить конкретную запись истории по её UUID.

**Требует авторизации:** JWT токен в заголовке Authorization.

Если запись с указанным ID не найдена, возвращается ошибка 404.
""",
    responses={
        200: {
            "description": "Данные записи истории",
            "content": {
                "application/json": {
                    "example": {
                        "id": "550e8400-e29b-41d4-a716-446655440000",
                        "user_id": 1,
                        "title": "Цель создана",
                        "body": "Цель «Отпуск в Турции» на сумму 150000 руб. создана",
                        "created_at": "2026-01-21T10:30:00",
                    }
                }
            },
        },
        401: {"description": "Не авторизован"},
        404: {"description": "Запись истории не найдена"},
        503: {"description": "Сервис истории недоступен"},
        504: {"description": "Таймаут сервиса истории"},
    },
)
async def get_history_entry(entry_id: UUID, current_user: Dict[str, Any] = Depends(get_current_user)):
    """Проксирует запрос на получение записи истории к history-service."""
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(f"{HISTORY_SERVICE_URL}/history/{entry_id}", timeout=10.0)

            if response.status_code == 200:
                return response.json()

            if response.status_code == 404:
                raise HTTPException(404, "History entry not found")

            error_detail = response.json().get("detail", "Failed to get history entry")
            raise HTTPException(status_code=response.status_code, detail=error_detail)

        except httpx.ConnectError:
            raise HTTPException(503, "History service is unavailable")
        except httpx.TimeoutException:
            raise HTTPException(504, "History service timeout")


@router.delete(
    "/{entry_id}",
    response_model=DeleteResponse,
    summary="Удалить запись истории",
    description="""
Удалить конкретную запись истории.

**Требует авторизации:** JWT токен в заголовке Authorization.

**Безопасность через X-User-ID:** History-service проверит, что запись принадлежит текущему пользователю перед удалением.
Невозможно удалить чужую запись истории.

Если запись не найдена или принадлежит другому пользователю, возвращается ошибка 404.
""",
    responses={
        200: {
            "description": "Запись успешно удалена",
            "content": {"application/json": {"example": {"status": "success", "message": "History entry deleted"}}},
        },
        401: {"description": "Не авторизован"},
        404: {"description": "Запись не найдена или доступ запрещён"},
        503: {"description": "Сервис истории недоступен"},
        504: {"description": "Таймаут сервиса истории"},
    },
)
async def delete_history_entry(entry_id: UUID, current_user: Dict[str, Any] = Depends(get_current_user)):
    """Проксирует запрос на удаление записи истории к history-service."""
    user_id = current_user["user_id"]

    async with httpx.AsyncClient() as client:
        try:
            response = await client.delete(
                f"{HISTORY_SERVICE_URL}/history/{entry_id}", headers={"X-User-ID": str(user_id)}, timeout=10.0
            )

            if response.status_code == 200:
                return response.json()

            if response.status_code == 404:
                raise HTTPException(404, "History entry not found or access denied")

            error_detail = response.json().get("detail", "Failed to delete history entry")
            raise HTTPException(status_code=response.status_code, detail=error_detail)

        except httpx.ConnectError:
            raise HTTPException(503, "History service is unavailable")
        except httpx.TimeoutException:
            raise HTTPException(504, "History service timeout")
