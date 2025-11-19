from pydantic import BaseModel, EmailStr, field_validator
from typing import Optional

class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    first_name: str
    last_name: str
    patronymic: Optional[str] = None

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserUpdateRequest(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    patronymic: Optional[str] = None
    
    @field_validator('first_name', 'last_name')
    @classmethod
    def validate_name_length(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError('Name cannot be empty')
        if len(v) < 2:
            raise ValueError('Name must be at least 2 characters long')
        if len(v) > 50:
            raise ValueError('Name must be less than 50 characters')
        return v
    
    @field_validator('patronymic')
    @classmethod
    def validate_patronymic(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        v = v.strip()
        if not v:  # Пустая строка становится None
            return None
        if len(v) < 2:
            raise ValueError('Patronymic must be at least 2 characters long')
        if len(v) > 50:
            raise ValueError('Patronymic must be less than 50 characters')
        return v  

class TokenResponse(BaseModel):
    access_token: str
    token_type: str