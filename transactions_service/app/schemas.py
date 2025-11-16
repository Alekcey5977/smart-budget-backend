from pydantic import BaseModel, ConfigDict, Field, field_validator
from datetime import datetime
import uuid

# TODO написать схемы для других ручек, например, для создания транзакции вручную

class TransactionBase(BaseModel):
    amount: float
    category_mcc: int = Field(..., ge=1000, le=9999)
    date_time: datetime
    type: str

    model_config = ConfigDict(from_attributes=True)

    @field_validator('amount')
    @classmethod
    def validate_amount(cls, v):
        """Проверка, что сумма не нулевая и в допустимом пределе"""
        if v == 0:
            raise ValueError('Amount cannot be zero')
        if abs(v) > 10_000_000:
            raise ValueError('Amount is too large')
        if abs(v) < 0.01:
            raise ValueError('Amount is too small')
        return v
    
    @field_validator('category_mcc')
    @classmethod
    def validate_category_mcc(cls, v):
        """Проверка MCC кода"""
        if not (1000 <= v <= 9999):
            raise ValueError('MCC code must be between 1000 and 9999')
        return v

    @field_validator('type')
    @classmethod
    def validate_type(cls, v):
        """Проверка типа транзакции"""
        if v not in ['income', 'expense']:
            raise ValueError('Type must be "income" or "expense"')
        
        return v

    @field_validator('date_time')
    @classmethod
    def validate_date_time(cls, v):
        """Проверка, что дата не в будущем"""
        if v > datetime.now():
            raise ValueError('Transaction date cannot be in the future')

        return v


class TransactionResponse(TransactionBase):
    id: uuid.UUID
    user_id: int
