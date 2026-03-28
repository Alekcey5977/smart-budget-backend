from datetime import datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, Field


class Validate_Bank_Account(BaseModel):
    """Схема хэша счёта карты"""
    bank_account_hash: str


class CategoryCreate(BaseModel):
    """Схема для создания категории"""
    id: int
    name: str = Field(..., max_length=100)
    type: Optional[str] = Field(None, max_length=10)


class MCCCategoryCreate(BaseModel):
    """Схема для создания MCC категории"""
    mcc: int
    name: str = Field(..., max_length=100)
    category_id: int


class MerchantCreate(BaseModel):
    """Схема для создания мерчанта"""
    id: int
    name: str = Field(..., max_length=200)
    inn: str = Field(..., max_length=100)
    category_id: int


class BankCreate(BaseModel):
    """Схема для создания банка"""
    id: int
    name: str = Field(..., max_length=50)


class BankAccountCreate(BaseModel):
    """Схема для создания банковского счета"""
    user_id: int
    bank_account_hash: str = Field(..., max_length=64)
    bank_account_name: str = Field(..., max_length=100)
    bank_id: int
    currency: str = Field(default="RUB", max_length=3)
    balance: Decimal = Field(default=Decimal("0.00"))


class TransactionCreate(BaseModel):
    """Схема для создания транзакции"""
    user_id: int
    category_id: int
    bank_account_id: int
    amount: Decimal
    type: str = Field(..., max_length=30)
    description: Optional[str] = Field(None, max_length=200)
    merchant_id: Optional[int] = None
    created_at: Optional[datetime] = None