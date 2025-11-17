from sqlalchemy import select
from sqlalchemy.orm import joinedload
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from datetime import datetime
from app.models import Transaction, Category

class TransactionRepository:
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def get_transactions_with_filters(
        self,
        user_id: int,
        transaction_type: Optional[str] = None,
        category_mcc: Optional[int] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        min_amount: Optional[float] = None,
        max_amount: Optional[float] = None,
        limit: int = 100,
        offset: int = 0
    ):
        """Основной метод для получения транзакций с фильтрацией"""
        
        # Базовый запрос с фильтрацией по id пользоавтеля
        query = select(Transaction).where(Transaction.user_id ==
                                          user_id).options(joinedload(Transaction.category))

        # Фильтрация по типу транзакции
        if transaction_type == "income":
            query = query.where(Transaction.amount > 0)
        elif transaction_type == "expense":
            query = query.where(Transaction.amount < 0)
        
        # Фильтрация по категории
        if category_mcc is not None:
            query = query.where(Transaction.category_mcc == category_mcc)

        # Фильтрация по дате
        if start_date is not None:
            query = query.where(Transaction.date_time >= start_date)
        if end_date:
            query = query.where(Transaction.date_time <= end_date)

        # Фильтрация по сумме
        if min_amount is not None:
            query = query.where(Transaction.amount >= min_amount)
        if max_amount is not None:
            query = query.where(Transaction.amount <= max_amount)

        # Сортировка и пагинация
        query = query.order_by(Transaction.date_time.desc()).limit(limit).offset(offset)
        
        # Выполнение запроса
        result = await self.db.execute(query)

        return result.scalars().all()


    async def create_transaction(self, transaction_data: dict):
        """Создание новой транзакции"""
        
        db_transaction = Transaction(**transaction_data)
        self.db.add(db_transaction)
        await self.db.commit()
        await self.db.refresh(db_transaction)

        return db_transaction
    

    async def get_transaction_by_id(self, user_id: int):
        """Получить транзакцию по ID"""

        query = select(Transaction).where(Transaction.user_id == user_id)
        result = await self.db.execute(query)

        return result.scalar_one_or_none()
    

    async def get_user_categories(self, user_id: int):
        """Получить уникальные категории пользователя"""

        query = select(Transaction.category).where(Transaction.user_id == user_id).distinct()
        result = await self.db.execute(query)

        return result.scalars().all()
    

    