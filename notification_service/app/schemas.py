from pydantic import BaseModel
from datetime import datetime
from uuid import UUID
from typing import Optional


class NotificationCreate(BaseModel):
    """Схема для создания уведомления"""
    user_id: str
    title: str
    body: str


class NotificationResponse(BaseModel):
    """Схема ответа для уведомления"""
    id: UUID
    user_id: str
    title: str
    body: str
    is_read: bool
    created_at: datetime
    read_at: Optional[datetime] = None


class NotificationRead(BaseModel):
    """Схема для отметки уведомления как прочитанного"""
    user_id: int
