import uuid
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

# ===========================
# Request Schemas
# ===========================


class TransactionFilterRequest(BaseModel):
    """Схема запроса фильтрации транзакций"""

    transaction_type: Optional[str] = Field(None, description="Тип транзакции: 'income' или 'expense'")
    category_ids: Optional[List[int]] = Field(None, description="Список ID категорий для фильтрации")
    start_date: Optional[datetime] = Field(None, description="Начальная дата периода")
    end_date: Optional[datetime] = Field(None, description="Конечная дата периода")
    min_amount: Optional[float] = Field(None, ge=0, description="Минимальная сумма")
    max_amount: Optional[float] = Field(None, ge=0, description="Максимальная сумма")
    merchant_ids: Optional[List[int]] = Field(None, description="Список ID мерчантов")
    bank_account_ids: Optional[List[int]] = Field(None, description="Список ID банковских счетов")
    limit: int = Field(..., ge=1, le=1000)
    offset: int = Field(0, ge=0)

    @field_validator("transaction_type")
    @classmethod
    def validate_type(cls, v):
        if v is not None and v not in ["income", "expense"]:
            raise ValueError('Type must be "income" or "expense"')
        return v


# ===========================
# Response Schemas
# ===========================


class TransactionResponse(BaseModel):
    """Схема ответа транзакции"""

    id: uuid.UUID
    user_id: int
    bank_account_id: int
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
    type: Optional[str] = None

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


class UpdateTransactionCategoryRequest(BaseModel):
    """Схема запроса изменения категории транзакции"""

    category_id: int = Field(..., gt=0, description="ID новой категории")


class CategorySummaryRequest(BaseModel):
    """Схема запроса сумм по категориям"""

    transaction_type: Optional[str] = Field(None, description="Тип: 'income' или 'expense'. Без параметра — всё")
    start_date: Optional[datetime] = Field(None, description="Начало периода")
    end_date: Optional[datetime] = Field(None, description="Конец периода")

    @field_validator("transaction_type")
    @classmethod
    def validate_type(cls, v):
        if v is not None and v not in ["income", "expense"]:
            raise ValueError('Type must be "income" or "expense"')
        return v


class CategorySummaryResponse(BaseModel):
    """Сумма транзакций по одной категории"""

    category_id: int
    category_name: str
    total_amount: float
    transaction_count: int

    model_config = ConfigDict(from_attributes=True)


class SyncTriggerRequest(BaseModel):
    bank_account_hash: str
    user_id: int
