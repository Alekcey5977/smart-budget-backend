from sqlalchemy import DECIMAL, Boolean, Column, DateTime, ForeignKey, Integer, String
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


class Bank(User_Base):
    __tablename__ = 'banks'

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), nullable=False, unique=True)

    bank_accounts = relationship("Bank_Accounts", back_populates="bank")


class Bank_Accounts(User_Base):
    __tablename__ = 'bank_accounts'

    bank_account_id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    bank_account_hash = Column(String(64), nullable=False)
    bank_account_name = Column(String(100), nullable=False)
    currency = Column(String(3), nullable=False)
    bank_id = Column(Integer, ForeignKey("banks.id"), nullable=False)
    balance = Column(DECIMAL(12, 2), nullable=False, default=0.00)

    user = relationship("User", back_populates="bank_accounts")
    bank = relationship("Bank", back_populates="bank_accounts")