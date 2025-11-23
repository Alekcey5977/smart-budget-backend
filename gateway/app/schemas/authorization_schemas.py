from pydantic import BaseModel, EmailStr, Field, field_validator, model_validator
from typing import Optional


class RegisterRequest(BaseModel):
    """Схема запроса регистрации пользователя"""
    email: EmailStr
    password: str = Field(..., min_length=2, description="Пароль (минимум 2 символа)")
    first_name: str
    last_name: str
    middle_name: Optional[str] = Field(None, description="Отчество (необязательно)")

    @field_validator('password')
    @classmethod
    def validate_password(cls, v: str) -> str:
        if len(v) < 2:
            raise ValueError('Password must be at least 2 characters long')
        return v

    @field_validator('first_name', 'last_name')
    @classmethod
    def validate_required_name(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError('Name cannot be empty')
        if len(v) < 2:
            raise ValueError('Name must be at least 2 characters long')
        if len(v) > 50:
            raise ValueError('Name must be less than 50 characters')
        return v

    @field_validator('middle_name')
    @classmethod
    def validate_middle_name(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        v = v.strip()
        if not v:
            return None
        if len(v) < 2:
            raise ValueError('Middle name must be at least 2 characters long')
        if len(v) > 50:
            raise ValueError('Middle name must be less than 50 characters')
        return v


class UserLogin(BaseModel):
    """Схема запроса авторизации"""
    email: EmailStr
    password: str = Field(..., min_length=2, description="Пароль (минимум 2 символа)")

    @field_validator('password')
    @classmethod
    def validate_password(cls, v: str) -> str:
        if len(v) < 2:
            raise ValueError('Password must be at least 2 characters long')
        return v


class UserUpdateRequest(BaseModel):
    """
    Схема запроса обновления профиля.

    Все поля опциональные - можно обновить одно, несколько или все.
    Отчество можно установить как пустую строку для удаления.
    """
    first_name: Optional[str] = Field(None, description="Имя (2-50 символов)")
    last_name: Optional[str] = Field(None, description="Фамилия (2-50 символов)")
    middle_name: Optional[str] = Field(None, description="Отчество (пустая строка для удаления)")

    @field_validator('first_name', 'last_name')
    @classmethod
    def validate_name(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        v = v.strip()
        if not v:
            raise ValueError('Name cannot be empty')
        if len(v) < 2:
            raise ValueError('Name must be at least 2 characters long')
        if len(v) > 50:
            raise ValueError('Name must be less than 50 characters')
        return v

    @field_validator('middle_name')
    @classmethod
    def validate_middle_name(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        v = v.strip()
        # Пустая строка означает удаление отчества
        if not v:
            return ""
        if len(v) < 2:
            raise ValueError('Middle name must be at least 2 characters long')
        if len(v) > 50:
            raise ValueError('Middle name must be less than 50 characters')
        return v

    @model_validator(mode='after')
    def check_at_least_one_field(self):
        if self.first_name is None and self.last_name is None and self.middle_name is None:
            raise ValueError('At least one field must be provided')
        return self


class TokenResponse(BaseModel):
    """Схема ответа с токеном"""
    access_token: str
    token_type: str
