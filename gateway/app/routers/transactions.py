from fastapi import APIRouter, Depends, HTTPException
import os
from typing import Dict, Any, List
from app.dependencies import get_current_user
from app.schemas.transaction_schema import TransactionFilterRequest, TransactionResponse, CategoryResponse
import httpx


router = APIRouter(
    prefix="/transactions",
    tags=["transactions"]
)

TRANSACTIONS_SERVICE_URL = os.getenv(
    "TRANSACTIONS_SERVICE_URL",
    "http://transactions-service:8002"
)


@router.post(
    "/",
    response_model=List[TransactionResponse],
    summary="Получить транзакции с фильтрацией",
    description="""
Получить список транзакций пользователя с возможностью фильтрации.

**Требует авторизации:** JWT токен в заголовке Authorization.

## Параметры фильтрации

| Параметр | Тип | Описание |
|----------|-----|----------|
| `transaction_type` | string | Тип: `income` (доходы) или `expense` (расходы) |
| `category_ids` | list[int] | Список ID категорий |
| `start_date` | datetime | Начало периода  |
| `end_date` | datetime | Конец периода  |
| `min_amount` | float | Минимальная сумма |
| `max_amount` | float | Максимальная сумма |
| `merchant_ids` | list[int] | Список ID мерчантов |
| `limit` | int | Количество записей (1-100, обязательное) |
| `offset` | int | Смещение для пагинации |

## Примеры запросов

### Все транзакции (первые 50)
```json
{"limit": 50}
```

### Только расходы
```json
{"transaction_type": "expense", "limit": 50}
```

### Транзакции за период
```json
{
    "start_date": "2024-01-01T00:00:00",
    "end_date": "2024-01-31T23:59:59",
    "limit": 50
}
```

### Крупные доходы с пагинацией
```json
{
    "transaction_type": "income",
    "min_amount": 5000,
    "limit": 20,
    "offset": 0
}
```
""",
    responses={
        200: {
            "description": "Список транзакций",
            "content": {
                "application/json": {
                    "example": [
                        {
                            "id": "550e8400-e29b-41d4-a716-446655440000",
                            "user_id": 1,
                            "category_id": 5,
                            "category_name": "Продукты",
                            "amount": 1500.50,
                            "created_at": "2024-01-15T14:30:00",
                            "type": "expense",
                            "description": "Покупка в супермаркете",
                            "merchant_id": 10,
                            "merchant_name": "Пятёрочка"
                        }
                    ]
                }
            }
        },
        401: {"description": "Не авторизован"},
        503: {"description": "Сервис транзакций недоступен"},
        504: {"description": "Таймаут сервиса транзакций"}
    }
)
async def get_transactions(
    filters: TransactionFilterRequest,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Получить транзакции пользователя с фильтрацией.

    Защищенный эндпоинт, требует JWT токен.
    Все параметры фильтрации передаются в теле запроса как JSON.
    """
    user_id = current_user["user_id"]

    request_data = filters.model_dump(exclude_none=True)

    async with httpx.AsyncClient() as client:
        try:
            headers = {"X-User-ID": str(user_id)}

            response = await client.post(
                f"{TRANSACTIONS_SERVICE_URL}/transactions/",
                headers=headers,
                json=request_data,
                timeout=10.0
            )

            if response.status_code == 200:
                return response.json()

            error_detail = response.json().get("detail", "Failed to get transactions")
            raise HTTPException(
                status_code=response.status_code,
                detail=error_detail
            )

        except httpx.ConnectError:
            raise HTTPException(503, "Transaction service is unavailable")
        except httpx.TimeoutException:
            raise HTTPException(504, "Transactions service timeout")


@router.get(
    "/categories",
    response_model=List[CategoryResponse],
    summary="Получить все категории",
    description="""
Получить список всех доступных категорий транзакций.

**Требует авторизации:** JWT токен в заголовке Authorization.

Возвращает список категорий с их ID и названиями.
""",
    responses={
        200: {
            "description": "Список категорий",
            "content": {
                "application/json": {
                    "example": [
                        {"id": 1, "name": "Продукты"},
                        {"id": 2, "name": "Транспорт"},
                        {"id": 3, "name": "Развлечения"}
                    ]
                }
            }
        },
        401: {"description": "Не авторизован"},
        503: {"description": "Сервис транзакций недоступен"}
    }
)
async def get_categories(
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Получить все категории транзакций.

    Защищенный эндпоинт, требует JWT токен.
    """
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(
                f"{TRANSACTIONS_SERVICE_URL}/transactions/categories",
                timeout=10.0
            )

            if response.status_code == 200:
                return response.json()

            error_detail = response.json().get("detail", "Failed to get categories")
            raise HTTPException(
                status_code=response.status_code,
                detail=error_detail
            )

        except httpx.ConnectError:
            raise HTTPException(503, "Transaction service is unavailable")
        except httpx.TimeoutException:
            raise HTTPException(504, "Transactions service timeout")
