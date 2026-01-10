from pydantic import BaseModel


class Validate_Bank_Account(BaseModel):
    """Схема хэша счёта карты"""
    bank_account_hash: str