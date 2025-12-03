from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime

class TransactionFilterRequest(BaseModel):
    """Схема фильтрации транзакций"""
    transaction_type: Optional[str] = Field(
        None,
        description="Тип транзакции: 'income' или 'expense'",
        pattern="^(income|expense)$"
    )
    category_ids: Optional[List[int]] = Field(
        None,
        description="Список ID категорий для фильтрации"
    )
    start_date: Optional[datetime] = Field(
        None,
        description="Начальная дата периода (ISO 8601)"
    )
    end_date: Optional[datetime] = Field(
        None,
        description="Конечная дата периода (ISO 8601)"
    )
    min_amount: Optional[float] = Field(
        None,
        ge=0,
        description="Минимальная сумма транзакции"
    )
    max_amount: Optional[float] = Field(
        None,
        ge=0,
        description="Максимальная сумма транзакции"
    )
    merchant_ids: Optional[List[int]] = Field(
        None,
        description="Список ID мерчантов для фильтрации"
    )
    limit: int = Field(
        ...,
        ge=1,
        le=100,
        description="Количество записей на странице"
    )
    offset: int = Field(
        0,
        ge=0,
        description="Смещение для пагинации"
    )


class TransactionResponse(BaseModel):
    """Схема ответа транзакции"""
    id: str
    user_id: int
    category_id: int
    category_name: Optional[str] = None
    amount: float
    created_at: datetime
    type: str
    description: Optional[str] = None
    merchant_id: Optional[int] = None
    merchant_name: Optional[str] = None


class CategoryResponse(BaseModel):
    """Схема ответа категории"""
    id: int
    name: str