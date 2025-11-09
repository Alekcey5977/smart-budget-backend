from fastapi import APIRouter, Depends, HTTPException, Form
import httpx
import os
from typing import Dict, Any
from fastapi.security import OAuth2PasswordBearer
from app.schemas import RegisterRequest, UserUpdateRequest


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
async def register(user_data: RegisterRequest):
    """
    Регистрация нового пользователя.

    **Параметры запроса (JSON)**:
    
    Поля для ввода:
    - `email` (str) — электронная почта пользователя
    - `password` (str) — пароль пользователя
    - `first_name` (str) - имя пользователя
    - `last_name` (str) - фамилия пользователя
    - `patronymic` (str) - отчество пользователя

    Валидация:
    - `email` - корректность email вида
    - `first_name` - не менее 2 и не более 50 символов
    - `last_name` - не менее 2 и не более 50 символов
    - `patronymic` - не менее 2 и не более 50 символов

    Пример запроса:
    ```json
    {
        "email": "user@example.com",
        "password": "1234",
        "first_name": "Иван",
        "last_name": "Иванов"
        "patronymic": "Иванович"
    }
    ```



    Возвращает:
    Словарь с данными пользователя.
    """
    async with httpx.AsyncClient() as client:
        try:
            # Конвертируем Pydantic модель в dict
            request_data = user_data.model_dump()

            response = await client.post(
                f"{USERS_SERVICE_URL}/users/register",
                json=request_data,
                timeout=30.0
            )

            if response.status_code >= 400:
                error_detail = response.json().get("detail", "Registration failed")
                raise HTTPException(
                    status_code=response.status_code,
                    detail=error_detail
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
async def update_me(update_data: UserUpdateRequest, current: Dict[str, Any] = Depends(get_current_user)):
    """
    Обновление профиля текущего пользователя.

    Примеры полей:
    - `first_name` (str) - имя пользователя
    - `last_name` (str) - фамилия пользователя
    - `patronymic` (str) - отчество пользователя


    Пример запроса:
    ```json
    {
        "first_name": "Иван",
        "last_name": "Иванов"
        "patronymic": "Иванович"
    }
    ```

    Валидация:
    - `first_name` - не менее 2 и не более 50 символов
    - `last_name` - не менее 2 и не более 50 символов
    - `patronymic` - не менее 2 и не более 50 символов

    Возвращает:
    Словарь с обновленными данными пользователя.
    """
    token = current["token"]
    async with httpx.AsyncClient() as client:
        try:
            # Конвертируем Pydantic модель в dict
            request_data = update_data.model_dump(exclude_unset=True)

            response = await client.put(
                f"{USERS_SERVICE_URL}/users/me",
                json=request_data,
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
