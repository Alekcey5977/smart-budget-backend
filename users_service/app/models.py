from sqlalchemy import DECIMAL, Column, ForeignKey, Integer, String, DateTime, Boolean
from sqlalchemy.orm import DeclarativeBase, relationship
from sqlalchemy.sql import func


class User_Base(DeclarativeBase):
    pass


class User(User_Base):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    first_name = Column(String, nullable=False)
    last_name = Column(String, nullable=False)
    middle_name = Column(String, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    bank_accounts = relationship("Bank_Accounts", back_populates="user")


class Bank_Accounts(User_Base):
    __tablename__ = 'bank_accounts'

    bank_account_id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    bank_account_number = Column(String(34), nullable=False)
    currency = Column(String(3), nullable=False)
    bank = Column(String, nullable=False)
    balance = Column(DECIMAL(12, 2), nullable=False, default=0.00)

    user = relationship("User", back_populates="bank_accounts")
