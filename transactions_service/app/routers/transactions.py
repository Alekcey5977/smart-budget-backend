from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, List
from datetime import datetime

from app.database import get_db
from app.dependencies import get_user_id_from_header
from app.repository.transactions_repository import TransactionRepository
from app.schemas import TransactionResponse

router = APIRouter(prefix="/transactions", tags=["transactions"])

    # FIXME: посмотреть print, нужно ли его убрать?


@router.get("/", response_model=List[TransactionResponse])
async def get_transactions(
    user_id: int = Depends(get_user_id_from_header),
    transaction_type: Optional[str] = Query(
        None,
        description="Тип транзакции: 'income', 'expense', или None для всех",
    ),
    category_mcc: Optional[List[str]] = Query(None, description="MCC коды через запятую: 5411,5812,5912"),
    start_date: Optional[datetime] = Query(
        None, description="Начальная дата периода"),
    end_date: Optional[datetime] = Query(
        None, description="Конечная дата периода"),
    min_amount: Optional[float] = Query(None, description="Минимальная сумма"),
    max_amount: Optional[float] = Query(
        None, description="Максимальная сумма"),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db)
):
    """Получить транзакции пользователя с фильтрацией"""

    try:

        # ПРЕОБРАЗУЕМ СТРОКИ В ЧИСЛА
        category_mcc_list = None
        if category_mcc:
            try:
                category_mcc_list = [int(mcc) for mcc in category_mcc]  # Преобразуем каждый элемент
                print(f"🔔 TRANSACTIONS SERVICE: Converted {category_mcc} -> {category_mcc_list}")
            except (ValueError, TypeError) as e:
                print(f"❌ MCC conversion error: {e}")
                raise HTTPException(400, "Invalid MCC codes format")
            
        repo = TransactionRepository(db)
        transactions = await repo.get_transactions_with_filters(
            user_id=user_id,
            transaction_type=transaction_type,
            category_mcc=category_mcc_list,
            start_date=start_date,
            end_date=end_date,
            min_amount=min_amount,
            max_amount=max_amount,
            limit=limit,
            offset=offset
        )
        
        result = []
        for t in transactions:
            result.append({
                "id": t.id,
                "user_id": t.user_id,
                "amount": t.amount,
                "category_mcc": t.category_mcc,
                "category_group": t.category.group if t.category else "Unknown",
                "date_time": t.date_time,
                "type": t.type
            })
        return result
        
    except Exception as e:
        print(f"❌ Error in get_transactions: {e}")
        raise HTTPException(500, f"Internal server error: {str(e)}")


    # TODO: в разработке

# @router.get("/categories")
# async def get_categories(
#     user_id: int = Depends(get_user_id_from_header),
#     db: AsyncSession = Depends(get_db)
# ):
#     """Получить уникальные категории пользователя"""
#     repo = TransactionRepository(db)
#     categories = await repo.get_user_categories(user_id)
#     return {"categories": categories}
