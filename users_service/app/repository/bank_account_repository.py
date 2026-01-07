import httpx
import asyncio
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.schemas import Bank_AccountCreate
from app.auth import hash_account_number
from app.models import User, Bank_Accounts
from decimal import Decimal


class Bank_AccountRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_account_bank(self, bank_account_hash: str):
        """Проверка дубликата счёта"""
        existing = await self.db.execute(
            select(Bank_Accounts).where(
                Bank_Accounts. bank_account_hash == bank_account_hash)
        )

        return existing.scalars().first()
    
    async def trigger_transaction_sync(self, bank_account_hash: str, user_id: int):
        """Вызов синхронизации данных в transaction_service"""
        try:
            async with httpx.AsyncClient(timeout=3.0) as client:
                await client.post(
                    "http://localhost:8002/transactions/trigger_sync",
                    json={"bank_account_hash": bank_account_hash,
                          "user_id": user_id}
                )
        except Exception as e:
            print(f"[SYNC ERROR] {e}")
    
    
    async def calling_validate_account(self, bank_account_hash: str):
        """Вызов валидации счёта в pseudo_bank_service"""
        async with httpx.AsyncClient(timeout=3.0) as client:
            resp = await client.post(
                "http://localhost:8004/pseudo_bank/validate_account",
                json={"account_hash": bank_account_hash}
            )
            return resp
        


    async def create(self, user_id: int, bank_account: Bank_AccountCreate):
        """Создать новый банковский счет"""
        account_number = bank_account.bank_account_number.strip()

        # Шифрование счёта
        account_hash = hash_account_number(account_number)


        existing_bank_account = await self.get_account_bank(account_hash)

        if existing_bank_account:
            raise HTTPException(
                status_code=400,
                detail="Bank account with this number already exists"
            )

        resp = await self.calling_validate_account(account_hash)

        if resp.status_code == 404:
            raise HTTPException(
                400, "Bank account does not exist in the bank system")
        if resp.status_code != 200:
            err = resp.json().get("detail", resp.text)
            raise HTTPException(400, f"Bank validation failed: {err}")

        bank_data = resp.json()
        
        try:
            balance = Decimal(str(bank_data.get("balance", "0.00")))
        except (ValueError, TypeError):
            balance = Decimal("0.00")
        currency = bank_data.get("currency", "RUB")

        new_account = Bank_Accounts(
            user_id=user_id,
            bank_account_hash=account_hash,
            bank_account_name=bank_account.bank_account_name,
            currency=currency,
            bank=bank_account.bank,
            balance=balance
        )

        self.db.add(new_account)
        await self.db.commit()
        await self.db.refresh(new_account)

        asyncio.create_task(self.trigger_transaction_sync(account_hash, user_id))
        
        return new_account
