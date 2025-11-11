import httpx
from fastapi import Depends, HTTPException, Header, Request
import os
from typing import Dict, Any

USERS_SERVICE_URL = os.getenv("USERS_SERVICE_URL")

async def get_current_user(
    request: Request,
    authorization: str = Header(..., description="Bearer token")
) -> Dict[str, Any]:
    """
    Dependency для проверки JWT токена и получения данных пользователя.
    """

    if not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=401,
            detail="Invalid authorization header format. Expected: Bearer <token>"
        )
    
    token = authorization.split(" ")[1]
    refresh_token = request.cookies.get("refresh_token")

    async with httpx.AsyncClient() as client:
        try:
            headers = {"Authorization": f"Bearer {token}"}
            cookies = {"refresh_token": refresh_token} if refresh_token else {}
            
            response = await client.get(
                f"{USERS_SERVICE_URL}/users/me",
                headers=headers,
                cookies=cookies,
                timeout=10.0
            )

            if response.status_code == 200:
                user_data = response.json()
                return {"token": token, "user": user_data}
            else:
                error_detail = response.json().get("detail", "Invalid token")
                raise HTTPException(
                    status_code=response.status_code,
                    detail=error_detail
                )
            
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