from sqlalchemy import DECIMAL, UUID, Column, DateTime, Integer, String, func
from sqlalchemy.orm import DeclarativeBase


class Purpose_Base(DeclarativeBase):
    pass


class Purpose(Purpose_Base):
    __tablename__ = "purposes"

    id = Column(UUID, primary_key=True, index=True, nullable=False)
    user_id = Column(Integer, index=True, nullable=False)
    title = Column(String, nullable=False)
    deadline = Column(DateTime, nullable=False)
    total_amount = Column(DECIMAL(12, 2), nullable=False)
    amount = Column(DECIMAL(12, 2), nullable=False, default=0.0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
