from fastapi import APIRouter, Depends, HTTPException, Request, Response
import httpx
import os
from typing import Dict, Any
from app.schemas import RegisterRequest, UserUpdateRequest, UserLogin
from app.dependencies import get_current_user

router = APIRouter(
    prefix="/auth",
    tags=["authentication"]
)

USERS_SERVICE_URL = os.getenv("USERS_SERVICE_URL")

# ----------------------------
# Регистрация пользователя
# ----------------------------
@router.post("/register")
async def register(user_data: RegisterRequest):
    """
    Регистрация нового пользователя в системе.

    🔓 Открытый эндпоинт, не требует аутентификации

    📝 **Поля запроса:**
    - `email` (обязательный, строка) - Электронная почта пользователя
      - Формат: валидный email
      - Уникальность: проверяется на сервере
      - Пример: "user@example.com"
    
    - `password` (обязательный, строка) - Пароль пользователя
      - Минимальная длина: 1 символ
      - Рекомендуемая длина: 8+ символов
      - Пример: "securepassword123"
    
    - `first_name` (обязательный, строка) - Имя пользователя
      - Минимальная длина: 2 символа
      - Максимальная длина: 50 символов
      - Не может быть пустым или содержать только пробелы
      - Пример: "Иван"
    
    - `last_name` (обязательный, строка) - Фамилия пользователя
      - Минимальная длина: 2 символа
      - Максимальная длина: 50 символов
      - Не может быть пустым или содержать только пробелы
      - Пример: "Иванов"
    
    - `patronymic` (обязательный, строка) - Отчество пользователя
      - Минимальная длина: 2 символа
      - Максимальная длина: 50 символов
      - Не может быть пустым или содержать только пробелы
      - Пример: "Иванович"

    ✅ **Пример успешного запроса:**
    ```json
    {
        "email": "user@example.com",
        "password": "securepassword123",
        "first_name": "Иван",
        "last_name": "Иванов",
        "patronymic": "Иванович"
    }
    ```

    ✅ **Пример успешного ответа:**
    ```json
    {
        "email": "user@example.com",
        "first_name": "Иван",
        "last_name": "Иванов",
        "patronymic": "Иванович",
        "is_active": true,
        "created_at": "2024-01-15T10:30:00.000Z",
        "updated_at": null
    }
    ```

    ❌ **Возможные ошибки:**
    - `400 Bad Request` - Email уже зарегистрирован в системе
    - `422 Validation Error` - Ошибки валидации входных данных
    - `503 Service Unavailable` - Сервис пользователей временно недоступен
    """

    async with httpx.AsyncClient() as client:
        try:
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
async def login(
    response: Response,
    user_data: UserLogin
):
    """
    Аутентификация пользователя в системе.

    🔓 Открытый эндпоинт, не требует аутентификации

    📝 **Поля запроса:**
    - `email` (обязательный, строка) - Электронная почта пользователя
      - Формат: валидный email
      - Должен существовать в системе
      - Пример: "user@example.com"
    
    - `password` (обязательный, строка) - Пароль пользователя
      - Должен соответствовать хешу в базе данных
      - Пример: "securepassword123"

    ✅ **Пример успешного запроса:**
    ```json
    {
        "email": "user@example.com",
        "password": "securepassword123"
    }
    ```

    ✅ **Пример успешного ответа:**
    ```json
    {
        "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
        "token_type": "bearer"
    }
    ```

    🍪 **Устанавливает cookies:**
    - `refresh_token` - JWT refresh token для обновления access token
      - Тип: HTTP-only cookie (недоступен из JavaScript)
      - Secure: false (в разработке), true в продакшене
      - SameSite: strict
      - Срок жизни: 7 дней

    ❌ **Возможные ошибки:**
    - `401 Unauthorized` - Неверный email или пароль
    - `400 Bad Request` - Пользователь неактивен
    - `503 Service Unavailable` - Сервис пользователей временно недоступен
    """

    async with httpx.AsyncClient() as client:
        try:
            request_data = user_data.model_dump()

            response_internal = await client.post(
                f"{USERS_SERVICE_URL}/users/login",
                json=request_data,
                timeout=15.0
            )
            
            if response_internal.status_code >= 400:
                raise HTTPException(
                    status_code=response_internal.status_code,
                    detail=response_internal.json().get("detail", "Login failed")
                )
            
            result = response_internal.json()
            
            if 'set-cookie' in response_internal.headers:
                refresh_cookie = response_internal.headers['set-cookie']
                response.headers['set-cookie'] = refresh_cookie

            return result
            
        except httpx.ConnectError:
            raise HTTPException(status_code=503, detail="Users service unavailable")

