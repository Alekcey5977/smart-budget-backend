import logging
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from app.database import get_db
from app.repository.sync_repository import SyncRepository
from app.schemas import SyncTriggerRequest
from app.routers.transactions import router
from app.models import Bank_Account

logger = logging.getLogger(__name__)


class SyncUserAccountsRequest(BaseModel):
    user_id: int


@router.post("/trigger_sync", summary="Синхронизировать один счет")
async def trigger_sync(
    request: SyncTriggerRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Синхронизировать один конкретный счет с псевдо банком.

    Этот endpoint используется для немедленной синхронизации данных
    по конкретному счету. Вызывается при добавлении нового счета
    или по требованию пользователя.
    """
    repo = SyncRepository(db)

    try:
        stats = await repo.sync_by_account(request.bank_account_hash, request.user_id)
        return {"status": "success", "synced": stats}
    except ValueError as e:
        logger.error(f"Account not found: {e}")
        raise HTTPException(status_code=404, detail=str(e))
    except RuntimeError as e:
        logger.error(f"Runtime error during sync: {e}")
        raise HTTPException(status_code=502, detail=str(e))
    except Exception as e:
        logger.exception(f"Unexpected error during sync: {e}")
        raise HTTPException(status_code=500, detail=f"Sync failed: {str(e)}")


@router.post("/sync_user_accounts", summary="Синхронизировать все счета пользователя")
async def sync_user_accounts(
    request: SyncUserAccountsRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Синхронизировать все счета конкретного пользователя с псевдо банком.

    Этот endpoint используется Gateway для синхронизации всех счетов
    одного пользователя. Подтягивает данные со всех его активных счетов.

    Вызывается:
    - При ручной синхронизации (кнопка "Обновить данные")
    - После добавления нового счета (background task)
    """
    repo = SyncRepository(db)

    try:
        result = await repo.sync_user_accounts(request.user_id)
        return {
            "status": "success",
            "message": f"Synced {result['success']} accounts for user {request.user_id}",
            **result
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Sync user accounts failed: {str(e)}"
        )


@router.post("/sync_all", summary="Синхронизировать все активные счета")
async def sync_all_accounts(
    db: AsyncSession = Depends(get_db)
):
    """
    Синхронизировать все активные счета с псевдо банком.

    Этот endpoint выполняет инкрементальную синхронизацию для всех
    активных счетов в системе. Подтягивает только новые транзакции
    с момента последней синхронизации.

    Используется:
    - По требованию пользователя (кнопка "Обновить все счета")
    - Автоматически по расписанию (каждые 10 минут)
    """
    repo = SyncRepository(db)

    try:
        result = await repo.sync_incremental()
        return {
            "status": "success",
            "message": "All accounts synchronized",
            **result
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Sync all failed: {str(e)}"
        )



