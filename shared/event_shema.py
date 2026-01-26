from pydantic import BaseModel
from uuid import UUID
from datetime import datetime


class DomainEvent(BaseModel):
    """Общая схема события"""
    event_id: UUID
    event_type: str
    source: str
    timestamp: datetime
    dict