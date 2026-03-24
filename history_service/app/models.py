import uuid

from sqlalchemy import INTEGER, UUID, Column, DateTime, String, Text, func
from sqlalchemy.orm import DeclarativeBase


class History_Base(DeclarativeBase):
    pass


class HistoryEntry(History_Base):
    __tablename__ = "history_entries"

    id = Column(UUID(as_uuid=True), default=uuid.uuid4, nullable=False, primary_key=True)
    user_id = Column(INTEGER, index=True)
    title = Column(String, nullable=False)
    body = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
