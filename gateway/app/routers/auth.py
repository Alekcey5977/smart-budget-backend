from fastapi import APIRouter, Depends, HTTPException, Form
import httpx
import os
from typing import Dict, Any
from fastapi.security import OAuth2PasswordBearer

from app.dependencies import get_current_user

router = APIRouter(
    prefix="/auth",
    tags=["authentication"]
)

# Подключаем схему безопасности для Swagger
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

USERS_SERVICE_URL = os.getenv("USERS_SERVICE_URL")

# ----------------------------
# Регистрация пользователя
# ----------------------------
@router.post("/register")
async def register(user_data: Dict[str, str]):
    """
    Регистрация нового пользователя.

    **Параметры запроса (JSON)**:
    - `email` (str) — электронная почта пользователя
    - `password` (str) — пароль пользователя

    Пример запроса:
    ```json
    {
        "email": "example@gmail.com",
        "password": "1234"
    }
    ```

    Возвращает:
    Словарь с данными пользователя, как от users-service.
    """
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                f"{USERS_SERVICE_URL}/users/register",
                json=user_data,
                timeout=30.0
            )
            if response.status_code >= 400:
                raise HTTPException(
                    status_code=response.status_code,
                    detail=response.json().get("detail", "Registration failed")
                )
            return response.json()
        except httpx.ConnectError:
            raise HTTPException(status_code=503, detail="Users service unavailable")

# ----------------------------
# Логин пользователя
# ----------------------------
@router.post("/login")
async def login(username: str = Form(...), password: str = Form(...)):
    """
    Аутентификация пользователя через form-data.

    **Поля для ввода**:
    - `username` — email
    - `password` — пароль

    Возвращает JWT токен с полями:
    - `access_token`
    - `token_type`
    """
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{USERS_SERVICE_URL}/users/login",
            json={"email": username, "password": password},
            timeout=15.0
        )
        if response.status_code >= 400:
            raise HTTPException(
                status_code=response.status_code,
                detail=response.json().get("detail", "Login failed")
            )
        return response.json()

# ----------------------------
# Получение текущего пользователя
# ----------------------------
@router.get("/me")
async def get_me(current_user: Dict[Any, Any] = Depends(get_current_user)):
    """
    Получение данных текущего пользователя.

    🔒 Требуется JWT токен.
    """
    return current_user

# ----------------------------
# Обновление профиля
# ----------------------------
@router.put("/me")
async def update_me(update_data: Dict[str, str], current: Dict[str, Any] = Depends(get_current_user)):
    """
    Обновление профиля текущего пользователя.

    Можно передавать одно или несколько значений.

    Примеры полей:
    - `first_name` (str)
    - `last_name` (str)

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
                params={"token": token},
                timeout=15.0
            )
            if response.status_code >= 400:
                raise HTTPException(
                    status_code=response.status_code,
                    detail=response.json().get("detail", "Update failed")
                )
            return response.json()
        except httpx.ConnectError:
            raise HTTPException(status_code=503, detail="Users service unavailable")
