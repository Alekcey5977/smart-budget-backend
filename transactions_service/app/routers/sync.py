from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from app.database import get_db
from app.repository.sync_repository import SyncRepository
from app.schemas import SyncTriggerRequest
from app.routers.transactions import router
from app.models import Bank_Account


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

    account = await repo.get_or_create_account_stub(
        request.bank_account_hash,
        request.user_id
    )

    if not await repo.validate_account_access(account, request.user_id):
        raise HTTPException(
            status_code=404,
            detail="Account not found or access denied"
        )


    try:
        stats = await repo.sync_by_account(request.bank_account_hash)
        return {"status": "success", "synced": stats}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=502, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Sync failed: {str(e)}")


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



