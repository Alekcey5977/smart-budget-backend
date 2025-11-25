import uuid
from sqlalchemy import Column, Integer, FLOAT, String, DateTime, ForeignKey, UUID
from sqlalchemy.orm import DeclarativeBase, relationship


class Transaction_Base(DeclarativeBase):
    pass



class Category(Transaction_Base):
    __tablename__ = "categories"
    
    id = Column(Integer, nullable=False, primary_key=True, index=True)
    name = Column(String(100), nullable=False)

    mcc = relationship("MCC_Category", back_populates="category")
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

    transactions = relationship("Transaction", back_populates="merchant")

class Transaction(Transaction_Base):
    __tablename__ = "transactions"

    id = Column(UUID(as_uuid=True), default=uuid.uuid4, nullable=False, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False, index=True)
    category_id = Column(Integer, ForeignKey("categories.id"), nullable=False)
    amount = Column(FLOAT, nullable=False)
    created_at = Column(DateTime, nullable=False)
    type = Column(String(30), nullable=False)
    description = Column(String(200), nullable=True)
    merchant_id = Column(Integer, ForeignKey("merchants.id"), nullable=True)

    merchant = relationship("Merchant", back_populates="transactions")
    category = relationship("Category", back_populates="transactions")

    def category_group(self) -> str:
        if self.category is None:
            return "Unknown"
        return self.category.name
