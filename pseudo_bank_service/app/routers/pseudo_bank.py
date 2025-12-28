from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models import Bank_Account
from app.schemas import Validate_Bank_Account
from app.database import get_db

router = APIRouter(prefix="/pseudo_bank", tags=["pseudo_bank"])


@router.post("/validate_account")
async def validate_account(request: Validate_Bank_Account, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Bank_Account).where(Bank_Account.account_number == request.bank_account_hash)
                                                          )
    
    bank_account = result.scalar_one_or_none()

    if not bank_account:
        raise HTTPException(404, "Account not found")

    return {
        "balance": float(bank_account.balance),
        "currency": bank_account.currency,
    }
