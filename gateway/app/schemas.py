from pydantic import BaseModel, EmailStr, field_validator

class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    first_name: str
    last_name: str

class UserUpdateRequest(BaseModel):
    first_name: str
    last_name: str 
    
    @field_validator('first_name', 'last_name')
    @classmethod
    def validate_name(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError('Name cannot be empty')
        if len(v) < 2:
            raise ValueError('Name must be at least 2 characters long')
        if len(v) > 50:
            raise ValueError('Name must be less than 50 characters')
        return v