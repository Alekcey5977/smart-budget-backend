from uuid import UUID, uuid4
from sqlalchemy import delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from app.schemas import PurposeCreate
from app.models import Purpose
from shared.event_publisher import EventPublisher
from shared.event_schema import DomainEvent
import datetime

class PurposeRepository:
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def create_purpose(self, user_id: int, purpose_data: PurposeCreate,):
        """Создание целей"""
        purpose = Purpose(
            id=uuid4(),
            user_id=user_id,
            title=purpose_data.title,
            deadline=purpose_data.deadline,
            amount=purpose_data.amount,
            total_amount=purpose_data.total_amount,
        )

        self.db.add(purpose)
        await self.db.commit()
        await self.db.refresh(purpose)


        # Проверяем прогресс при создании цели
        if purpose.total_amount > 0:
            progress_percent = (purpose.amount / purpose.total_amount) * 100
            
            # Проверяем пороги для уведомлений (25%, 50%, 80%, 100%)
            thresholds = [25, 50, 80, 100]
            
            for threshold in thresholds:
                if progress_percent >= threshold:
                    # Создаем событие для уведомления
                    event_data_progress = {
                        "user_id": user_id,
                        "purpose_id": str(purpose.id),
                        "purpose_name": purpose.title,
                        "progress_percent": round(progress_percent, 2),
                        "threshold": threshold
                    }
                    
                    # Публикуем событие в Redis Streams
                    publisher = EventPublisher()
                    event_progress = DomainEvent(
                        event_id=str(uuid4()),
                        event_type="purpose.progress",
                        source="purposes-service",
                        timestamp=datetime.datetime.now(),
                        payload=event_data_progress
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
            select(Purpose).where(
                (Purpose.id == purpose_id) & (Purpose.user_id == user_id)
            )
        )
        purpose = purpose.scalar_one_or_none()
        
        if not purpose:
            return None
            
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
        
        # Проверяем прогресс только если сумма изменилась
        if "amount" in update_data or "total_amount" in update_data:
            # Пересчитываем прогресс
            if new_total_amount > 0:
                progress_percent = (new_amount / new_total_amount) * 100
                
                # Проверяем пороги для уведомлений (25%, 50%, 80%, 100%)
                thresholds = [25, 50, 80, 100]
                
                for threshold in thresholds:
                    # Проверяем, пересекли ли мы этот порог (были ниже или стали выше)
                    if (purpose.amount / purpose.total_amount) * 100 < threshold and progress_percent >= threshold:
                        # Создаем событие для уведомления
                        event_data = {
                            "user_id": user_id,
                            "purpose_id": str(purpose.id),
                            "purpose_name": purpose.title,
                            "progress_percent": round(progress_percent, 2),
                            "threshold": threshold
                        }
                        
                        # Публикуем событие в Redis Streams
                        publisher = EventPublisher()
                        event = DomainEvent(
                            event_id=str(uuid4()),
                            event_type="purpose.progress",
                            source="purposes-service",
                            timestamp=datetime.datetime.now(),
                            payload=event_data
                        )
                        await publisher.publish(event)
                        
        return result.scalar_one_or_none()
    
    async def delete_purpose(self, user_id: int, purpose_id: UUID):
        """Удаление цели"""
        # Получаем цель перед удалением для события
        purpose = await self.db.execute(
            select(Purpose).where(
                (Purpose.id == purpose_id) & (Purpose.user_id == user_id)
            )
        )
        purpose = purpose.scalar_one_or_none()
        
        if not purpose:
            return None
            
        # Удаляем цель
        stmt = (
            delete(Purpose)
            .where((Purpose.id == purpose_id) & (Purpose.user_id == user_id))
            .returning(Purpose)
        )
        result = await self.db.execute(stmt)
        await self.db.commit()
        
        # Создаем событие об удалении цели
        event_data = {
            "user_id": user_id,
            "purpose_id": str(purpose.id),
            "name": purpose.title,
            "target_amount": purpose.total_amount,
            "current_amount": purpose.amount
        }
        
        # Публикуем событие в Redis Streams
        publisher = EventPublisher()
        event = DomainEvent(
            event_id=str(uuid4()),
            event_type="purpose.deleted",
            source="purposes-service",
            timestamp=datetime.datetime.now(),
            payload=event_data
        )
        await publisher.publish(event)
        
        return result.scalar_one_or_none()