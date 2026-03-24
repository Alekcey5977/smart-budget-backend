import uuid

from sqlalchemy import INTEGER, UUID, Boolean, Column, DateTime, String, Text, func
from sqlalchemy.orm import DeclarativeBase


class Notification_Base(DeclarativeBase):
    pass


class Notification(Notification_Base):
    __tablename__ = "notifications"

    id = Column(UUID(as_uuid=True), default=uuid.uuid4, nullable=False, primary_key=True)
    user_id = Column(INTEGER, index=True)
    title = Column(String, nullable=False)
    body = Column(Text, nullable=False)
    is_read = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
