from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from datetime import datetime
from decimal import Decimal
from uuid import UUID
from typing import Self


class PurposeCreate(BaseModel):
    """Схема для создания цели"""
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "title": "Отпуск в Турции",
            "deadline": "2026-07-01T00:00:00",
            "total_amount": 100000.00
        }
    })

    title: str = Field(..., min_length=1, max_length=200, description="Название цели")
    deadline: datetime = Field(..., description="Дедлайн достижения цели")
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
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "title": "Отпуск в Греции",
            "amount": 25000.00
        }
    })

    title: str | None = Field(None, min_length=1, max_length=200, description="Новое название цели")
    deadline: datetime | None = Field(None, description="Новый дедлайн")
    amount: Decimal | None = Field(None, ge=0, description="Новая накопленная сумма")
    total_amount: Decimal | None = Field(None, gt=0, description="Новая целевая сумма")

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
    """Схема ответа с данными цели"""
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "id": "550e8400-e29b-41d4-a716-446655440000",
            "user_id": 1,
            "title": "Отпуск в Турции",
            "deadline": "2026-07-01T00:00:00",
            "amount": 15000.00,
            "total_amount": 100000.00,
            "created_at": "2026-01-15T10:30:00",
            "updated_at": "2026-01-20T14:20:00"
        }
    })

    id: UUID = Field(..., description="UUID цели")
    user_id: int = Field(..., description="ID пользователя")
    title: str = Field(..., description="Название цели")
    deadline: datetime = Field(..., description="Дедлайн достижения цели")
    amount: Decimal = Field(..., description="Текущая накопленная сумма")
    total_amount: Decimal = Field(..., description="Целевая сумма")
    created_at: datetime = Field(..., description="Дата создания")
    updated_at: datetime | None = Field(None, description="Дата последнего обновления")