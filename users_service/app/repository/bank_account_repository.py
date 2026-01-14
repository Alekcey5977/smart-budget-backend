import os
import httpx
import logging
from decimal import Decimal
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.schemas import Bank_AccountCreate
from app.auth import get_bank_account_number_hash
from app.models import Bank_Accounts, Bank

logger = logging.getLogger(__name__)


TRANSACTIONS_SERVICE_URL = os.getenv("TRANSACTIONS_SERVICE_URL")
PSEUDO_BANK_SERVICE_URL = os.getenv("PSEUDO_BANK_SERVICE_URL")


class Bank_AccountRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_or_create_bank(self, bank_name: str) -> int:
        """Получить или создать банк по имени"""
        bank_name = bank_name.strip()

        # Ищем существующий банк
        result = await self.db.execute(
            select(Bank).where(Bank.name == bank_name)
        )
        bank = result.scalars().first()

        if bank:
            return bank.id

        # Создаем новый банк
        new_bank = Bank(name=bank_name)
        self.db.add(new_bank)
        await self.db.flush()  # Получаем ID не коммитя
        return new_bank.id

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
                    f"{TRANSACTIONS_SERVICE_URL}/transactions/trigger_sync",
                    json={"bank_account_hash": bank_account_hash,
                          "user_id": user_id}
                )
        except Exception as e:
            logger.error(f"[SYNC ERROR] {e}")
    
    
    async def calling_validate_account(self, bank_account_hash: str):
        """Вызов валидации счёта в pseudo_bank_service"""
        logger.info(f"[DEBUG] Calling pseudo bank with hash: {bank_account_hash}")
        logger.info(f"[DEBUG] URL: {PSEUDO_BANK_SERVICE_URL}/pseudo_bank/validate_account")
        async with httpx.AsyncClient(timeout=3.0) as client:
            resp = await client.post(
                f"{PSEUDO_BANK_SERVICE_URL}/pseudo_bank/validate_account",
                json={"bank_account_hash": bank_account_hash}
            )
            logger.info(f"[DEBUG] Response status: {resp.status_code}")
            logger.info(f"[DEBUG] Response body: {resp.text}")
            return resp
        


    async def create(self, user_id: int, bank_account: Bank_AccountCreate):
        """Создать новый банковский счет"""
        account_number = bank_account.bank_account_number.strip()

        # Шифрование счёта
        account_hash = get_bank_account_number_hash(account_number)
        logger.info(f"[DEBUG] Account number: {account_number}")
        logger.info(f"[DEBUG] Account hash: {account_hash}")


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

        # Получаем или создаем банк
        bank_id = await self.get_or_create_bank(bank_account.bank)

        new_account = Bank_Accounts(
            user_id=user_id,
            bank_account_hash=account_hash,
            bank_account_name=bank_account.bank_account_name,
            currency=currency,
            bank_id=bank_id,
            balance=balance
        )

        self.db.add(new_account)
        await self.db.commit()
        await self.db.refresh(new_account)

        # Загружаем relationship bank для доступа вне сессии
        await self.db.refresh(new_account, ["bank"])

        # Возвращаем account и hash для фоновой синхронизации
        return new_account, account_hash

    async def get_all_by_user_id(self, user_id: int):
        """Получить все банковские счета пользователя с информацией о банке"""
        from sqlalchemy.orm import selectinload

        result = await self.db.execute(
            select(Bank_Accounts)
            .options(selectinload(Bank_Accounts.bank))
            .where(Bank_Accounts.user_id == user_id)
        )
        return result.scalars().all()

    async def delete(self, bank_account_id: int, user_id: int):
        """Удалить банковский счет пользователя"""
        result = await self.db.execute(
            select(Bank_Accounts).where(
                Bank_Accounts.bank_account_id == bank_account_id,
                Bank_Accounts.user_id == user_id
            )
        )
        account = result.scalars().first()

        if not account:
            return None

        await self.db.delete(account)
        await self.db.commit()
        return account
