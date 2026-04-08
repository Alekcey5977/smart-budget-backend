import uuid
from datetime import datetime
from typing import List, Optional

from app.cache import (
    CATEGORIES_ALL_KEY,
    CATEGORIES_EXPENSE_KEY,
    CATEGORIES_INCOME_KEY,
    CATEGORIES_TTL,
    cache_client,
    category_by_id_key,
)
from app.database import get_db
from app.dependencies import get_user_id_from_header
from app.repository.transactions_repository import TransactionRepository
from app.schemas import (
    CategoryResponse,
    TransactionFilterRequest,
    TransactionResponse,
    UpdateTransactionCategoryRequest,
)
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from shared.event_publisher import EventPublisher
from shared.event_schema import DomainEvent

router = APIRouter(prefix="/transactions", tags=["transactions"])


@router.post(
    "/",
    response_model=List[TransactionResponse],
    summary="Получить транзакции с фильтрацией",
    description="Получить список транзакций пользователя с возможностью фильтрации по различным параметрам."
)
async def get_transactions(
    filters: TransactionFilterRequest,
    user_id: int = Depends(get_user_id_from_header),
    db: AsyncSession = Depends(get_db)
):
    """
    Получить транзакции пользователя с фильтрацией.

    Принимает JSON с параметрами фильтрации:
    - transaction_type: тип транзакции (income/expense)
    - category_ids: список ID категорий
    - start_date, end_date: период дат
    - min_amount, max_amount: диапазон сумм
    - merchant_ids: список ID мерчантов
    - limit, offset: пагинация
    """
    try:
        repo = TransactionRepository(db)
        transactions = await repo.get_transactions_with_filters(
            user_id=user_id,
            transaction_type=filters.transaction_type,
            category_ids=filters.category_ids,
            start_date=filters.start_date,
            end_date=filters.end_date,
            min_amount=filters.min_amount,
            max_amount=filters.max_amount,
            merchant_ids=filters.merchant_ids,
            limit=filters.limit,
            offset=filters.offset
        )

        result = []
        for t in transactions:
            result.append({
                "id": t.id,
                "user_id": t.user_id,
                "bank_account_id": t.bank_account_id,
                "category_id": t.category_id,
                "category_name": t.category.name if t.category else None,
                "amount": t.amount,
                "created_at": t.created_at,
                "type": t.type,
                "description": t.description,
                "merchant_id": t.merchant_id,
                "merchant_name": t.merchant.name if t.merchant else None
            })

        return result

    except Exception as e:
        raise HTTPException(500, f"Internal server error: {str(e)}")


@router.patch(
    "/{transaction_id}/category",
    response_model=TransactionResponse,
    summary="Изменить категорию транзакции",
    description="Изменить категорию для конкретной транзакции пользователя."
)
async def update_transaction_category(
    transaction_id: str,
    body: UpdateTransactionCategoryRequest,
    user_id: int = Depends(get_user_id_from_header),
    db: AsyncSession = Depends(get_db)
):
    """
    Изменить категорию транзакции.

    - **transaction_id**: UUID транзакции
    - **category_id**: ID новой категории
    """
    try:
        repo = TransactionRepository(db)

        category = await repo.get_category_by_id(body.category_id)
        if not category:
            raise HTTPException(404, f"Category {body.category_id} not found")

        transaction = await repo.update_transaction_category(transaction_id, user_id, body.category_id)
        if not transaction:
            raise HTTPException(404, f"Transaction {transaction_id} not found")

        await EventPublisher().publish(DomainEvent(
            event_id=uuid.uuid4(),
            event_type="transaction.category.updated",
            source="transactions-service",
            timestamp=datetime.now(),
            payload={
                "user_id": user_id,
                "transaction_id": str(transaction_id),
                "old_category_name": category.name,
                "new_category_name": transaction.category.name if transaction.category else str(body.category_id),
            }
        ))

        return {
            "id": transaction.id,
            "user_id": transaction.user_id,
            "bank_account_id": transaction.bank_account_id,
            "category_id": transaction.category_id,
            "category_name": transaction.category.name if transaction.category else None,
            "amount": float(transaction.amount),
            "created_at": transaction.created_at,
            "type": transaction.type,
            "description": transaction.description,
            "merchant_id": transaction.merchant_id,
            "merchant_name": transaction.merchant.name if transaction.merchant else None,
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"Internal server error: {str(e)}")


