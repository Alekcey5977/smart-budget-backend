from typing import Optional
from pydantic import BaseModel, EmailStr, field_validator, model_validator
from datetime import datetime

class UserBase(BaseModel):
    email: EmailStr
    first_name: str
    last_name: str
    patronymic: str

    @field_validator('first_name', 'last_name', 'patronymic')
    @classmethod
    def validate_name_not_empty(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError('Name cannot be empty')
        if len(v) < 2:
            raise ValueError('Name must be at least 2 characters long')
        if len(v) > 50:
            raise ValueError('Name must be less than 50 characters')
        return v

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserCreate(UserBase):
    password: str


class UserUpdate(BaseModel):
    first_name: str
    last_name: str
    patronymic: str

    @field_validator('first_name', 'last_name', 'patronymic')
    @classmethod
    def validate_name_length(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            v = v.strip()
            if not v:
                raise ValueError('Name cannot be empty')
            if len(v) < 2:
                raise ValueError('Name must be at least 2 characters long')
            if len(v) > 50:
                raise ValueError('Name must be less than 50 characters')
        return v

class UserResponse(UserBase):
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime] = None


class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    user_id: int = None
