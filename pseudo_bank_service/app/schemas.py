from decimal import Decimal
from typing import Optional
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel, EmailStr, Field, field_validator, model_validator
from datetime import datetime


class Validate_Bank_Account(BaseModel):
    """Схема хэша счёта карты"""
    bank_account_hash: str