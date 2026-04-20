import os
from typing import Any, Dict, Optional

import httpx
from fastapi import Header, HTTPException, Request
from jose import JWTError, jwt

from shared.cache import cache_client

USERS_SERVICE_URL = os.getenv("USERS_SERVICE_URL")
ACCESS_SECRET_KEY = os.getenv("ACCESS_SECRET_KEY")
_USER_PROFILE_TTL = 300  # секунд

# Shared client — reuses connections across requests
_http_client: Optional[httpx.AsyncClient] = None


def get_http_client() -> httpx.AsyncClient:
    global _http_client
    if _http_client is None or _http_client.is_closed:
        _http_client = httpx.AsyncClient(
            limits=httpx.Limits(max_connections=None, max_keepalive_connections=200),
            timeout=httpx.Timeout(10.0),
        )
    return _http_client


def _extract_token(authorization: Optional[str], token: Optional[str]) -> str:
    if authorization and authorization.startswith("Bearer "):
        return authorization.split(" ")[1]
    if token:
        return token
    raise HTTPException(
        status_code=401,
        detail="Authorization required. Use Header 'Authorization: Bearer <token>' or query parameter 'token'",
    )


def _decode_token(token_value: str) -> str:
    try:
        payload = jwt.decode(token_value, ACCESS_SECRET_KEY, algorithms=["HS256"], options={"verify_signature": True})
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(401, "Invalid token: missing user ID")
        return user_id
    except JWTError as e:
        raise HTTPException(401, f"Invalid token: {str(e)}")


# TODO: убрать query запрос, когда будет продакшн
async def get_current_user(
    request: Request,
    authorization: Optional[str] = Header(None),
    token: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Лёгкая аутентификация — только локальная проверка JWT, без HTTP-вызова к users-service.
    Используется для большинства эндпоинтов, которым нужен только user_id.
    """
    token_value = _extract_token(authorization, token)
    user_id = _decode_token(token_value)
    return {"token": token_value, "user": None, "user_id": user_id}


async def get_current_user_with_profile(
    request: Request,
    authorization: Optional[str] = Header(None),
    token: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Полная аутентификация — JWT + HTTP-вызов к users-service для получения профиля.
    Используется только там, где нужны данные пользователя (GET /auth/me, PUT /auth/me).
    """
    token_value = _extract_token(authorization, token)
    user_id = _decode_token(token_value)

    cache_key = f"user:profile:{user_id}"
    try:
        cached = await cache_client.get(cache_key)
        if cached:
            return {"token": token_value, "user": cached, "user_id": user_id}
    except Exception:
        pass

    refresh_token = request.cookies.get("refresh_token")
    client = get_http_client()

    try:
        headers = {"Authorization": f"Bearer {token_value}"}
        cookies = {"refresh_token": refresh_token} if refresh_token else {}

        response = await client.get(f"{USERS_SERVICE_URL}/users/me", headers=headers, cookies=cookies)

        if response.status_code == 200:
            user_data = response.json()
            try:
                await cache_client.set(cache_key, user_data, ttl=_USER_PROFILE_TTL)
            except Exception:
                pass
            return {"token": token_value, "user": user_data, "user_id": user_id}

        error_detail = response.json().get("detail", "Invalid token")
        raise HTTPException(status_code=response.status_code, detail=error_detail)

    except httpx.ConnectError:
        raise HTTPException(status_code=503, detail="Users service is currently unavailable")
    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="Users service request timeout")


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
