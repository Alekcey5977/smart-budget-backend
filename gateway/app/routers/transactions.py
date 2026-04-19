import os
from typing import Any, Dict, List, Optional

import httpx
from app.dependencies import get_current_user
from app.schemas.transaction_schema import (
    CategoryResponse,
    CategorySummaryRequest,
    CategorySummaryResponse,
    TransactionFilterRequest,
    TransactionResponse,
    UpdateTransactionCategoryRequest,
)
from fastapi import APIRouter, Depends, HTTPException, Query

router = APIRouter(prefix="/transactions", tags=["transactions"])

TRANSACTIONS_SERVICE_URL = os.getenv("TRANSACTIONS_SERVICE_URL", "http://transactions-service:8002")


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
                            "bank_account_id": 1,
                            "category_id": 5,
                            "category_name": "Продукты",
                            "amount": 1500.50,
                            "created_at": "2024-01-15T14:30:00",
                            "type": "expense",
                            "description": "Покупка в супермаркете",
                            "merchant_id": 10,
                            "merchant_name": "Пятёрочка",
                        }
                    ]
                }
            },
        },
        401: {"description": "Не авторизован"},
        503: {"description": "Сервис транзакций недоступен"},
        504: {"description": "Таймаут сервиса транзакций"},
    },
)
async def get_transactions(filters: TransactionFilterRequest, current_user: Dict[str, Any] = Depends(get_current_user)):
    """
    Получить транзакции пользователя с фильтрацией.

    Защищенный эндпоинт, требует JWT токен.
    Все параметры фильтрации передаются в теле запроса как JSON.
    """
    user_id = current_user["user_id"]

    request_data = filters.model_dump(exclude_none=True, mode="json")

    async with httpx.AsyncClient() as client:
        try:
            headers = {"X-User-ID": str(user_id)}

            response = await client.post(
                f"{TRANSACTIONS_SERVICE_URL}/transactions/", headers=headers, json=request_data, timeout=10.0
            )

            if response.status_code == 200:
                return response.json()

            error_detail = response.json().get("detail", "Failed to get transactions")
            raise HTTPException(status_code=response.status_code, detail=error_detail)

        except httpx.ConnectError:
            raise HTTPException(503, "Transaction service is unavailable")
        except httpx.TimeoutException:
            raise HTTPException(504, "Transactions service timeout")


