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
    db: AsyncSession = Depends(get_db),
    transaction_repo: TransactionRepository = Depends(
        get_transactions_repository)
):
    """Экспорт данных о счёте"""
    
    account = await transaction_repo.get_account_bank(account_hash)
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")

    bank = await db.execute(
        select(Bank).where(Bank.id == account.bank_id)
    )
    bank = bank.scalar_one()

    transactions = await db.execute(
        select(Transaction)
        .where(Transaction.bank_account_id == account.id)
        .options(
            selectinload(Transaction.merchant),
            selectinload(Transaction.category)
        )
    )
    transactions = transactions.scalars().all()

    merchant_ids = {t.merchant_id for t in transactions if t.merchant_id}
    category_ids = {t.category_id for t in transactions} | {
        m.category_id for t in transactions if t.merchant for m in [t.merchant]}

    merchants = []
    if merchant_ids:
        merchants = await db.execute(
            select(Merchant)
            .where(Merchant.id.in_(merchant_ids))
            .options(selectinload(Merchant.category))
        )
        merchants = merchants.scalars().all()

    categories = []
    if category_ids:
        categories = await db.execute(
            select(Category).where(Category.id.in_(category_ids))
        )
        categories = categories.scalars().all()

    mccs = []
    if category_ids:
        mccs = await db.execute(
            select(MCC_Category).where(
                MCC_Category.category_id.in_(category_ids))
        )
        mccs = mccs.scalars().all()

    def to_dict(obj):
        if hasattr(obj, '__table__'):
            return {c.name: getattr(obj, c.name) for c in obj.__table__.columns}
        return obj

    return {
        "bank_account": to_dict(account),
        "bank": to_dict(bank),
        "transactions": [to_dict(t) for t in transactions],
        "merchants": [to_dict(m) for m in merchants],
        "categories": [to_dict(c) for c in categories],
        "mcc_categories": [to_dict(m) for m in mccs],
    }
