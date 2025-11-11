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
    Получение данных текущего пользователя.

    🔒 Требуется JWT токен в заголовке Authorization: Bearer <token>
    """
    return current_user

# ----------------------------
# Обновление профиля - ИСПРАВЛЕННАЯ ВЕРСИЯ
# ----------------------------
@router.put("/me")
async def update_me(
    update_data: UserUpdateRequest, 
    current_user: Dict[str, Any] = Depends(get_current_user),
    request: Request = None
):
    """
    Обновление профиля текущего пользователя.

    🔒 Требуется JWT токен в заголовке Authorization: Bearer <token>
    """
    async with httpx.AsyncClient() as client:
        try:
            request_data = update_data.model_dump(exclude_unset=True)
            
            # Получаем refresh_token из cookies запроса
            refresh_token = request.cookies.get("refresh_token") if request else None
            
            # Подготавливаем заголовки и cookies для запроса к User Service
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