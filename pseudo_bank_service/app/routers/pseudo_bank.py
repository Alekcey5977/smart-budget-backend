from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models import Transaction, Bank, Merchant, Category, MCC_Category
from app.schemas import Validate_Bank_Account
from app.database import get_db
from app.repository.transactions_repository import TransactionRepository


router = APIRouter(prefix="/pseudo_bank", tags=["pseudo_bank"])

# Получение репозитория транзакций
async def get_transactions_repository(db: AsyncSession = Depends(get_db)):
    """Dependency для получения репозитория"""
    return TransactionRepository(db)


@router.post("/validate_account/{account_hash}")
async def validate_account(
    request: Validate_Bank_Account, 
    db: AsyncSession = Depends(get_db),
    transaction_repo: TransactionRepository = Depends(get_transactions_repository)):
    """Получение данных о счёте"""
    
    result = await transaction_repo.get_account_bank(request.bank_account_hash)

    if not result:
        raise HTTPException(status_code=404, detail="Account not found")

    return {
        "balance": str(result.balance),
        "currency": result.currency,
    }


@router.get("/account/{account_hash}/export")
async def export_account_data(
    account_hash: str,
    since: Optional[datetime] = None,
    transaction_repo: TransactionRepository = Depends(
        get_transactions_repository)
):
    """Экспорт данных о счёте"""
    data = await transaction_repo.export_account_data(account_hash)
    if not data:
        raise HTTPException(status_code=404, detail="Account not found")

    to_dict = transaction_repo.to_dict

    return {
        "bank_account": to_dict(data["account"]),
        "bank": to_dict(data["bank"]),
        "transactions": [to_dict(t) for t in data["transactions"]],
        "merchants": [to_dict(m) for m in data["merchants"]],
        "categories": [to_dict(c) for c in data["categories"]],
        "mcc_categories": [to_dict(m) for m in data["mccs"]],
    }
