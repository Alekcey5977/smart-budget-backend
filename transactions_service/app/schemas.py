from pydantic import BaseModel, ConfigDict, Field, field_validator
from datetime import datetime
from typing import Optional, List
import uuid


# ===========================
# Request Schemas
# ===========================

class TransactionFilterRequest(BaseModel):
    """Схема запроса фильтрации транзакций"""
    transaction_type: Optional[str] = Field(
        None,
        description="Тип транзакции: 'income' или 'expense'"
    )
    category_ids: Optional[List[int]] = Field(
        None,
        description="Список ID категорий для фильтрации"
    )
    start_date: Optional[datetime] = Field(
        None,
        description="Начальная дата периода"
    )
    end_date: Optional[datetime] = Field(
        None,
        description="Конечная дата периода"
    )
    min_amount: Optional[float] = Field(
        None,
        ge=0,
        description="Минимальная сумма"
    )
    max_amount: Optional[float] = Field(
        None,
        ge=0,
        description="Максимальная сумма"
    )
    merchant_ids: Optional[List[int]] = Field(
        None,
        description="Список ID мерчантов"
    )
    limit: int = Field(..., ge=1, le=1000)
    offset: int = Field(0, ge=0)

    @field_validator('transaction_type')
    @classmethod
    def validate_type(cls, v):
        if v is not None and v not in ['income', 'expense']:
            raise ValueError('Type must be "income" or "expense"')
        return v


# ===========================
# Response Schemas
# ===========================

class TransactionResponse(BaseModel):
    """Схема ответа транзакции"""
    id: uuid.UUID
    user_id: int
    category_id: int
    category_name: Optional[str] = None
    amount: float
    created_at: datetime
    type: str
    description: Optional[str] = None
    merchant_id: Optional[int] = None
    merchant_name: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class CategoryResponse(BaseModel):
    """Схема ответа категории"""
    id: int
    name: str

    model_config = ConfigDict(from_attributes=True)


class MccCategoryResponse(BaseModel):
    """Схема ответа MCC категории"""
    mcc: int
    name: str
    category_id: int

    model_config = ConfigDict(from_attributes=True)


class MerchantResponse(BaseModel):
    """Схема ответа мерчанта"""
    id: int
    name: str
    inn: str
    mcc_id: Optional[int] = None

    model_config = ConfigDict(from_attributes=True)
