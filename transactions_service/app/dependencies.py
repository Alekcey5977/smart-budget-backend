# app/dependencies/auth.py
from fastapi import Header, HTTPException
from typing import Annotated


async def get_user_id_from_header(
    x_user_id: Annotated[str, Header(..., alias="X-User-ID")]
) -> int:
    """Извлекает user_id из заголовка X-User-ID"""
    try:
        user_id = int(x_user_id)
        if user_id <= 0:
            raise ValueError("User ID must be positive")
        return user_id
    
    except (ValueError, TypeError):
        raise HTTPException(
            status_code=400,
            detail="Invalid user ID in headers"
        )
