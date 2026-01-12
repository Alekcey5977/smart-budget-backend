from datetime import datetime
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models import Transaction, Bank, Merchant, Category, MCC_Category
from app.schemas import (
    Validate_Bank_Account, CategoryCreate, MCCCategoryCreate,
    MerchantCreate, BankCreate, BankAccountCreate, TransactionCreate
)
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


@router.post("/categories", status_code=status.HTTP_201_CREATED)
async def create_category(
    category: CategoryCreate,
    transaction_repo: TransactionRepository = Depends(get_transactions_repository)
):
    """Создание категории"""
    result = await transaction_repo.create_category(category)
    return transaction_repo.to_dict(result)


@router.post("/categories/bulk", status_code=status.HTTP_201_CREATED)
async def create_categories_bulk(
    categories: List[CategoryCreate],
    transaction_repo: TransactionRepository = Depends(get_transactions_repository)
):
    """Массовое создание категорий"""
    return await transaction_repo.bulk_create_categories(categories)


@router.post("/mcc_categories", status_code=status.HTTP_201_CREATED)
async def create_mcc_category(
    mcc: MCCCategoryCreate,
    transaction_repo: TransactionRepository = Depends(get_transactions_repository)
):
    """Создание MCC категории"""
    result = await transaction_repo.create_mcc_category(mcc)
    return transaction_repo.to_dict(result)


@router.post("/mcc_categories/bulk", status_code=status.HTTP_201_CREATED)
async def create_mcc_categories_bulk(
    mcc_list: List[MCCCategoryCreate],
    transaction_repo: TransactionRepository = Depends(get_transactions_repository)
):
    """Массовое создание MCC категорий"""
    return await transaction_repo.bulk_create_mcc_categories(mcc_list)


@router.post("/merchants", status_code=status.HTTP_201_CREATED)
async def create_merchant(
    merchant: MerchantCreate,
    transaction_repo: TransactionRepository = Depends(get_transactions_repository)
):
    """Создание мерчанта"""
    result = await transaction_repo.create_merchant(merchant)
    return transaction_repo.to_dict(result)


@router.post("/merchants/bulk", status_code=status.HTTP_201_CREATED)
async def create_merchants_bulk(
    merchants: List[MerchantCreate],
    transaction_repo: TransactionRepository = Depends(get_transactions_repository)
):
    """Массовое создание мерчантов"""
    return await transaction_repo.bulk_create_merchants(merchants)


@router.post("/banks", status_code=status.HTTP_201_CREATED)
async def create_bank(
    bank: BankCreate,
    transaction_repo: TransactionRepository = Depends(get_transactions_repository)
):
    """Создание банка"""
    result = await transaction_repo.create_bank(bank)
    return transaction_repo.to_dict(result)


@router.post("/banks/bulk", status_code=status.HTTP_201_CREATED)
async def create_banks_bulk(
    banks: List[BankCreate],
    transaction_repo: TransactionRepository = Depends(get_transactions_repository)
):
    """Массовое создание банков"""
    return await transaction_repo.bulk_create_banks(banks)


@router.post("/bank_accounts", status_code=status.HTTP_201_CREATED)
async def create_bank_account(
    account: BankAccountCreate,
    transaction_repo: TransactionRepository = Depends(get_transactions_repository)
):
    """Создание банковского счета"""
    result = await transaction_repo.create_bank_account(account)
    return transaction_repo.to_dict(result)


@router.post("/bank_accounts/bulk", status_code=status.HTTP_201_CREATED)
async def create_bank_accounts_bulk(
    accounts: List[BankAccountCreate],
    transaction_repo: TransactionRepository = Depends(get_transactions_repository)
):
    """Массовое создание банковских счетов"""
    return await transaction_repo.bulk_create_bank_accounts(accounts)


@router.post("/transactions", status_code=status.HTTP_201_CREATED)
async def create_transaction(
    transaction: TransactionCreate,
    transaction_repo: TransactionRepository = Depends(get_transactions_repository)
):
    """Создание транзакции"""
    result = await transaction_repo.create_transaction(transaction)
    return transaction_repo.to_dict(result)


@router.post("/transactions/bulk", status_code=status.HTTP_201_CREATED)
async def create_transactions_bulk(
    transactions: List[TransactionCreate],
    transaction_repo: TransactionRepository = Depends(get_transactions_repository)
):
    """Массовое создание транзакций"""
    return await transaction_repo.bulk_create_transactions(transactions)
