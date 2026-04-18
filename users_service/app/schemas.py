import re
from datetime import datetime
from decimal import Decimal
from typing import Optional

from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel, EmailStr, Field, field_validator, model_validator

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/users/login")


class PasswordMixin:
    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("String should have at least 8 characters")
        if len(v) > 128:
            raise ValueError("String should have at most 128 characters")
        if not re.search(r"[A-Z]", v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not re.search(r"[a-z]", v):
            raise ValueError("Password must contain at least one lowercase letter")
        if not re.search(r"\d", v):
            raise ValueError("Password must contain at least one digit")
        if not re.search(r'[!@#$%^&*()_+\-=\[\]{};\':"\\|,.<>\/?`~]', v):
            raise ValueError("Password must contain at least one special character")
        return v


class UserBase(BaseModel):
    """Базовая схема пользователя"""

    email: EmailStr
    first_name: str
    last_name: str
    middle_name: Optional[str] = None

    @field_validator("first_name", "last_name")
    @classmethod
    def validate_required_name(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Name cannot be empty")
        if len(v) < 2:
            raise ValueError("Name must be at least 2 characters long")
        if len(v) > 50:
            raise ValueError("Name must be less than 50 characters")
        return v

    @field_validator("middle_name")
    @classmethod
    def validate_middle_name(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        v = v.strip()
        if not v:
            return None
        if len(v) < 2:
            raise ValueError("Middle name must be at least 2 characters long")
        if len(v) > 50:
            raise ValueError("Middle name must be less than 50 characters")
        return v

    @field_validator("email")
    @classmethod
    def normalize_email(cls, v: str) -> str:
        return v.lower()


class UserLogin(BaseModel, PasswordMixin):
    """Схема запроса авторизации"""

    email: EmailStr
    password: str = Field(..., min_length=8, description="Пароль (минимум 8 символа)")

    @field_validator("email")
    @classmethod
    def normalize_email(cls, v: str) -> str:
        return v.lower()


class UserCreate(UserBase, PasswordMixin):
    """Схема создания пользователя"""

    password: str = Field(..., min_length=8, description="Пароль (минимум 8 символа)")


class UserUpdate(BaseModel):
    """
    Схема обновления профиля пользователя.

    Все поля опциональные - можно обновить одно, несколько или все.
    Отчество можно установить как пустую строку для удаления.
    """

    first_name: Optional[str] = Field(None, description="Имя (2-50 символов)")
    last_name: Optional[str] = Field(None, description="Фамилия (2-50 символов)")
    middle_name: Optional[str] = Field(None, description="Отчество (пустая строка для удаления)")

    @field_validator("first_name", "last_name")
    @classmethod
    def validate_name(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        v = v.strip()
        if not v:
            raise ValueError("Name cannot be empty")
        if len(v) < 2:
            raise ValueError("Name must be at least 2 characters long")
        if len(v) > 50:
            raise ValueError("Name must be less than 50 characters")
        return v

    @field_validator("middle_name")
    @classmethod
    def validate_middle_name(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        v = v.strip()
        # Пустая строка означает удаление отчества
        if not v:
            return ""
        if len(v) < 2:
            raise ValueError("Middle name must be at least 2 characters long")
        if len(v) > 50:
            raise ValueError("Middle name must be less than 50 characters")
        return v

    @model_validator(mode="after")
    def check_at_least_one_field(self):
        if self.first_name is None and self.last_name is None and self.middle_name is None:
            raise ValueError("At least one field must be provided")
        return self


class UserResponse(BaseModel):
    """Схема ответа с данными пользователя"""

    id: int
    email: EmailStr
    first_name: str
    last_name: str
    middle_name: Optional[str] = None
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime] = None


class Token(BaseModel):
    """Схема токена"""

    access_token: str
    token_type: str


class TokenData(BaseModel):
    """Схема данных токена"""

    user_id: int = None


class Bank_AccountCreate(BaseModel):
    """Схема создания банковского счета"""

    bank_account_number: str
    bank_account_name: str | None = None
    bank: str


class Bank_accountResponse(BaseModel):
    """Схема банковского счета"""

    bank_account_id: int
    bank_account_name: str | None
    currency: str
    bank: str
    balance: Decimal
