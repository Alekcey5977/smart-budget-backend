import os
from fastapi import APIRouter, Depends, HTTPException, Request
import httpx
from app.dependencies import get_current_user
from typing import Dict

router = APIRouter(prefix="/sync", tags=["sync"])

TRANSACTIONS_SERVICE_URL = os.getenv("TRANSACTIONS_SERVICE_URL", "http://transactions-service:8002")


@router.post(
    "/trigger",
    summary="Синхронизировать один счет пользователя",
    description="Немедленно синхронизирует данные конкретного банковского счета с псевдо банком"
)
async def trigger_sync(
    bank_account_hash: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Синхронизировать конкретный счет пользователя.

    Этот endpoint вызывается:
    - При добавлении нового счета
    - По требованию пользователя (кнопка "Обновить счет")

    Args:
        bank_account_hash: Хеш банковского счета для синхронизации

    Returns:
        Статистику синхронизации (количество добавленных записей)
    """
    user_id = current_user["user_id"]

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(
                f"{TRANSACTIONS_SERVICE_URL}/transactions/trigger_sync",
                json={
                    "bank_account_hash": bank_account_hash,
                    "user_id": user_id
                }
            )

            if response.status_code == 404:
                raise HTTPException(
                    status_code=404,
                    detail="Счет не найден или доступ запрещен"
                )
            elif response.status_code == 502:
                raise HTTPException(
                    status_code=502,
                    detail="Псевдо банк недоступен"
                )

            response.raise_for_status()
            return response.json()

    except httpx.TimeoutException:
        raise HTTPException(
            status_code=504,
            detail="Таймаут синхронизации"
        )
    except httpx.HTTPStatusError as e:
        raise HTTPException(
            status_code=e.response.status_code,
            detail=f"Ошибка синхронизации: {e.response.text}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Внутренняя ошибка: {str(e)}"
        )


@router.post(
    "/all",
    summary="Синхронизировать все активные счета",
    description="Выполняет инкрементальную синхронизацию всех активных счетов пользователя с псевдо банком"
)
async def sync_all_accounts(
    current_user: dict = Depends(get_current_user)
):
    """
    Синхронизировать все активные счета.

    Этот endpoint:
    - Подтягивает новые транзакции для всех счетов
    - Синхронизирует только изменения с момента последней синхронизации
    - Может вызываться по требованию пользователя или автоматически

    Returns:
        Статистику синхронизации всех счетов
    """
    try:
        async with httpx.AsyncClient(timeout=60) as client:
            response = await client.post(
                f"{TRANSACTIONS_SERVICE_URL}/transactions/sync_all"
            )

            response.raise_for_status()
            return response.json()

    except httpx.TimeoutException:
        raise HTTPException(
            status_code=504,
            detail="Таймаут синхронизации всех счетов"
        )
    except httpx.HTTPStatusError as e:
        raise HTTPException(
            status_code=e.response.status_code,
            detail=f"Ошибка синхронизации: {e.response.text}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Внутренняя ошибка: {str(e)}"
        )