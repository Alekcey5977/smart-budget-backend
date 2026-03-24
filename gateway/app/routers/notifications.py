import os
from typing import Any, Dict, List
from uuid import UUID

import httpx
from app.dependencies import get_current_user
from app.schemas.notification_schema import MarkAsReadResponse, NotificationResponse, UnreadCountResponse
from fastapi import APIRouter, Depends, HTTPException, Query

router = APIRouter(
    prefix="/notifications",
    tags=["notifications"]
)

NOTIFICATION_SERVICE_URL = os.getenv(
    "NOTIFICATION_SERVICE_URL",
    "http://notification-service:8006"
)


@router.get(
    "/user/me",
    response_model=List[NotificationResponse],
    summary="Получить уведомления пользователя",
    description="""
Получить список уведомлений текущего авторизованного пользователя с поддержкой пагинации.

**Требует авторизации:** JWT токен в заголовке Authorization.

Gateway автоматически передает user_id в сервис через заголовок X-User-ID.

## Параметры пагинации
- `skip`: Пропустить N первых записей (по умолчанию 0)
- `limit`: Максимальное количество возвращаемых записей (по умолчанию 20, макс 100)

Уведомления возвращаются отсортированными от новых к старым (по дате создания).

## Примеры использования пагинации
- Первая страница (20 записей): `skip=0&limit=20`
- Вторая страница (20 записей): `skip=20&limit=20`
- Третья страница (20 записей): `skip=40&limit=20`
""",
    responses={
        200: {
            "description": "Список уведомлений пользователя",
            "content": {
                "application/json": {
                    "example": [
                        {
                            "id": "550e8400-e29b-41d4-a716-446655440000",
                            "user_id": 1,
                            "title": "Новая цель создана",
                            "body": "Вы успешно создали цель 'Отпуск в Турции'",
                            "is_read": False,
                            "created_at": "2026-01-21T10:30:00"
                        },
                        {
                            "id": "660f9511-f30c-52e5-b827-55766541b001",
                            "user_id": 1,
                            "title": "Добро пожаловать!",
                            "body": "Ваш аккаунт успешно создан",
                            "is_read": True,
                            "created_at": "2026-01-20T15:20:00"
                        }
                    ]
                }
            }
        },
        401: {"description": "Не авторизован"},
        503: {"description": "Сервис уведомлений недоступен"}
    }
)
async def get_user_notifications(
    skip: int = Query(0, ge=0, description="Пропустить N записей (для пагинации)"),
    limit: int = Query(20, ge=1, le=100, description="Максимум записей на страницу"),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Проксирует запрос на получение уведомлений к notification-service.

    Получает все уведомления пользователя с поддержкой пагинации.
    Сортировка: от новых к старым (created_at DESC).
    """
    user_id = current_user["user_id"]

    async with httpx.AsyncClient() as client:
        try:
            headers = {"X-User-ID": str(user_id)}

            response = await client.get(
                f"{NOTIFICATION_SERVICE_URL}/notifications/user/me",
                headers=headers,
                params={"skip": skip, "limit": limit},
                timeout=10.0
            )

            if response.status_code == 200:
                return response.json()

            error_detail = response.json().get("detail", "Failed to get notifications")
            raise HTTPException(
                status_code=response.status_code,
                detail=error_detail
            )

        except httpx.ConnectError:
            raise HTTPException(503, "Notification service is unavailable")
        except httpx.TimeoutException:
            raise HTTPException(504, "Notification service timeout")


@router.get(
    "/user/me/unread/count",
    response_model=UnreadCountResponse,
    summary="Получить количество непрочитанных уведомлений",
    description="""
Получить количество непрочитанных уведомлений текущего пользователя.

**Требует авторизации:** JWT токен в заголовке Authorization.

Полезно для отображения бейджа с количеством непрочитанных уведомлений в UI.
Возвращает только количество уведомлений с `is_read = false`.
""",
    responses={
        200: {
            "description": "Количество непрочитанных уведомлений",
            "content": {
                "application/json": {
                    "example": {"count": 5}
                }
            }
        },
        401: {"description": "Не авторизован"},
        503: {"description": "Сервис уведомлений недоступен"}
    }
)
async def get_unread_count(
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Проксирует запрос на получение количества непрочитанных уведомлений.

    Notification-service подсчитывает все уведомления с is_read=False для данного пользователя.
    """
    user_id = current_user["user_id"]

    async with httpx.AsyncClient() as client:
        try:
            headers = {"X-User-ID": str(user_id)}

            response = await client.get(
                f"{NOTIFICATION_SERVICE_URL}/notifications/user/me/unread/count",
                headers=headers,
                timeout=10.0
            )

            if response.status_code == 200:
                return response.json()

            error_detail = response.json().get("detail", "Failed to get unread count")
            raise HTTPException(
                status_code=response.status_code,
                detail=error_detail
            )

        except httpx.ConnectError:
            raise HTTPException(503, "Notification service is unavailable")
        except httpx.TimeoutException:
            raise HTTPException(504, "Notification service timeout")


@router.get(
    "/{notification_id}",
    response_model=NotificationResponse,
    summary="Получить уведомление по ID",
    description="""
Получить конкретное уведомление по его UUID.

**Требует авторизации:** JWT токен в заголовке Authorization.

**Важно:** Не проверяет, принадлежит ли уведомление текущему пользователю.
Для безопасности используйте эндпоинт `/user/me` для получения только своих уведомлений.
""",
    responses={
        200: {"description": "Данные уведомления"},
        401: {"description": "Не авторизован"},
        404: {"description": "Уведомление не найдено"},
        503: {"description": "Сервис уведомлений недоступен"}
    }
)
async def get_notification_by_id(
    notification_id: UUID,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Проксирует запрос на получение уведомления по ID к notification-service.

    Возвращает полную информацию об уведомлении.
    """
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(
                f"{NOTIFICATION_SERVICE_URL}/notifications/{notification_id}",
                timeout=10.0
            )

            if response.status_code == 200:
                return response.json()

            if response.status_code == 404:
                raise HTTPException(404, "Notification not found")

            error_detail = response.json().get("detail", "Failed to get notification")
            raise HTTPException(
                status_code=response.status_code,
                detail=error_detail
            )

        except httpx.ConnectError:
            raise HTTPException(503, "Notification service is unavailable")
        except httpx.TimeoutException:
            raise HTTPException(504, "Notification service timeout")


@router.post(
    "/{notification_id}/mark-as-read",
    response_model=MarkAsReadResponse,
    summary="Отметить уведомление как прочитанное",
    description="""
Отметить конкретное уведомление как прочитанное.

**Требует авторизации:** JWT токен в заголовке Authorization.

**Безопасность через X-User-ID:** Notification-service проверит, что уведомление принадлежит текущему пользователю перед обновлением.
Если уведомление не найдено или не принадлежит пользователю, вернется ошибка 404.

После успешного выполнения, поле `is_read` уведомления будет установлено в `true`.
""",
    responses={
        200: {
            "description": "Уведомление отмечено как прочитанное",
            "content": {
                "application/json": {
                    "example": {
                        "status": "success",
                        "message": "Notification marked as read"
                    }
                }
            }
        },
        401: {"description": "Не авторизован"},
        404: {"description": "Уведомление не найдено или доступ запрещен"},
        503: {"description": "Сервис уведомлений недоступен"}
    }
)
async def mark_as_read(
    notification_id: UUID,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Проксирует запрос на отметку уведомления как прочитанного.

    Notification-service обновит поле is_read=True для данного уведомления.
    Проверяет владельца перед обновлением через X-User-ID.
    """
    user_id = current_user["user_id"]

    async with httpx.AsyncClient() as client:
        try:
            headers = {"X-User-ID": str(user_id)}

            response = await client.post(
                f"{NOTIFICATION_SERVICE_URL}/notifications/{notification_id}/mark-as-read",
                headers=headers,
                timeout=10.0
            )

            if response.status_code == 200:
                return response.json()

            if response.status_code == 404:
                raise HTTPException(404, "Notification not found or access denied")

            error_detail = response.json().get("detail", "Failed to mark notification as read")
            raise HTTPException(
                status_code=response.status_code,
                detail=error_detail
            )

        except httpx.ConnectError:
            raise HTTPException(503, "Notification service is unavailable")
        except httpx.TimeoutException:
            raise HTTPException(504, "Notification service timeout")


@router.post(
    "/mark-all-as-read",
    response_model=MarkAsReadResponse,
    summary="Отметить все уведомления как прочитанные",
    description="""
Отметить все уведомления текущего пользователя как прочитанные одним запросом.

**Требует авторизации:** JWT токен в заголовке Authorization.

**Безопасность через X-User-ID:** Обновляются только уведомления текущего пользователя.

Полезно для функции "Отметить всё как прочитанное" в UI.
Обновляет `is_read=True` для всех уведомлений пользователя.

После выполнения, счетчик непрочитанных уведомлений станет равным 0.
""",
    responses={
        200: {
            "description": "Все уведомления отмечены как прочитанные",
            "content": {
                "application/json": {
                    "example": {
                        "status": "success",
                        "message": "All notifications marked as read"
                    }
                }
            }
        },
        401: {"description": "Не авторизован"},
        503: {"description": "Сервис уведомлений недоступен"}
    }
)
async def mark_all_as_read(
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Проксирует запрос на отметку всех уведомлений как прочитанных.

    Notification-service обновит все уведомления пользователя.
    Безопасность через X-User-ID - обновляются только уведомления текущего пользователя.
    """
    user_id = current_user["user_id"]

    async with httpx.AsyncClient() as client:
        try:
            headers = {"X-User-ID": str(user_id)}

            response = await client.post(
                f"{NOTIFICATION_SERVICE_URL}/notifications/mark-all-as-read",
                headers=headers,
                timeout=10.0
            )

            if response.status_code == 200:
                return response.json()

            error_detail = response.json().get("detail", "Failed to mark all notifications as read")
            raise HTTPException(
                status_code=response.status_code,
                detail=error_detail
            )

        except httpx.ConnectError:
            raise HTTPException(503, "Notification service is unavailable")
        except httpx.TimeoutException:
            raise HTTPException(504, "Notification service timeout")


@router.delete(
    "/{notification_id}",
    response_model=MarkAsReadResponse,
    summary="Удалить уведомление",
    description="""
Удалить конкретное уведомление.

**Требует авторизации:** JWT токен в заголовке Authorization.

**Безопасность через X-User-ID:** Notification-service проверит, что уведомление принадлежит текущему пользователю перед удалением.
Невозможно удалить чужое уведомление.

Если уведомление не найдено или не принадлежит пользователю, вернется ошибка 404.
""",
    responses={
        200: {
            "description": "Уведомление успешно удалено",
            "content": {
                "application/json": {
                    "example": {
                        "status": "success",
                        "message": "Notification deleted"
                    }
                }
            }
        },
        401: {"description": "Не авторизован"},
        404: {"description": "Уведомление не найдено или доступ запрещен"},
        503: {"description": "Сервис уведомлений недоступен"}
    }
)
async def delete_notification(
    notification_id: UUID,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Проксирует запрос на удаление уведомления к notification-service.

    Notification-service проверит владельца через X-User-ID перед удалением.
    Безопасность: невозможно удалить чужое уведомление.
    """
    user_id = current_user["user_id"]

    async with httpx.AsyncClient() as client:
        try:
            headers = {"X-User-ID": str(user_id)}

            response = await client.delete(
                f"{NOTIFICATION_SERVICE_URL}/notifications/{notification_id}",
                headers=headers,
                timeout=10.0
            )

            if response.status_code == 200:
                return response.json()

            if response.status_code == 404:
                raise HTTPException(404, "Notification not found or access denied")

            error_detail = response.json().get("detail", "Failed to delete notification")
            raise HTTPException(
                status_code=response.status_code,
                detail=error_detail
            )

        except httpx.ConnectError:
            raise HTTPException(503, "Notification service is unavailable")
        except httpx.TimeoutException:
            raise HTTPException(504, "Notification service timeout")
