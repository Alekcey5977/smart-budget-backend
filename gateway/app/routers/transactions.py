from fastapi import APIRouter, Depends, HTTPException, Header, Query
import os
from typing import Dict, Any, List, Optional
from app.dependencies import get_current_user
import httpx
from datetime import datetime


router = APIRouter(
    prefix="/transactions",
    tags=["transactions"]

)
TRANSACTIONS_SERVICE_URL = os.getenv("TRANSACTIONS_SERVICE_URL", "http://transactions-service:8002")

# ----------------------------
# Вывод всех транзакций
# ----------------------------
@router.get("/")
async def get_transactions(
    current_user: Dict[str, Any] = Depends(get_current_user),
    transaction_type: Optional[str] = Query(
        None,
        description="Тип транзакции: 'income', 'expense', или None для всех",
        regex="^(income|expense)?$"),

    category_mcc: Optional[int] = Query(
        None,
        description="Фильтр по категории"),
    
    start_date: Optional[datetime] = Query(
        None,
        description="Начальная дата периода"),
    
    end_date: Optional[datetime] = Query(
        None,
        description="Конечная дата периода"),
    
    min_amount: Optional[float] = Query(
        None,
        description="Минимальная сумма транзакции"),
    
    max_amount: Optional[float] = Query(
        None,
        description="Максимальная сумма транзакции"),
    
    limit: int = Query(50, ge=1, le=100, description="Лимит записей"),

    offset: int = Query(0, ge=0, description="Смещение")
):
    """
    Получить транзакции пользователя с фильтрацией
    
    Защищенный эндпоинт, требует JWT токен
    
    **Параметры фильтрации:**
    - `transaction_type`: 'income' (доходы), 'expense' (расходы)
    - `category`: фильтр по категории
    - `start_date`, `end_date`: период дат
    - `min_amount`, `max_amount`: диапазон сумм
    - `limit`, `offset`: пагинация
    
    **Примеры запросов:**
    
    ## Все транзакции
    GET /transactions
    
    ## Только доходы
    GET /transactions?transaction_type=income
    
    ## Только расходы за январь 2024
    GET /transactions?transaction_type=expense&start_date=2024-01-01&end_date=2024-01-31
    
    ## Транзакции категории "Еда" с пагинацией
    GET /transactions?category=Еда&limit=50&offset=0
    
    ## Крупные доходы (>5000 руб)
    GET /transactions?transaction_type=income&min_amount=5000
    """

    # достаем user_id из уже проверенного current_user
    user_id = current_user["user_id"]

    # Собираем параметры фильтрации
    params = {
        "transaction_type": transaction_type,
        "category_mcc": category_mcc,
        "start_date": start_date.isoformat() if start_date else None,
        "end_date": end_date.isoformat() if end_date else None,
        "min_amount": min_amount,
        "max_amo"
        "unt": max_amount,
        "limit": limit,
        "offset": offset
    }

    clean_params = {k: v for k, v in params.items() if v is not None}

    async with httpx.AsyncClient() as client:
        try:
            headers = {"X-User-ID": str(user_id)}
            print(f"🔔 Gateway: отправляю запрос в {TRANSACTIONS_SERVICE_URL}/transactions")
            print(f"🔔 Gateway: заголовки {headers}")
            response = await client.get(
                f"{TRANSACTIONS_SERVICE_URL}/transactions/",
                headers=headers,
                params=clean_params,
                timeout=10.0
            )
            print(f"🔔 Gateway: статус ответа {response.status_code}")
            print(f"🔔 Gateway: заголовки ответа {response.headers}")
            print(f"🔔 Gateway: тело ответа {response.text}")
            if response.status_code == 200:
                return response.json()
            
            else:
                error_detail = response.json().get("detail", "Failed to get transactions")
                raise HTTPException(
                    status_code=response.status_code,
                    detail=error_detail
                )
            
        except httpx.ConnectError:
            raise HTTPException(503, "Transaction service is unavailable")
        except httpx.TimeoutException:
            raise HTTPException(504, "Transactions service timeout")