from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class NotificationCreate(BaseModel):
    """Схема для создания уведомления"""

    user_id: int
    title: str
    body: str


class NotificationResponse(BaseModel):
    """Схема ответа для уведомления"""

    id: UUID
    user_id: int
    title: str
    body: str
    is_read: bool
    created_at: datetime
