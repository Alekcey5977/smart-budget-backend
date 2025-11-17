import uuid
from sqlalchemy import Column, Integer, FLOAT, String, DateTime, ForeignKey, UUID
from sqlalchemy.orm import DeclarativeBase, relationship


class Transaction_Base(DeclarativeBase):
    pass


class Category(Transaction_Base):
    __tablename__ = "categories"
    
    mcc = Column(Integer, primary_key=True, index=True)
    group = Column(String(100), nullable=False)

    transactions = relationship("Transaction", back_populates="category")




class Transaction(Transaction_Base):
    __tablename__ = "transactions"

    id = Column(UUID(as_uuid=True), default=uuid.uuid4, nullable=False, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False, index=True)
    amount = Column(FLOAT, nullable=False)
    category_mcc = Column(Integer, ForeignKey("categories.mcc"), nullable=False)
    date_time = Column(DateTime, nullable=False)
    type = Column(String(30), nullable=False)

    category = relationship("Category", back_populates="transactions")

    def category_group(self) -> str:
        if self.category is None:
            return "Unknown"
        return self.category.group
