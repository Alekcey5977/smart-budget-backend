from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models import Bank_Account


class TransactionRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_account_bank(self, bank_account_hash: str):
        """Получение счёта"""
        existing = await self.db.execute(
            select(Bank_Account).where(
                Bank_Account.account_number == bank_account_hash)
        ).scalars().first()
        return existing
