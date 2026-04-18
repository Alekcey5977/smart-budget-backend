from uuid import UUID

from app.models import Notification
from app.schemas import NotificationCreate
from sqlalchemy import delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession


class NotificationRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_notification(self, notification_data: NotificationCreate):
        """Создание уведомления"""
        notification = Notification(
            user_id=notification_data.user_id, title=notification_data.title, body=notification_data.body
        )
        self.db.add(notification)
        await self.db.commit()
        await self.db.refresh(notification)
        return notification

    async def get_notifications_by_user(self, user_id: int, skip: int = 0, limit: int = 100):
        """Получение уведомлений пользователя"""
        result = await self.db.execute(
            select(Notification)
            .where(Notification.user_id == user_id)
            .order_by(Notification.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        return result.scalars().all()

    async def get_notification_by_id(self, notification_id: UUID):
        """Получение уведомления по ID"""
        result = await self.db.execute(select(Notification).where(Notification.id == notification_id))
        return result.scalar_one_or_none()

    async def get_unread_notifications_count(self, user_id: int):
        """Получение количества непрочитанных уведомлений"""
        result = await self.db.execute(
            select(func.count(Notification.id)).where(
                (Notification.user_id == user_id) & (~Notification.is_read)
            )
        )
        return result.scalar()

    async def mark_notification_as_read(self, notification_id: UUID, user_id: int):
        """Отметить уведомление как прочитанное"""
        stmt = (
            update(Notification)
            .where((Notification.id == notification_id) & (Notification.user_id == user_id))
            .values(is_read=True)
            .returning(Notification)
        )
        result = await self.db.execute(stmt)
        await self.db.commit()
        return result.scalar_one_or_none()

    async def mark_all_notifications_as_read(self, user_id: int):
        """Отметить все уведомления пользователя как прочитанные"""
        stmt = update(Notification).where(
            Notification.user_id == user_id).values(is_read=True)
        result = await self.db.execute(stmt)
        await self.db.commit()
        return result.rowcount

    async def delete_notification(self, notification_id: UUID, user_id: int):
        """Удаление уведомления"""
        stmt = delete(Notification).where(
            (Notification.id == notification_id) & (Notification.user_id == user_id))
        result = await self.db.execute(stmt)
        await self.db.commit()
        return result.rowcount
