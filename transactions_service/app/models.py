from enum import Enum
import uuid
from sqlalchemy import Column, Integer, DECIMAL, String, DateTime, ForeignKey, UUID, func
from sqlalchemy.orm import DeclarativeBase, relationship
from sqlalchemy import Enum as SAEnum


class Transaction_Base(DeclarativeBase):
    pass



class Category(Transaction_Base):
    __tablename__ = "categories"
    
    id = Column(Integer, nullable=False, primary_key=True, index=True)
    name = Column(String(100), nullable=False)

    mcc = relationship("MCC_Category", back_populates="category")
    merchants = relationship("Merchant", back_populates="category")
    transactions = relationship("Transaction", back_populates="category")



class MCC_Category(Transaction_Base):
    __tablename__ = "mcc_categories"

    mcc = Column(Integer, nullable=False, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    category_id = Column(Integer, ForeignKey("categories.id"), nullable=False)

    category = relationship("Category", back_populates="mcc")


class Merchant(Transaction_Base):
    __tablename__ = "merchants"

    id = Column(Integer, nullable=False, primary_key=True, index=True)
    name = Column(String(200), nullable=False)
    inn = Column(String(100), nullable=False)
    category_id = Column(Integer, ForeignKey("categories.id"), nullable=False)

    category = relationship("Category", back_populates="merchants")
    transactions = relationship("Transaction", back_populates="merchant")



class Bank(Transaction_Base):
    __tablename__ = "banks"
    
    id = Column(Integer, nullable=False, primary_key=True, index=True)
    name = Column(String(50), nullable=False)

    bank_accounts = relationship("Bank_Account", back_populates="bank")


class Bank_Account(Transaction_Base):
    __tablename__ = "bank_accounts"

    id = Column(Integer, nullable=False, primary_key=True, index=True)
    account_number = Column(String(60), nullable=False, unique=True, index=True)
    bank_id = Column(Integer, ForeignKey("banks.id"), nullable=False)
    currency = Column(String(3), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    bank = relationship("Bank", back_populates="bank_accounts")
    transactions = relationship("Transaction", back_populates="bank_account")



class Transaction(Transaction_Base):
    __tablename__ = "transactions"

    id = Column(UUID(as_uuid=True), default=uuid.uuid4, nullable=False, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False, index=True)
    category_id = Column(Integer, ForeignKey("categories.id"), nullable=False)
    bank_account_id = Column(Integer, ForeignKey("bank_accounts.id"), nullable=False)
    amount = Column(DECIMAL(12, 2), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    type = Column(String(30), nullable=False)
    description = Column(String(200), nullable=True)
    merchant_id = Column(Integer, ForeignKey("merchants.id"), nullable=True)

    bank_account = relationship("Bank_Account", back_populates="transactions")
    merchant = relationship("Merchant", back_populates="transactions")
    category = relationship("Category", back_populates="transactions")

    def category_group(self) -> str:
        if self.category is None:
            return "Unknown"
        return self.category.name
