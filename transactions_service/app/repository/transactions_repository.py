from datetime import datetime
from typing import List, Optional

from app.models import Category, Transaction
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload


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
        offset: int = 0,
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
            .options(joinedload(Transaction.category), joinedload(Transaction.merchant))
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

        query = query.order_by(Transaction.created_at.desc()).limit(limit).offset(offset)

        result = await self.db.execute(query)
        return result.scalars().unique().all()

    async def get_all_categories(self, type: Optional[str] = None) -> List[Category]:
        """
        Получение всех категорий.

        Args:
            type: Фильтр по типу ("income" / "expense"). Если указан,
                  возвращаются категории с данным типом И универсальные (type=NULL).

        Returns:
            Список категорий
        """
        query = select(Category).order_by(Category.id)
        if type is not None:
            query = query.where((Category.type == type) | (Category.type.is_(None)))
        result = await self.db.execute(query)
        return result.scalars().all()

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
            .options(joinedload(Transaction.category), joinedload(Transaction.merchant))
        )
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def update_transaction_category(
        self, transaction_id: str, user_id: int, category_id: int
    ) -> Optional[Transaction]:
        """
        Изменить категорию транзакции.

        Args:
            transaction_id: ID транзакции
            user_id: ID пользователя (для проверки владельца)
            category_id: ID новой категории

        Returns:
            Обновлённая транзакция или None если не найдена
        """
        transaction = await self.get_transaction_by_id(transaction_id, user_id)
        if transaction is None:
            return None
        transaction.category_id = category_id
        await self.db.flush()
        self.db.expire(transaction)
        return await self.get_transaction_by_id(transaction_id, user_id)

    async def get_category_summary(
        self,
        user_id: int,
        transaction_type: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> list:
        query = (
            select(
                Category.id.label("category_id"),
                Category.name.label("category_name"),
                func.sum(Transaction.amount).label("total_amount"),
                func.count(Transaction.id).label("transaction_count"),
            )
            .join(Category, Transaction.category_id == Category.id)
            .where(Transaction.user_id == user_id)
            .group_by(Category.id, Category.name)
            .having(func.sum(Transaction.amount) > 0)
            .order_by(func.sum(Transaction.amount).desc())
        )

        if transaction_type:
            query = query.where(Transaction.type == transaction_type)
        if start_date:
            query = query.where(Transaction.created_at >= start_date)
        if end_date:
            query = query.where(Transaction.created_at <= end_date)

        result = await self.db.execute(query)
        return result.all()

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
