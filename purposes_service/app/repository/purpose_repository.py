from uuid import UUID, uuid4
from sqlalchemy import delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from app.schemas import PurposeCreate
from app.models import Purpose

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

        return purpose
    
    async def get_purposes_by_user(self, user_id: int):
        """Получение целей пользователя"""
        result = await self.db.execute(select(Purpose).where(Purpose.user_id == user_id))

        return list(result.scalars().all())
    
    async def update_purpose(self, user_id: int, purpose_id: UUID, update_data: dict):
        """Обновление цели"""
        update_data["updated_at"] = func.now()
        stmt = (
            update(Purpose)
            .where((Purpose.id == purpose_id) & (Purpose.user_id == user_id))
            .values(**update_data)
            .returning(Purpose)
        )
        result = await self.db.execute(stmt)
        await self.db.commit()

        return result.scalar_one_or_none()
    
    async def delete_purpose(self, user_id: int, purpose_id: UUID):
        """Удаление цели"""
        stmt = (
            delete(Purpose)
            .where((Purpose.id == purpose_id) & (Purpose.user_id == user_id))
            .returning(Purpose)
        )
        result = await self.db.execute(stmt)
        await self.db.commit()
        
        return result.scalar_one_or_none()