# ----------------------------
# Обновление токена
# ----------------------------
@router.post("/refresh")
async def refresh_token(
    response: Response,
    request: Request
):
    """
    Обновление access token с помощью refresh token.

    🔓 Открытый эндпоинт, требует только refresh token в cookie

    📋 **Требования:**
    - Действительный `refresh_token` в HTTP-only cookie
    - Refresh token не должен быть просрочен

    ✅ **Пример успешного ответа:**
    ```json
    {
        "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
        "token_type": "bearer"
    }
    ```

    🍪 **Обновляет cookies:**
    - `refresh_token` - Новый JWT refresh token
      - Тип: HTTP-only cookie
      - Secure: false (в разработке), true в продакшене
      - SameSite: strict
      - Срок жизни: 7 дней

    ❌ **Возможные ошибки:**
    - `401 Unauthorized` - Refresh token отсутствует в cookie
    - `401 Unauthorized` - Refresh token невалиден или просрочен
    - `401 Unauthorized` - Неверный тип токена
    - `401 Unauthorized` - Пользователь неактивен или не найден
    - `503 Service Unavailable` - Сервис пользователей временно недоступен
    """

    async with httpx.AsyncClient() as client:
        try:
            cookies = {"refresh_token": request.cookies.get("refresh_token", "")}
            
            response_internal = await client.post(
                f"{USERS_SERVICE_URL}/users/refresh",
                cookies=cookies,
                timeout=15.0
            )
            
            if response_internal.status_code >= 400:
                raise HTTPException(
                    status_code=response_internal.status_code,
                    detail=response_internal.json().get("detail", "Token refresh failed")
                )
            
            result = response_internal.json()
            
            if 'set-cookie' in response_internal.headers:
                refresh_cookie = response_internal.headers['set-cookie']
                response.headers['set-cookie'] = refresh_cookie

            return result
            
        except httpx.ConnectError:
            raise HTTPException(status_code=503, detail="Users service unavailable")

# ----------------------------
# Выход из системы
# ----------------------------
@router.post("/logout")
async def logout(response: Response):
    """
    Выход пользователя из системы.

    🔓 Открытый эндпоинт, не требует аутентификации

    🗑️ **Действия:**
    - Удаляет refresh_token из cookies пользователя
    - Инвалидирует текущую сессию на стороне сервера

    ✅ **Пример успешного ответа:**
    ```json
    {
        "msg": "Logged out"
    }
    ```

    🍪 **Удаляет cookies:**
    - `refresh_token` - HTTP-only cookie полностью удаляется

    ❌ **Возможные ошибки:**
    - `503 Service Unavailable` - Сервис пользователей временно недоступен

    💡 **Примечание:** Cookie удаляется даже при недоступности сервиса пользователей
    """

    async with httpx.AsyncClient() as client:
        try:
            response_internal = await client.post(
                f"{USERS_SERVICE_URL}/users/logout",
                timeout=10.0
            )
            
            response.delete_cookie(
                key="refresh_token",
                secure=False,
                samesite="strict"
            )
            
            if response_internal.status_code >= 400:
                raise HTTPException(
                    status_code=response_internal.status_code,
                    detail=response_internal.json().get("detail", "Logout failed")
                )
            
            return {"msg": "Logged out"}
            
        except httpx.ConnectError:
            response.delete_cookie(
                key="refresh_token",
                secure=False,
                samesite="strict"
            )
            raise HTTPException(status_code=503, detail="Users service unavailable")

