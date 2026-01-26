import uuid
from datetime import datetime
from sqlalchemy import Boolean, Column, Integer, String, DateTime, UUID, DECIMAL, Text, func
from sqlalchemy.orm import DeclarativeBase


class Notification_Base(DeclarativeBase):
    pass


class Notification(Notification_Base):
    __tablename__ = "notifications"

    id = Column(UUID(as_uuid=True), default=uuid.uuid4, nullable=False, primary_key=True)
    user_id = Column(String, index=True)
    title = Column(String, nullable=False)
    body = Column(Text, nullable=False)
    is_read = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
