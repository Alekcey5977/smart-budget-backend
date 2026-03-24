from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class HistoryEntryCreate(BaseModel):
    user_id: int
    title: str
    body: str


class HistoryEntryResponse(BaseModel):
    id: UUID
    user_id: int
    title: str
    body: str
    created_at: datetime


class DeleteResponse(BaseModel):
    status: str
    message: str
