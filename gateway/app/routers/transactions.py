from fastapi import APIRouter, Depends, HTTPException, Header
import os
from typing import Dict, Any, List
from app.dependencies import get_current_user
import httpx


router = APIRouter(
    prefix="/transactions",
    tags=["transactions"]
)

TRANSACTION_SERVICE_URL = os.getenv("TRANSACTION_SERVICE_URL")

# ----------------------------
# Вывод всех транзакций
# ----------------------------
@router.get("/")
async def get_all_transactions(
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Получить все транзакции пользователя
    
    🔒 Защищенный эндпоинт, требует JWT токен
    
    ✅ **Пример успешного ответа:**
    ```json
    {
        "transactions": [
            {
                "id": 1,
                "amount": 100.50,
                "type": "income",
                "category": "Salary",
                "description": "Monthly salary",
                "date": "2024-01-15T10:30:00.000Z"
            }
        ]
    }
    """

    user_id = current_user["user_id"] # Берем из токена!

    async with httpx.AsyncClient as client:
        try:
            headers = {"X-User-ID": str(user_id)}

            response = await client.get(
                f"{TRANSACTION_SERVICE_URL}/transactions",
                headers=headers,
                timeout=10.0
            )

            if response.status_code == 200:
                return response.json()
            
            else:
                error_detail = response.json().get("detail", "Failed to get transactions")
                raise HTTPException(
                    status_code=response.status_code,
                    detail=error_detail
                )
            
        except httpx.ConnectError:
            raise HTTPException(503, "Transaction service is unavailable")
            
# ----------------------------
# Получение только доходов
# ----------------------------
@router.get("/income")
async def get_income_transactions(
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Получить только доходные транзакции пользователя
    """

    user_id = current_user["user_id"] # Берем из токена!

    async with httpx.AsyncClient as client:
        try:
            headers = {"X-User-ID": str(user_id)}

            response = await client.get(
                f"{TRANSACTION_SERVICE_URL}/transactions/income",
                headers=headers,
                timeout=10.0
            )

            if response.status_code == 200:
                return response.json()
            
            else:
                error_detail = response.json().get("detail", "Failed to get income transactions")
                raise HTTPException(
                    status_code=response.status_code,
                    detail=error_detail
                )
            
        except httpx.ConnectError:
            raise HTTPException(503, "Transaction service is unavailable")