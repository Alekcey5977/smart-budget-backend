import httpx
from fastapi import Depends, HTTPException, Header, Request, Query
from fastapi.params import Depends as FastAPIDepends
import os
from typing import Dict, Any, Optional

USERS_SERVICE_URL = os.getenv("USERS_SERVICE_URL")

async def get_current_user(
    request: Request,
    token: str = Query(..., description="JWT token for authentication"),
    authorization: Optional[str] = Header(None, include_in_schema=False)  # Скрываем из Swagger
) -> Dict[str, Any]:
    """
    Dependency для проверки JWT токена
    """
    # Приоритет: Header > Query параметр (для обратной совместимости)
    if authorization and authorization.startswith("Bearer "):
        token_value = authorization.split(" ")[1]
    else:
        token_value = token
    
    refresh_token = request.cookies.get("refresh_token")

    async with httpx.AsyncClient() as client:
        try:
            headers = {"Authorization": f"Bearer {token_value}"}
            cookies = {"refresh_token": refresh_token} if refresh_token else {}
            
            response = await client.get(
                f"{USERS_SERVICE_URL}/users/me",
                headers=headers,
                cookies=cookies,
                timeout=10.0
            )

            if response.status_code == 200:
                user_data = response.json()
                return {"token": token_value, "user": user_data}
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