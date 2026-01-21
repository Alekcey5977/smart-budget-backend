from pydantic import BaseModel, Field
from datetime import datetime
from decimal import Decimal
from uuid import UUID


class PurposeCreate(BaseModel):
    """Схема для создания цели"""
    title: str
    deadline: datetime
    amount: Decimal = Field(..., ge=0)
    total_amount: Decimal = Field(0, ge=0)


class PurposeUpdate(BaseModel):
    """Схема для обновления цели"""
    title: str | None = None
    deadline: datetime | None = None
    amount: Decimal | None = Field(None, ge=0)
    total_amount: Decimal | None = Field(None, ge=0)


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
