from pydantic import BaseModel, Field
from datetime import datetime
from decimal import Decimal
from uuid import UUID


class PurposeCreate(BaseModel):
    """Схема для создания цели"""
    title: str = Field(..., min_length=1, max_length=200, description="Название цели")
    deadline: datetime = Field(..., description="Дедлайн достижения цели")
    amount: Decimal = Field(..., ge=0, description="Текущая накопленная сумма")
    total_amount: Decimal = Field(0, ge=0, description="Целевая сумма")

    class Config:
        json_schema_extra = {
            "example": {
                "title": "Отпуск в Турции",
                "deadline": "2026-07-01T00:00:00",
                "amount": 15000.00,
                "total_amount": 100000.00
            }
        }


class PurposeUpdate(BaseModel):
    """Схема для обновления цели"""
    title: str | None = Field(None, min_length=1, max_length=200, description="Новое название цели")
    deadline: datetime | None = Field(None, description="Новый дедлайн")
    amount: Decimal | None = Field(None, ge=0, description="Новая накопленная сумма")
    total_amount: Decimal | None = Field(None, ge=0, description="Новая целевая сумма")

    class Config:
        json_schema_extra = {
            "example": {
                "title": "Отпуск в Греции",
                "amount": 25000.00
            }
        }


class PurposeResponse(BaseModel):
    """Схема ответа с данными цели"""
    id: UUID = Field(..., description="UUID цели")
    user_id: int = Field(..., description="ID пользователя")
    title: str = Field(..., description="Название цели")
    deadline: datetime = Field(..., description="Дедлайн достижения цели")
    amount: Decimal = Field(..., description="Текущая накопленная сумма")
    total_amount: Decimal = Field(..., description="Целевая сумма")
    created_at: datetime = Field(..., description="Дата создания")
    updated_at: datetime | None = Field(None, description="Дата последнего обновления")

    class Config:
        json_schema_extra = {
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
        }
