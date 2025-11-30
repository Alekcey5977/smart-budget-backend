from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from app.database import get_db
from app.dependencies import get_user_id_from_header
from app.repository.transactions_repository import TransactionRepository
from app.schemas import TransactionFilterRequest, TransactionResponse, CategoryResponse

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


@router.get(
    "/categories",
    response_model=List[CategoryResponse],
    summary="Получить все категории",
    description="Получить список всех доступных категорий транзакций."
)
async def get_categories(
    db: AsyncSession = Depends(get_db)
):
    """
    Получить все категории транзакций.

    Возвращает список всех категорий с их ID и названиями.
    """
    try:
        repo = TransactionRepository(db)
        categories = await repo.get_all_categories()
        return categories

    except Exception as e:
        raise HTTPException(500, f"Internal server error: {str(e)}")