@router.patch(
    "/{transaction_id}/category",
    response_model=TransactionResponse,
    summary="Изменить категорию транзакции",
    description="""
Изменить категорию для конкретной транзакции пользователя.

**Требует авторизации:** JWT токен в заголовке Authorization.

Можно изменить только свою транзакцию. Указанная категория должна существовать.
""",
    responses={
        200: {
            "description": "Транзакция с обновлённой категорией",
            "content": {
                "application/json": {
                    "example": {
                        "id": "550e8400-e29b-41d4-a716-446655440000",
                        "user_id": 1,
                        "bank_account_id": 1,
                        "category_id": 3,
                        "category_name": "Транспорт",
                        "amount": 250.00,
                        "created_at": "2024-01-15T14:30:00",
                        "type": "expense",
                        "description": "Такси",
                        "merchant_id": None,
                        "merchant_name": None,
                    }
                }
            },
        },
        401: {"description": "Не авторизован"},
        404: {"description": "Транзакция или категория не найдена"},
        503: {"description": "Сервис транзакций недоступен"},
        504: {"description": "Таймаут сервиса транзакций"},
    },
)
async def update_transaction_category(
    transaction_id: str,
    body: UpdateTransactionCategoryRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """
    Изменить категорию транзакции.

    Защищённый эндпоинт, требует JWT токен.
    """
    user_id = current_user["user_id"]

    async with httpx.AsyncClient() as client:
        try:
            response = await client.patch(
                f"{TRANSACTIONS_SERVICE_URL}/transactions/{transaction_id}/category",
                headers={"X-User-ID": str(user_id)},
                json=body.model_dump(),
                timeout=10.0,
            )

            if response.status_code == 200:
                return response.json()

            error_detail = response.json().get("detail", "Failed to update transaction category")
            raise HTTPException(status_code=response.status_code, detail=error_detail)

        except httpx.ConnectError:
            raise HTTPException(503, "Transaction service is unavailable")
        except httpx.TimeoutException:
            raise HTTPException(504, "Transactions service timeout")


@router.post(
    "/categories/summary",
    response_model=List[CategorySummaryResponse],
    summary="Суммы транзакций по категориям",
    description="""
Возвращает агрегированные суммы и количество операций по каждой категории пользователя.

**Требует авторизации:** JWT токен в заголовке Authorization.

Категории с нулевой суммой за указанный период не включаются.
Результат отсортирован по убыванию суммы.

## Примеры запросов

### Расходы за январь
```json
{
    "transaction_type": "expense",
    "start_date": "2026-01-01T00:00:00",
    "end_date": "2026-01-31T23:59:59"
}
```

### Все доходы за всё время
```json
{ "transaction_type": "income" }
```

### Все операции без фильтров
```json
{}
```
""",
    responses={
        200: {
            "description": "Список категорий с суммами",
            "content": {
                "application/json": {
                    "example": [
                        {"category_id": 1, "category_name": "Продукты", "total_amount": 15420.50, "transaction_count": 42},
                        {"category_id": 2, "category_name": "Транспорт", "total_amount": 3200.00, "transaction_count": 18},
                    ]
                }
            },
        },
        401: {"description": "Не авторизован"},
        503: {"description": "Сервис транзакций недоступен"},
        504: {"description": "Таймаут сервиса транзакций"},
    },
)
async def get_category_summary(
    filters: CategorySummaryRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    user_id = current_user["user_id"]

    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                f"{TRANSACTIONS_SERVICE_URL}/transactions/categories/summary",
                headers={"X-User-ID": str(user_id)},
                json=filters.model_dump(exclude_none=True, mode="json"),
                timeout=10.0,
            )

            if response.status_code == 200:
                return response.json()

            error_detail = response.json().get("detail", "Failed to get category summary")
            raise HTTPException(status_code=response.status_code, detail=error_detail)

        except httpx.ConnectError:
            raise HTTPException(503, "Transaction service is unavailable")
        except httpx.TimeoutException:
            raise HTTPException(504, "Transactions service timeout")


@router.get(
    "/categories",
    response_model=List[CategoryResponse],
    summary="Получить категории",
    description="""
Получить список категорий транзакций.

**Требует авторизации:** JWT токен в заголовке Authorization.

Опциональный параметр **type** фильтрует выдачу:
- `expense` — категории расходов + универсальные
- `income` — категории доходов + универсальные
- без параметра — все категории

**Используйте при смене категории транзакции**, чтобы показывать фронту только подходящие варианты.
""",
    responses={
        200: {
            "description": "Список категорий",
            "content": {
                "application/json": {
                    "example": [
                        {"id": 1, "name": "Продукты", "type": "expense"},
                        {"id": 2, "name": "Транспорт", "type": "expense"},
                        {"id": 11, "name": "Зарплата", "type": "income"},
                        {"id": 13, "name": "Инвестиции", "type": None},
                    ]
                }
            },
        },
        401: {"description": "Не авторизован"},
        503: {"description": "Сервис транзакций недоступен"},
    },
)
async def get_categories(
    type: Optional[str] = Query(
        None, description="Фильтр по типу: 'income' или 'expense'. Универсальные категории (null) включаются всегда."
    ),
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """
    Получить категории транзакций с опциональной фильтрацией по типу.

    Защищенный эндпоинт, требует JWT токен.
    """
    async with httpx.AsyncClient() as client:
        try:
            params = {}
            if type is not None:
                params["type"] = type

            response = await client.get(
                f"{TRANSACTIONS_SERVICE_URL}/transactions/categories", params=params, timeout=10.0
            )

            if response.status_code == 200:
                return response.json()

            error_detail = response.json().get("detail", "Failed to get categories")
            raise HTTPException(status_code=response.status_code, detail=error_detail)

        except httpx.ConnectError:
            raise HTTPException(503, "Transaction service is unavailable")
        except httpx.TimeoutException:
            raise HTTPException(504, "Transactions service timeout")


@router.get(
    "/categories/{category_id}",
    response_model=CategoryResponse,
    summary="Получить категорию по ID",
    description="""
Получить категорию транзакций по её ID.

**Требует авторизации:** JWT токен в заголовке Authorization.
""",
    responses={
        200: {
            "description": "Категория",
            "content": {"application/json": {"example": {"id": 1, "name": "Продукты", "type": "expense"}}},
        },
        401: {"description": "Не авторизован"},
        404: {"description": "Категория не найдена"},
        503: {"description": "Сервис транзакций недоступен"},
        504: {"description": "Таймаут сервиса транзакций"},
    },
)
async def get_category_by_id(category_id: int, current_user: Dict[str, Any] = Depends(get_current_user)):
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(
                f"{TRANSACTIONS_SERVICE_URL}/transactions/categories/{category_id}", timeout=10.0
            )

            if response.status_code == 200:
                return response.json()

            error_detail = response.json().get("detail", "Failed to get category")
            raise HTTPException(status_code=response.status_code, detail=error_detail)

        except httpx.ConnectError:
            raise HTTPException(503, "Transaction service is unavailable")
        except httpx.TimeoutException:
            raise HTTPException(504, "Transactions service timeout")


@router.get(
    "/{transaction_id}",
    response_model=TransactionResponse,
    summary="Получить транзакцию по ID",
    description="""
Получить конкретную транзакцию пользователя по её UUID.

**Требует авторизации:** JWT токен в заголовке Authorization.

Возвращает только транзакции текущего пользователя.
""",
    responses={
        200: {
            "description": "Транзакция",
            "content": {
                "application/json": {
                    "example": {
                        "id": "550e8400-e29b-41d4-a716-446655440000",
                        "user_id": 1,
                        "bank_account_id": 1,
                        "category_id": 5,
                        "category_name": "Продукты",
                        "amount": 1500.50,
                        "created_at": "2024-01-15T14:30:00",
                        "type": "expense",
                        "description": "Покупка в супермаркете",
                        "merchant_id": 10,
                        "merchant_name": "Пятёрочка",
                    }
                }
            },
        },
        401: {"description": "Не авторизован"},
        404: {"description": "Транзакция не найдена"},
        503: {"description": "Сервис транзакций недоступен"},
        504: {"description": "Таймаут сервиса транзакций"},
    },
)
async def get_transaction_by_id(transaction_id: str, current_user: Dict[str, Any] = Depends(get_current_user)):
    user_id = current_user["user_id"]

    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(
                f"{TRANSACTIONS_SERVICE_URL}/transactions/{transaction_id}",
                headers={"X-User-ID": str(user_id)},
                timeout=10.0,
            )

            if response.status_code == 200:
                return response.json()

            error_detail = response.json().get("detail", "Failed to get transaction")
            raise HTTPException(status_code=response.status_code, detail=error_detail)

        except httpx.ConnectError:
            raise HTTPException(503, "Transaction service is unavailable")
        except httpx.TimeoutException:
            raise HTTPException(504, "Transactions service timeout")