@router.get(
    "/categories",
    response_model=List[CategoryResponse],
    summary="Получить категории",
    description="""Получить список категорий транзакций.

Опциональный параметр **type** фильтрует выдачу:
- `expense` — категории расходов + универсальные (type=null)
- `income` — категории доходов + универсальные (type=null)
- без параметра — все категории

Используйте фильтр при смене категории транзакции, чтобы показывать только подходящие варианты.
"""
)
async def get_categories(
    type: Optional[str] = Query(
        None,
        description="Фильтр по типу: 'income' или 'expense'. Универсальные категории (null) включаются всегда."
    ),
    db: AsyncSession = Depends(get_db),
):
    """Получить категории с кэшем в Redis"""
    # Определяем ключ кэша
    if type == "income":
        cache_key = CATEGORIES_INCOME_KEY
    elif type == "expense":
        cache_key = CATEGORIES_EXPENSE_KEY
    else:
        cache_key = CATEGORIES_ALL_KEY

    # Cache-Aside: пробуем получить из кэша
    cached = await cache_client.get(cache_key)
    if cached is not None:
        return cached

    # Промах кэша -> запрос в БД
    try:
        repo = TransactionRepository(db)
        categories = await repo.get_all_categories(type=type)

        # Сериализуем в dict для кэширования
        result = [
            {
                "id": cat.id,
                "name": cat.name,
                "type": cat.type,
            }
            for cat in categories
        ]

        # Сохраняем в кэш
        await cache_client.set(cache_key, result, ttl=CATEGORIES_TTL)

        return result

    except Exception as e:
        raise HTTPException(500, f"Internal server error: {str(e)}")


@router.get(
    "/categories/{category_id}",
    response_model=CategoryResponse,
    summary="Получить категорию по ID",
    description="Получить категорию транзакций по её ID."
)
async def get_category_by_id(
    category_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Получить категорию по ID с кэшем в Redis"""
    cache_key = category_by_id_key(category_id)

    # Cache-Aside
    cached = await cache_client.get(cache_key)
    if cached is not None:
        return cached

    try:
        repo = TransactionRepository(db)
        category = await repo.get_category_by_id(category_id)
        if not category:
            raise HTTPException(404, f"Category {category_id} not found")

        result = {
            "id": category.id,
            "name": category.name,
            "type": category.type,
        }

        await cache_client.set(cache_key, result, ttl=CATEGORIES_TTL)
        return result

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"Internal server error: {str(e)}")


@router.get(
    "/{transaction_id}",
    response_model=TransactionResponse,
    summary="Получить транзакцию по ID",
    description="Получить конкретную транзакцию пользователя по её UUID."
)
async def get_transaction_by_id(
    transaction_id: str,
    user_id: int = Depends(get_user_id_from_header),
    db: AsyncSession = Depends(get_db)
):
    """Получить транзакцию по ID без кэширования"""
    try:
        repo = TransactionRepository(db)
        transaction = await repo.get_transaction_by_id(transaction_id, user_id)
        if not transaction:
            raise HTTPException(404, f"Transaction {transaction_id} not found")

        result = {
            "id": transaction.id,
            "user_id": transaction.user_id,
            "bank_account_id": transaction.bank_account_id,
            "category_id": transaction.category_id,
            "category_name": transaction.category.name if transaction.category else None,
            "amount": float(transaction.amount),
            "created_at": transaction.created_at,
            "type": transaction.type,
            "description": transaction.description,
            "merchant_id": transaction.merchant_id,
            "merchant_name": transaction.merchant.name if transaction.merchant else None,
        }

        return result

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"Internal server error: {str(e)}")
