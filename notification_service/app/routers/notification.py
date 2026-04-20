from typing import List
from uuid import UUID

from app.database import get_db
from app.dependencies import get_user_id_from_header
from app.repository.notification_repository import NotificationRepository
from app.schemas import NotificationResponse
from fastapi import APIRouter, Depends, HTTPException
from fastapi.encoders import jsonable_encoder
from sqlalchemy.ext.asyncio import AsyncSession

from shared.cache import cache_client

router = APIRouter(prefix="/notifications", tags=["notifications"])

_NOTIFICATIONS_TTL = 30


async def get_notification_repository(db: AsyncSession = Depends(get_db)):
    return NotificationRepository(db)


@router.get("/user/me", response_model=List[NotificationResponse])
async def get_notifications_by_user(
    user_id: int = Depends(get_user_id_from_header),
    skip: int = 0,
    limit: int = 100,
    repo: NotificationRepository = Depends(get_notification_repository),
):
    """Получение уведомлений пользователя"""
    cache_key = f"notifications:{user_id}:{skip}:{limit}"
    try:
        cached = await cache_client.get(cache_key)
        if cached is not None:
            return cached
    except Exception:
        pass

    notifications = await repo.get_notifications_by_user(user_id, skip, limit)
    result = jsonable_encoder(notifications)

    try:
        await cache_client.set(cache_key, result, ttl=_NOTIFICATIONS_TTL)
    except Exception:
        pass

    return result


@router.get("/user/me/unread/count")
async def get_unread_notifications_count(
    user_id: int = Depends(get_user_id_from_header),
    repo: NotificationRepository = Depends(get_notification_repository),
):
    """Получение количества непрочитанных уведомлений пользователя"""
    count = await repo.get_unread_notifications_count(user_id)
    return {"count": count}


@router.get("/{notification_id}", response_model=NotificationResponse)
async def get_notification(
    notification_id: UUID, repo: NotificationRepository = Depends(get_notification_repository)
):
    """Получение уведомления по ID"""
    notification = await repo.get_notification_by_id(notification_id)
    if not notification:
        raise HTTPException(status_code=404, detail="Notification not found")
    return notification


@router.post("/{notification_id}/mark-as-read")
async def mark_notification_as_read(
    notification_id: UUID,
    user_id: int = Depends(get_user_id_from_header),
    repo: NotificationRepository = Depends(get_notification_repository),
):
    """Отметить уведомление как прочитанное"""
    notification = await repo.mark_notification_as_read(notification_id, user_id)
    if not notification:
        raise HTTPException(status_code=404, detail="Notification not found or access denied")

    try:
        await cache_client.delete_pattern(f"notifications:{user_id}:*")
    except Exception:
        pass

    return {"status": "success", "message": "Notification marked as read"}


@router.post("/mark-all-as-read")
async def mark_all_notifications_as_read(
    user_id: int = Depends(get_user_id_from_header),
    repo: NotificationRepository = Depends(get_notification_repository),
):
    """Отметить все уведомления пользователя как прочитанными"""
    await repo.mark_all_notifications_as_read(user_id)

    try:
        await cache_client.delete_pattern(f"notifications:{user_id}:*")
    except Exception:
        pass

    return {"status": "success", "message": "All notifications marked as read"}


@router.delete("/{notification_id}")
async def delete_notification(
    notification_id: UUID,
    user_id: int = Depends(get_user_id_from_header),
    repo: NotificationRepository = Depends(get_notification_repository),
):
    """Удаление уведомления"""
    rowcount = await repo.delete_notification(notification_id, user_id)
    if rowcount == 0:
        raise HTTPException(status_code=404, detail="Notification not found or access denied")

    try:
        await cache_client.delete_pattern(f"notifications:{user_id}:*")
    except Exception:
        pass

    return {"status": "success", "message": "Notification deleted"}
