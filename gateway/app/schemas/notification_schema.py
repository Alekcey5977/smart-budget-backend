from pydantic import BaseModel, Field
from datetime import datetime
from uuid import UUID


class NotificationResponse(BaseModel):
    """Схема ответа для уведомления"""
    id: UUID = Field(..., description="UUID уведомления")
    user_id: int = Field(..., description="ID пользователя")
    title: str = Field(..., description="Заголовок уведомления")
    body: str = Field(..., description="Текст уведомления")
    is_read: bool = Field(..., description="Прочитано ли уведомление")
    created_at: datetime = Field(..., description="Дата создания")

    class Config:
        json_schema_extra = {
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "user_id": 1,
                "title": "Добро пожаловать!",
                "body": "Ваш аккаунт успешно создан",
                "is_read": False,
                "created_at": "2026-01-21T10:30:00"
            }
        }


class UnreadCountResponse(BaseModel):
    """Схема ответа с количеством непрочитанных уведомлений"""
    count: int = Field(..., description="Количество непрочитанных уведомлений")

    class Config:
        json_schema_extra = {
            "example": {
                "count": 5
            }
        }


class MarkAsReadResponse(BaseModel):
    """Схема ответа при отметке уведомления как прочитанного"""
    status: str = Field(..., description="Статус операции")
    message: str = Field(..., description="Сообщение о результате")

    class Config:
        json_schema_extra = {
            "example": {
                "status": "success",
                "message": "Notification marked as read"
            }
        }
