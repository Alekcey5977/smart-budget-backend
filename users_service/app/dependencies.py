import os
from typing import Any, Dict, Optional

import httpx
from fastapi import Header, HTTPException, Request
from jose import JWTError, jwt

USERS_SERVICE_URL = os.getenv("USERS_SERVICE_URL")
ACCESS_SECRET_KEY = os.getenv("ACCESS_SECRET_KEY")


# TODO: урать query запрос, когда будет продакшн
async def get_current_user(
    request: Request,
    authorization: Optional[str] = Header(None),
    token: Optional[str] = None,  # Делаем параметр опциональным
) -> Dict[str, Any]:
    """
    Dependency для проверки JWT токена
    """

    # Приоритет: Header > Query параметр
    if authorization and authorization.startswith("Bearer "):
        token_value = authorization.split(" ")[1]
        print("🔑 Using token from Authorization header")
    elif token:
        token_value = token
        print("🔑 Using token from query parameter")
    else:
        raise HTTPException(
            status_code=401,
            detail="Authorization required. Use Header 'Authorization: Bearer <token>' or query parameter 'token'",
        )

    refresh_token = request.cookies.get("refresh_token")

    # Быстрое извлечение user_id из токена
    try:
        payload = jwt.decode(token_value, ACCESS_SECRET_KEY, algorithms=["HS256"], options={"verify_signature": True})
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(401, "Invalid token: missing user ID")
    except JWTError as e:
        raise HTTPException(401, f"Invalid token: {str(e)}")

    async with httpx.AsyncClient() as client:
        try:
            headers = {"Authorization": f"Bearer {token_value}"}
            cookies = {"refresh_token": refresh_token} if refresh_token else {}

            response = await client.get(f"{USERS_SERVICE_URL}/users/me", headers=headers, cookies=cookies, timeout=10.0)

            if response.status_code == 200:
                user_data = response.json()
                return {"token": token_value, "user": user_data, "user_id": user_id}
            else:
                error_detail = response.json().get("detail", "Invalid token")
                raise HTTPException(status_code=response.status_code, detail=error_detail)

        except httpx.ConnectError:
            raise HTTPException(status_code=503, detail="Users service is currently unavailable")
        except httpx.TimeoutException:
            raise HTTPException(status_code=504, detail="Users service request timeout")

        # FIXME: Проверить нужен ли эта обработка исключения
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


def verify_websocket_token(token: str) -> int | None:
    """
    Проверка JWT токена для WebSocket соединений.

    Возвращает user_id если токен валиден, иначе None.
    """
    try:
        payload = jwt.decode(token, ACCESS_SECRET_KEY, algorithms=["HS256"])

        if payload.get("type") != "access":
            return None

        user_id_str = payload.get("sub")
        if user_id_str is None:
            return None

        return int(user_id_str)

    except (JWTError, ValueError, TypeError):
        return None
