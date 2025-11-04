from fastapi import APIRouter, Depends, HTTPException, Header, Form
import httpx
import os
from typing import Dict
from fastapi.security import OAuth2PasswordBearer

from app.schemas import UserCreate, UserUpdate, UserLogin, Token, UserResponse
from app.dependencies import get_current_user # Импортируем dependency

# Создаем роутер с префиксом /auth и тегом для Swagger документации
router = APIRouter(
    prefix="/auth",
    tags=["authentication"]
)

# Подключаем схему безопасности — теперь Swagger покажет кнопку Authorize
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

# Получаем URL сервиса пользователей из переменных окружения
USERS_SERVICE_URL = os.getenv("USERS_SERVICE_URL")

# ----------------------------
# Регистрация пользователя
# ----------------------------
@router.post("/register", response_model=UserResponse)
async def register(user_data: UserCreate):
    """
    Регистрация нового пользователя.
    
    **Поля для ввода (JSON):**
    - email: EmailStr
    - password: str
    
    Проксирует запрос в users-service и возвращает результат.
    """
    async with httpx.AsyncClient() as client:
        try:
            # Проксируем запрос к users-service
            response = await client.post(
                f"{USERS_SERVICE_URL}/users/register",  # Эндпоинт регистрации
                json=user_data.dict(),
                timeout=30.0                            # Увеличенный таймаут для регистрации
            )
            
            # Если users-service вернул ошибку - пробрасываем ее
            if response.status_code >= 400:
                error_detail = response.json().get("detail", "Registration failed")
                raise HTTPException(
                    status_code=response.status_code,
                    detail=error_detail
                )
            
            # Возвращаем успешный ответ от users-service
            return response.json()
            
        except httpx.ConnectError:
            raise HTTPException(
                status_code=503,
                detail="Users service is currently unavailable. Please try again later."
            )

# ----------------------------
# Вход пользователя
# ----------------------------
@router.post("/login", response_model=Token)
async def login(
    username: str = Form(...),
    password: str = Form(...)
):
    """
    Аутентификация пользователя.
    
    **Поля для ввода (JSON):**
    - email: EmailStr
    - password: str
    
    Возвращает JWT токен:
    - access_token
    - token_type
    """
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{USERS_SERVICE_URL}/users/login",
            json={"email": username, "password": password},
            timeout=15.0
        )

        if response.status_code >= 400:
            error_detail = response.json().get("detail", "Login failed")
            raise HTTPException(status_code=response.status_code, detail=error_detail)
            
        response.raise_for_status()

        return response.json()

# ----------------------------
# Получение данных текущего пользователя
# ----------------------------
@router.get("/me", response_model=UserResponse)
async def get_me(current_user: Dict = Depends(get_current_user)):
    """
    Получение данных текущего пользователя.
    """
    return current_user["user"]  # <-- возвращаем только данные пользователя

# ----------------------------
# Обновление профиля текущего пользователя
# ---------------------------
@router.put("/me", response_model=UserResponse)
async def update_me(update_data: UserUpdate, current_user: Dict = Depends(get_current_user)):
    """
    Обновление профиля текущего пользователя.
    """
    token = current_user["token"]
    
    async with httpx.AsyncClient() as client:
        response = await client.put(
            f"{USERS_SERVICE_URL}/users/me",
            json=update_data.dict(exclude_unset=True),
            params={"token": token},
            timeout=15.0
        )
        if response.status_code >= 400:
            raise HTTPException(
                status_code=response.status_code,
                detail=response.json().get("detail", "Update failed")
            )
        
        # Возвращаем только данные пользователя
        return response.json()
        

@router.get("/test")
async def test_auth_router():
    """
    Тестовый эндпоинт для проверки работы auth роутера
    """
    return {
        "message": "Auth router is working correctly",
        "status": "success",
        "service": "gateway-auth"
    }

#Пока не работает, просто заглушка для будущей функциональности
@router.post("/refresh")
async def refresh_token(refresh_data: Dict[str, str]):
    """
    Обновление JWT токена (будет добавлено позже)
    Пока заглушка для будущей функциональности
    """
    return {"message": "Token refresh endpoint - to be implemented"}