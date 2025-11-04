import httpx
from fastapi import Depends, HTTPException, Header
import os
from typing import Optional, Dict, Any

# Получаем URL сервиса пользователей из переменных окружения
# Формат: http://users-service:8001
USERS_SERVICE_URL = os.getenv("USERS_SERVICE_URL")

async def get_current_user(authorization: Optional[str] = Header(None)) -> Dict[str, Any]:
    """
    Dependency для проверки JWT токена и получения данных пользователя.
    Возвращает словарь вида:
    {
        "token": "<JWT токен>",
        "user": {данные пользователя из users-service}
    }
    """

    # Проверяем наличие заголовка авторизации
    if authorization is None:
        raise HTTPException(
            status_code=401,
            detail="Authorization header is required"
        )
    
    # Проверяем формат заголовка: должен быть "Bearer {token}"
    if not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=401,
            detail="Invalid authorization header format. Expected: Bearer <token>"
        )
    
    # Извлекаем чистый токен (убираем "Bearer ")
    token = authorization.split(" ")[1]

    # Создаем асинхронный HTTP клиент для запроса к users-service
    async with httpx.AsyncClient() as client:
        try:
            # Делаем запрос к users-service для проверки токена
            response = await client.get(
                f"{USERS_SERVICE_URL}/users/me",  # Эндпоинт проверки токена
                params={"token": token},          # Передаем токен как параметр
                timeout=10.0                      # Таймаут 10 секунд
            )

            # Если users-service вернул 200 - токен валиден
            if response.status_code == 200:
                user_data = response.json()
                return {"token": token, "user": user_data}  # Возвращаем данные пользователя
            
            # Если users-service вернул ошибку - пробрасываем ее
            else:
                error_detail = response.json().get("detail", "Invalid token")
                raise HTTPException(
                    status_code=response.status_code,
                    detail=error_detail
                )
            
        # Обработка ошибок сети (users-service недоступен)
        except httpx.ConnectError:
            raise HTTPException(
                status_code=503,
                detail="Users service is currently unavailable"
            )
        except httpx.TimeoutException:
            raise HTTPException(
                status_code=504,
                detail="Users service request timeout"
            )
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Internal server error: {str(e)}"
            )
        
# Дополнительная dependency для опциональной аутентификации
# Для того чтобы можно было сделать эндпоинты доступными и для аутентифицированных и для неаутентифицированных пользователей, например @router.get("/")
async def get_optional_user(authorization: Optional[str] = Header(None)):
    """
    Опциональная проверка пользователя
    Возвращает данные пользователя если токен есть и валиден,
    возвращает None если токена нет или невалиден
    """
    if authorization is None:
        return None
        
    try:
        return await get_current_user(authorization)
    except HTTPException:
        return None