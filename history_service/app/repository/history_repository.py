from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import delete, select
from app.models import HistoryEntry
from app.schemas import HistoryEntryCreate
from uuid import UUID


class HistoryRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_entry(self, entry_data: HistoryEntryCreate):
        """Создание записи истории"""
        entry = HistoryEntry(
            user_id=entry_data.user_id,
            title=entry_data.title,
            body=entry_data.body
        )
        self.db.add(entry)
        await self.db.commit()
        await self.db.refresh(entry)
        return entry

    async def get_entries_by_user(self, user_id: int, skip: int = 0, limit: int = 100):
        """Получение истории пользователя"""
        result = await self.db.execute(
            select(HistoryEntry)
            .where(HistoryEntry.user_id == user_id)
            .order_by(HistoryEntry.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        return result.scalars().all()

    async def get_entry_by_id(self, entry_id: UUID):
        """Получение записи по ID"""
        result = await self.db.execute(
            select(HistoryEntry)
            .where(HistoryEntry.id == entry_id)
        )
        return result.scalar_one_or_none()

    async def delete_entry(self, entry_id: UUID, user_id: int):
        """Удаление записи истории"""
        stmt = (
            delete(HistoryEntry)
            .where((HistoryEntry.id == entry_id) & (HistoryEntry.user_id == user_id))
        )
        result = await self.db.execute(stmt)
        await self.db.commit()
        return result.rowcount
