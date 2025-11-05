from fastapi import APIRouter, Depends, HTTPException, Header, Form
import httpx
import os
from typing import Dict
from fastapi.security import OAuth2PasswordBearer

from app.schemas import UserCreate, UserUpdate, UserLogin, Token, UserResponse
from app.dependencies import get_current_user # Импортируем dependency
from app.dependencies import get_current_user


router = APIRouter(
    prefix="/auth",
    tags=["authentication"]
)

# Подключаем схему безопасности — теперь Swagger покажет кнопку Authorize

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

USERS_SERVICE_URL = os.getenv("USERS_SERVICE_URL")

# ----------------------------
# Регистрация пользователя
# ----------------------------
@router.post("/register", response_model=UserResponse)
async def register(user_data: UserCreate):
    """
<<<<<<< HEAD
    Регистрация нового пользователя.
    
    **Поля для ввода (JSON):**
    - email: EmailStr
    - password: str
    
    Проксирует запрос в users-service и возвращает результат.

    Регистрация нового пользователя.\n
    Принимает данные пользователя и проксирует запрос в users-service.

    Параметры запроса (JSON):
    Можно передавать одно или несколько значений.
    Примеры полей:
    - `email` (str) — электронная почта пользователя
    - `password` (str) — пароль пользователя

     Пример запроса:
    ```json
    {
        "email": "example@gmail.com",
        "password": "1234"
    }
    ```
    Возвращает:\n
    Словарь с данными пользователя.
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

    Логин пользователя.\n
    Принимает email и пароль, возвращает JWT токен для дальнейшей аутентификации.\n

    Процесс работы:
    1. Получает учетные данные (email и пароль) от клиента.
    2. Отправляет их в users-service для проверки подлинности.
    3. Если аутентификация успешна, возвращает JWT токен.
    4. В случае ошибки возвращает соответствующий HTTP статус и сообщение.
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

@router.get("/me")
async def get_me(current_user: Dict[Any, Any] = Depends(get_current_user)):
    """
    Получение информации о текущем пользователе.\n

    🔒 Требует аутентификацию через встроенный механизм авторизации.\n
    Пользователь должен быть авторизован и иметь действительный JWT токен.\n

    Возвращает:\n
        Словарь с информацией о пользователе.
    """
    return current_user

@router.put("/me")
async def update_me(update_data: Dict[str, str], current: Dict[str, Any] = Depends(get_current_user)):
    """
    Обновление профиля текущего пользователя.\n

    🔒 Требует авторизацию через встроенный механизм (JWT токен).\n
    Пользователь должен быть авторизован, токен проверяется автоматически.\n

    Параметры запроса (JSON):
    Можно передавать одно или несколько значений.
    Примеры полей:
    - `first_name` (str) — имя пользователя
    - `last_name` (str) — фамилия пользователя

    Пример запроса с несколькими полями:
    ```json
    {
        "first_name": "Иван",
        "last_name": "Иванов"
    }
    ```

    Пример запроса с одним полем:
    ```json
    {
        "first_name": "Борис"
    }
    ```

    Возвращает:
        Словарь с обновленными данными пользователя.
    """
    token = current["token"]
    async with httpx.AsyncClient() as client:
        try:
            response = await client.put(
                f"{USERS_SERVICE_URL}/users/me",
                json=update_data,
                params={"token": token},  # передаем токен корректно
                timeout=15.0
            )

            if response.status_code >= 400:
                detail = response.json().get("detail", "Update failed")
                raise HTTPException(status_code=response.status_code, detail=detail)

            return response.json()

        except httpx.ConnectError:
            raise HTTPException(status_code=503, detail="Users service unavailable")
