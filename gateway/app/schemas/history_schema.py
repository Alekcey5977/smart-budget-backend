from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class HistoryEntryResponse(BaseModel):
    """Схема ответа для записи истории"""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "user_id": 1,
                "title": "Цель создана",
                "body": "Цель «Отпуск» на сумму 100000 руб. создана",
                "created_at": "2026-01-21T10:30:00",
            }
        }
    )

    id: UUID = Field(..., description="UUID записи")
    user_id: int = Field(..., description="ID пользователя")
    title: str = Field(..., description="Заголовок записи")
    body: str = Field(..., description="Текст записи")
    created_at: datetime = Field(..., description="Дата создания")


class DeleteResponse(BaseModel):
    """Схема ответа при удалении записи"""

    status: str = Field(..., description="Статус операции")
    message: str = Field(..., description="Сообщение о результате")
