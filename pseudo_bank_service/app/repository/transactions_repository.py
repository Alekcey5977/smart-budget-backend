from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from app.models import Bank_Account, Bank, Transaction, Merchant, Category, MCC_Category

class TransactionRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_account_bank(self, bank_account_hash: str):
        """Получение счёта"""
        result = await self.db.execute(
            select(Bank_Account).where(
                Bank_Account.bank_account_hash == bank_account_hash
            )
        )
        return result.scalar_one_or_none()

    async def export_account_data(self, account_hash: str):
        """Экспорт всех связанных данных по счёту"""
        account = await self.get_account_bank(account_hash)
        if not account:
            return None

        # Получаем банк
        bank_result = await self.db.execute(
            select(Bank).where(Bank.id == account.bank_id)
        )
        bank = bank_result.scalar_one()

        # Получаем транзакции с мерчантами и категориями
        transactions_result = await self.db.execute(
            select(Transaction)
            .where(Transaction.bank_account_id == account.id)
            .options(
                selectinload(Transaction.merchant).selectinload(
                    Merchant.category),
                selectinload(Transaction.category)
            )
        )
        transactions = transactions_result.scalars().all()

        # Собираем ID для категорий и мерчантов
        merchant_ids = {t.merchant_id for t in transactions if t.merchant_id}
        category_ids = {t.category_id for t in transactions}
        if merchant_ids:
            merchant_categories = await self.db.execute(
                select(Merchant.category_id)
                .where(Merchant.id.in_(merchant_ids))
            )
            category_ids.update(
                m_id for m_id, in merchant_categories.fetchall() if m_id)

        # Получаем все категории
        categories = []
        if category_ids:
            categories_result = await self.db.execute(
                select(Category).where(Category.id.in_(category_ids))
            )
            categories = categories_result.scalars().all()

        # Получаем MCC
        mccs = []
        if category_ids:
            mcc_result = await self.db.execute(
                select(MCC_Category).where(
                    MCC_Category.category_id.in_(category_ids))
            )
            mccs = mcc_result.scalars().all()

        # Получаем мерчантов (уже загружены через selectinload, но можно уточнить)
        merchants = [t.merchant for t in transactions if t.merchant]

        return {
            "account": account,
            "bank": bank,
            "transactions": transactions,
            "merchants": merchants,
            "categories": categories,
            "mccs": mccs
        }

    @staticmethod
    def to_dict(obj):
        """Утилита для сериализации SQLAlchemy-объектов"""
        if hasattr(obj, '__table__'):
            return {c.name: getattr(obj, c.name) for c in obj.__table__.columns}
        return obj
