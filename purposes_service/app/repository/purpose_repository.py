from datetime import datetime
from uuid import UUID, uuid4

from app.models import Purpose
from app.schemas import PurposeCreate
from app.utils import get_crossed_thresholds
from sqlalchemy import delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from shared.event_publisher import EventPublisher
from shared.event_schema import DomainEvent


class PurposeRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_purpose(
        self,
        user_id: int,
        purpose_data: PurposeCreate,
    ):
        """Создание целей"""
        purpose = Purpose(
            id=uuid4(),
            user_id=user_id,
            title=purpose_data.title,
            deadline=purpose_data.deadline,
            amount=0,  # При создании всегда 0
            total_amount=purpose_data.total_amount,
        )

        self.db.add(purpose)
        await self.db.commit()
        await self.db.refresh(purpose)

        # Публикуем событие о создании цели
        event_data_created = {
            "user_id": user_id,
            "purpose_id": str(purpose.id),
            "name": purpose.title,
            "target_amount": str(purpose.total_amount),
            "current_amount": str(purpose.amount),
            "deadline": purpose.deadline.isoformat(),
        }

        publisher = EventPublisher()
        event_created = DomainEvent(
            event_id=str(uuid4()),
            event_type="purpose.created",
            source="purposes-service",
            timestamp=datetime.now(),
            payload=event_data_created,
        )
        await publisher.publish(event_created)

        # При создании amount=0, поэтому пороги не пересекаются
        # (оставлено для совместимости, если amount будет задаваться при создании)
        crossed = get_crossed_thresholds(0, purpose.total_amount, purpose.amount, purpose.total_amount)
        for threshold in crossed:
            progress_percent = (purpose.amount / purpose.total_amount) * 100
            event_data_progress = {
                "user_id": user_id,
                "purpose_id": str(purpose.id),
                "purpose_name": purpose.title,
                "progress_percent": round(progress_percent, 2),
                "threshold": threshold,
            }
            publisher = EventPublisher()
            event_progress = DomainEvent(
                event_id=str(uuid4()),
                event_type="purpose.progress",
                source="purposes-service",
                timestamp=datetime.now(),
                payload=event_data_progress,
            )
            await publisher.publish(event_progress)

        return purpose

    async def get_purposes_by_user(self, user_id: int):
        """Получение целей пользователя"""
        result = await self.db.execute(select(Purpose).where(Purpose.user_id == user_id))
        return list(result.scalars().all())

    async def update_purpose(self, user_id: int, purpose_id: UUID, update_data: dict):
        """Обновление цели и проверка прогресса"""
        # Получаем текущую цель из БД
        purpose = await self.db.execute(
            select(Purpose).where((Purpose.id == purpose_id) & (Purpose.user_id == user_id))
        )
        purpose = purpose.scalar_one_or_none()

        if not purpose:
            return None

        # Сохраняем старые значения ДО обновления (для проверки порогов)
        old_amount = purpose.amount
        old_total_amount = purpose.total_amount

        # Обновляем дату изменения
        update_data["updated_at"] = func.now()

        # Формируем обновленные данные (остаются прежними, если не переданы)
        new_amount = update_data.get("amount", purpose.amount)
        new_total_amount = update_data.get("total_amount", purpose.total_amount)

        # Выполняем обновление
        stmt = (
            update(Purpose)
            .where((Purpose.id == purpose_id) & (Purpose.user_id == user_id))
            .values(**update_data)
            .returning(Purpose)
        )
        result = await self.db.execute(stmt)
        await self.db.commit()

        updated_purpose = result.scalar_one_or_none()

        # Публикуем событие об обновлении цели
        event_data_updated = {
            "user_id": user_id,
            "purpose_id": str(purpose.id),
            "name": updated_purpose.title if updated_purpose else purpose.title,
            "target_amount": str(new_total_amount),
            "current_amount": str(new_amount),
        }
        publisher = EventPublisher()
        event_updated = DomainEvent(
            event_id=str(uuid4()),
            event_type="purpose.updated",
            source="purposes-service",
            timestamp=datetime.now(),
            payload=event_data_updated,
        )
        await publisher.publish(event_updated)

        # Проверяем прогресс только если сумма изменилась
        if "amount" in update_data or "total_amount" in update_data:
            crossed = get_crossed_thresholds(old_amount, old_total_amount, new_amount, new_total_amount)

            for threshold in crossed:
                progress_percent = (new_amount / new_total_amount) * 100
                event_data = {
                    "user_id": user_id,
                    "purpose_id": str(purpose.id),
                    "purpose_name": purpose.title,
                    "progress_percent": round(progress_percent, 2),
                    "threshold": threshold,
                }
                publisher = EventPublisher()
                event = DomainEvent(
                    event_id=str(uuid4()),
                    event_type="purpose.progress",
                    source="purposes-service",
                    timestamp=datetime.now(),
                    payload=event_data,
                )
                await publisher.publish(event)

        return updated_purpose

    async def delete_purpose(self, user_id: int, purpose_id: UUID):
        """Удаление цели"""
        # Получаем цель перед удалением для события
        purpose = await self.db.execute(
            select(Purpose).where((Purpose.id == purpose_id) & (Purpose.user_id == user_id))
        )
        purpose = purpose.scalar_one_or_none()

        if not purpose:
            return None

        # Удаляем цель
        stmt = delete(Purpose).where((Purpose.id == purpose_id) & (Purpose.user_id == user_id))
        await self.db.execute(stmt)
        await self.db.commit()

        # Создаем событие об удалении цели
        event_data = {
            "user_id": user_id,
            "purpose_id": str(purpose.id),
            "name": purpose.title,
            "target_amount": purpose.total_amount,
            "current_amount": purpose.amount,
        }

        # Публикуем событие в Redis Streams
        publisher = EventPublisher()
        event = DomainEvent(
            event_id=str(uuid4()),
            event_type="purpose.deleted",
            source="purposes-service",
            timestamp=datetime.now(),
            payload=event_data,
        )
        await publisher.publish(event)

        # Возвращаем объект, который был загружен до удаления
        return purpose