# ----------------------------
# Получение текущего пользователя
# ----------------------------
@router.get("/me")
async def get_me(current_user: Dict[Any, Any] = Depends(get_current_user)):
    """
    Получение данных текущего аутентифицированного пользователя.

    🔒 Защищенный эндпоинт, требует JWT токен

    📋 **Требования аутентификации:**
    - Действительный JWT access token

    🔑 **Способы передачи токена:**

    ## 🖥️ Для Swagger UI:
    - **Поле для ввода:** `token` (query parameter)
    - **Расположение:** Поле ввода появится под описанием метода
    - **Формат:** Просто вставьте ваш JWT токен без префикса "Bearer"
    - **Пример значения:** `eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...`

    ## 📮 Для Postman/REST клиентов:
    - **Заголовок:** `Authorization`
    - **Формат:** `Bearer <ваш_токен>`
    - **Пример:** `Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...`

    ## 🌐 Прямые HTTP запросы:
    ```http
    # Вариант 1: Через query parameter (как в Swagger)
    GET /auth/me?token=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...

    # Вариант 2: Через header (как в Postman)
    GET /auth/me
    Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
    ```

    ✅ **Пример успешного ответа:**
    ```json
    {
        "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
        "user": {
            "email": "user@example.com",
            "first_name": "Иван",
            "last_name": "Иванов",
            "patronymic": "Иванович",
            "is_active": true,
            "created_at": "2024-01-15T10:30:00.000Z",
            "updated_at": null
        }
    }
    ```

    ❌ **Возможные ошибки:**
    - `401 Unauthorized` - Токен отсутствует или невалиден
    - `401 Unauthorized` - Неверный формат заголовка Authorization
    - `404 Not Found` - Пользователь не найден
    - `503 Service Unavailable` - Сервис пользователей временно недоступен

    """

    return current_user

# ----------------------------
# Обновление профиля
# ----------------------------
@router.put("/me")
async def update_me(
    update_data: UserUpdateRequest, 
    current_user: Dict[str, Any] = Depends(get_current_user),
    request: Request = None
):
    """
    Обновление данных профиля текущего пользователя.

    🔒 Защищенный эндпоинт, требует JWT токен

    📋 **Требования аутентификации:**
    - Действительный JWT access token
    - Действительный refresh token в cookie (для верификации)

    🔑 **Способы передачи токена:**

    ## 🖥️ Для Swagger UI:
    - **Поле для ввода:** `token` (query parameter) 
    - **Расположение:** Поле ввода появится под описанием метода
    - **Формат:** Просто вставьте ваш JWT токен без префикса "Bearer"
    - **Пример значения:** `eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...`

    ## 📮 Для Postman/REST клиентов:
    - **Заголовок:** `Authorization`
    - **Формат:** `Bearer <ваш_токен>`
    - **Пример:** `Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...`

    📝 **Поля запроса (все опциональны, но хотя бы одно должно быть передано):**
    - `first_name` (строка) - Новое имя пользователя (2-50 символов)
    - `last_name` (строка) - Новая фамилия пользователя (2-50 символов)  
    - `patronymic` (строка) - Новое отчество пользователя (2-50 символов)

    ✅ **Пример успешного запроса:**
    ```json
    {
        "first_name": "Петр",
        "last_name": "Петров",
        "patronymic": "Петрович"
    }
    ```

    ✅ **Пример успешного ответа:**
    ```json
    {
        "email": "user@example.com",
        "first_name": "Петр",
        "last_name": "Петров",
        "patronymic": "Петрович",
        "is_active": true,
        "created_at": "2024-01-15T10:30:00.000Z",
        "updated_at": "2024-01-20T15:45:00.000Z"
    }
    ```

    ❌ **Возможные ошибки:**
    - `401 Unauthorized` - Токен отсутствует или невалиден
    - `404 Not Found` - Пользователь не найден
    - `422 Validation Error` - Ошибки валидации входных данных
    - `503 Service Unavailable` - Сервис пользователей временно недоступен

    """

    async with httpx.AsyncClient() as client:
        try:
            request_data = update_data.model_dump(exclude_unset=True)
            
            refresh_token = request.cookies.get("refresh_token") if request else None
            
            headers = {
                "Authorization": f"Bearer {current_user['token']}",
                "Content-Type": "application/json"
            }
            cookies = {"refresh_token": refresh_token} if refresh_token else {}
            
            response = await client.put(
                f"{USERS_SERVICE_URL}/users/me",
                json=request_data,
                headers=headers,
                cookies=cookies,
                timeout=15.0
            )
            
            if response.status_code >= 400:
                error_detail = response.json().get("detail", "Update failed")
                raise HTTPException(
                    status_code=response.status_code,
                    detail=error_detail
                )
            return response.json()
        
        except httpx.ConnectError:
            raise HTTPException(status_code=503, detail="Users service unavailable")