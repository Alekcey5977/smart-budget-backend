from sqlalchemy import select
from sqlalchemy.orm import joinedload
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, List
from datetime import datetime
from app.models import Transaction, Category


class TransactionRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_transactions_with_filters(
        self,
        user_id: int,
        transaction_type: Optional[str] = None,
        category_ids: Optional[List[int]] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        min_amount: Optional[float] = None,
        max_amount: Optional[float] = None,
        merchant_ids: Optional[List[int]] = None,
        limit: int = 50,
        offset: int = 0
    ):
        """
        Получение транзакций с фильтрацией.

        Args:
            user_id: ID пользователя
            transaction_type: Тип транзакции (income/expense)
            category_ids: Список ID категорий
            start_date: Начальная дата периода
            end_date: Конечная дата периода
            min_amount: Минимальная сумма
            max_amount: Максимальная сумма
            merchant_ids: Список ID мерчантов
            limit: Лимит записей
            offset: Смещение

        Returns:
            Список транзакций
        """
        query = (
            select(Transaction)
            .where(Transaction.user_id == user_id)
            .options(
                joinedload(Transaction.category),
                joinedload(Transaction.merchant)
            )
        )

        if transaction_type:
            query = query.where(Transaction.type == transaction_type)

        if category_ids:
            query = query.where(Transaction.category_id.in_(category_ids))

        if start_date:
            query = query.where(Transaction.created_at >= start_date)

        if end_date:
            query = query.where(Transaction.created_at <= end_date)

        if min_amount is not None:
            query = query.where(Transaction.amount >= min_amount)

        if max_amount is not None:
            query = query.where(Transaction.amount <= max_amount)

        if merchant_ids:
            query = query.where(Transaction.merchant_id.in_(merchant_ids))

        query = (
            query
            .order_by(Transaction.created_at.desc())
            .limit(limit)
            .offset(offset)
        )

        result = await self.db.execute(query)
        return result.scalars().unique().all()

    async def get_all_categories(self) -> List[Category]:
        """
        Получение всех категорий.

        Returns:
            Список всех категорий
        """
        query = select(Category).order_by(Category.id)
        result = await self.db.execute(query)
        return result.scalars().all()

    async def create_transaction(self, transaction_data: dict) -> Transaction:
        """
        Создание новой транзакции.

        Args:
            transaction_data: Данные транзакции

        Returns:
            Созданная транзакция
        """
        db_transaction = Transaction(**transaction_data)
        self.db.add(db_transaction)
        await self.db.commit()
        await self.db.refresh(db_transaction)
        return db_transaction

    async def get_transaction_by_id(self, transaction_id: str, user_id: int) -> Optional[Transaction]:
        """
        Получение транзакции по ID.

        Args:
            transaction_id: ID транзакции
            user_id: ID пользователя

        Returns:
            Транзакция или None
        """
        query = (
            select(Transaction)
            .where(Transaction.id == transaction_id)
            .where(Transaction.user_id == user_id)
            .options(
                joinedload(Transaction.category),
                joinedload(Transaction.merchant)
            )
        )
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def get_category_by_id(self, category_id: int) -> Optional[Category]:
        """
        Получение категории по ID.

        Args:
            category_id: ID категории

        Returns:
            Категория или None
        """
        query = select(Category).where(Category.id == category_id)
        result = await self.db.execute(query)
        return result.scalar_one_or_none()
