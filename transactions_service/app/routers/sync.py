from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from app.database import get_db
from app.repository.sync_repository import SyncRepository
from app.schemas import SyncTriggerRequest
from app.routers.transactions import router
from transactions_service.app.models import Bank_Account



@router.post("/trigger_sync")
async def trigger_sync(
    request: SyncTriggerRequest,
    db: AsyncSession = Depends(get_db)):

    account = await db.execute(
        select(Bank_Account.id)
        .where(
            Bank_Account.bank_account_hash == request.bank_account_hash,
            Bank_Account.user_id == request.user_id,
            Bank_Account.is_deleted.is_(False)
        )
    )
    if not account.scalar():
        raise HTTPException(404, "Account not found or access denied")

    repo = SyncRepository(db)
    stats = await repo.sync_by_account(request.bank_account_hash)
    try:
        stats = await repo.sync_by_account(request.bank_account_hash)
        return {"status": "success", "synced": stats}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=502, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Sync failed: {str(e)}")



