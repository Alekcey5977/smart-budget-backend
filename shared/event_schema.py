from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class DomainEvent(BaseModel):
    """Общая схема события"""
    event_id: UUID
    event_type: str
    source: str
    timestamp: datetime
    payload: dict