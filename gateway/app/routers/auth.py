from fastapi import APIRouter, Depends, HTTPException
import httpx
import os
from typing import Dict, Any
from fastapi.security import OAuth2PasswordBearer
from fastapi import Form

from app.dependencies import get_current_user # Импортируем dependency

# Создаем роутер с префиксом /auth и тегом для Swagger документации
router = APIRouter(
    prefix="/auth",
    tags=["authentication"]
)

# Подключаем схему безопасности — теперь Swagger покажет кнопку Authorize 🔒
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

# Получаем URL сервиса пользователей из переменных окружения
USERS_SERVICE_URL = os.getenv("USERS_SERVICE_URL")

@router.post("/register")
async def register(user_data: Dict[Any, Any]):
    """
    Регистрация нового пользователя
    Принимает данные пользователя и проксирует запрос в users-service
    
    Flow:
    1. Получает JSON с данными пользователя от клиента
    2. Отправляет эти данные в users-service
    3. Возвращает ответ от users-service обратно клиенту
    """
    async with httpx.AsyncClient() as client:
        try:
            # Проксируем запрос к users-service
            response = await client.post(
                f"{USERS_SERVICE_URL}/users/register",  # Эндпоинт регистрации
                json=user_data,                         # Тело запроса
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
        
@router.post("/login")
async def login(
    username: str = Form(...),
    password: str = Form(...)
):
    """
    Аутентификация пользователя
    Принимает email и пароль, возвращает JWT токен
    
    Flow:
    1. Получает credentials от клиента
    2. Отправляет их в users-service для проверки
    3. Возвращает JWT токен если аутентификация успешна
    """
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                f"{USERS_SERVICE_URL}/users/login",
                json={"email": username, "password": password},
                timeout=15.0
            )

            if response.status_code >= 400:
                error_detail = response.json().get("detail", "Login failed")
                raise HTTPException(status_code=response.status_code, detail=error_detail)

            return response.json()

        except httpx.ConnectError:
            raise HTTPException(
                status_code=503,
                detail="Authentication service unavailable"
            )

@router.get("/me")
async def get_me(current_user: Dict[Any, Any] = Depends(get_current_user)):
    """
    Получение данных текущего пользователя
    Требует валидный JWT токен в заголовке Authorization
    
    Dependency get_current_user автоматически:
    1. Проверяет токен
    2. Получает данные пользователя из users-service
    3. Передает их в этот эндпоинт как параметр current_user
    """
    return current_user

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
async def refresh_token(refresh_data: Dict[Any, Any]):
    """
    Обновление JWT токена (будет добавлено позже)
    Пока заглушка для будущей функциональности
    """
    return {"message": "Token refresh endpoint - to be implemented"}