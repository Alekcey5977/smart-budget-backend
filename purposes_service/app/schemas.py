from datetime import datetime
from decimal import Decimal
from typing import Self
from uuid import UUID

from pydantic import BaseModel, Field, field_validator, model_validator


class PurposeCreate(BaseModel):
    """Схема для создания цели"""
    title: str
    deadline: datetime
    total_amount: Decimal = Field(..., gt=0, description="Целевая сумма (должна быть больше 0)")

    @field_validator('deadline')
    @classmethod
    def validate_deadline_in_future(cls, v: datetime) -> datetime:
        """Проверка, что дедлайн в будущем"""
        if v <= datetime.now():
            raise ValueError('Дедлайн должен быть в будущем')
        return v


class PurposeUpdate(BaseModel):
    """Схема для обновления цели"""
    title: str | None = None
    deadline: datetime | None = None
    amount: Decimal | None = Field(None, ge=0)
    total_amount: Decimal | None = Field(None, ge=0)

    @field_validator('deadline')
    @classmethod
    def validate_deadline_in_future(cls, v: datetime | None) -> datetime | None:
        """Проверка, что дедлайн в будущем (если указан)"""
        if v is not None and v <= datetime.now():
            raise ValueError('Дедлайн должен быть в будущем')
        return v

    @model_validator(mode='after')
    def validate_amount_less_than_total(self) -> Self:
        """Проверка, что накопленная сумма не превышает целевую (если оба указаны)"""
        if self.amount is not None and self.total_amount is not None:
            if self.amount > self.total_amount:
                raise ValueError('Накопленная сумма не может превышать целевую сумму')
        return self


class PurposeResponse(BaseModel):
    """Схема ответа на запрос цели"""
    id: UUID
    user_id: int
    title: str
    deadline: datetime
    amount: Decimal
    total_amount: Decimal
    created_at: datetime
    updated_at: datetime | None = None
