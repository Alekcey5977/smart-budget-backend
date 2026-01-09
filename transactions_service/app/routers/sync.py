from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from app.database import get_db
from app.repository.sync_repository import SyncRepository
from app.schemas import SyncTriggerRequest
from app.routers.transactions import router
from app.models import Bank_Account


@router.post("/trigger_sync")
async def trigger_sync(
    request: SyncTriggerRequest,
    db: AsyncSession = Depends(get_db)
):
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



