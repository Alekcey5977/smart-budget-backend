from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import DeclarativeBase, relationship



class Base(DeclarativeBase):
    pass



class Category(Base):
    __tablename__ = "categories"
    
    mcc = Column(Integer, primary_key=True, index=True)
    group = Column(String(100), nullable=False)

    transactions = relationship("Transactions", back_populates="category")




class Transactions(Base):
    __tablename__ = "transactions"

    user_id = Column(Integer, primary_key=True, index=True)
    amount = Column(Integer, nullable=False)
    category_mcc = Column(Integer, ForeignKey("categories.mcc"), nullable=False)
    date_time = Column(DateTime, nullable=False)
    type = Column(String(30), nullable=False)

    category = relationship("Category", back_populates="transactions")
