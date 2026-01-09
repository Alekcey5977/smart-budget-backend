from datetime import datetime
import httpx
from typing import Dict
from sqlalchemy import insert, select, text, update
from sqlalchemy.ext.asyncio import AsyncSession
from app.models import Category, MCC_Category, Merchant, Bank, Bank_Account, Transaction

class SyncRepository:
    def __init__(self, db):
        self.db = db

    async def get_or_create_account_stub(self, bank_account_hash: str, user_id: int) -> Bank_Account:
        """Получить счёт или создать заглушку"""
        result = await self.db.execute(
            select(Bank_Account).where(
                Bank_Account.bank_account_hash == bank_account_hash)
        )
        account = result.scalar_one_or_none()

        if account is None:
            account = Bank_Account(
                user_id=user_id,
                bank_account_hash=bank_account_hash,
                bank_account_name="Imported Account",
                bank_id=1,
                currency="RUB",
                balance=0,
                is_deleted=False
            )
            self.db.add(account)
            await self.db.commit()
            await self.db.refresh(account)

        return account

    async def validate_account_access(self, account: Bank_Account, user_id: int) -> bool:
        """Проверить, имеет ли пользователь доступ к счёту"""
        return account.user_id == user_id and not account.is_deleted
    
    async def upsert_categories(self, categories: list) -> int:
        """Добавление категорий"""
        if not categories:
            return 0
        stmt = insert(Category).values(
            categories).on_conflict_do_nothing(index_elements=["id"])
        res = await self.db.execute(stmt)
        return res.rowcount

    async def upsert_mcc(self, mcc_list: list) -> int:
        """Добавление MCC"""
        if not mcc_list:
            return 0
        stmt = insert(MCC_Category).values(
            mcc_list).on_conflict_do_nothing(index_elements=["mcc"])
        res = await self.db.execute(stmt)
        return res.rowcount

    async def upsert_merchants(self, merchants: list) -> int:
        """Добавление мерчантов"""
        if not merchants:
            return 0
        stmt = insert(Merchant).values(
            merchants).on_conflict_do_nothing(index_elements=["id"])
        res = await self.db.execute(stmt)
        return res.rowcount

    async def upsert_banks(self, banks: list) -> int:
        """Добавление банков"""
        if not banks:
            return 0
        stmt = insert(Bank).values(
            banks).on_conflict_do_nothing(index_elements=["id"])
        res = await self.db.execute(stmt)
        return res.rowcount
    
    async def upsert_bank_accounts(self, accounts: list) -> int:
        """Добавление банковских счетов"""
        if not accounts:
            return 0

        excluded = insert(Bank_Account).excluded
        stmt = (
            insert(Bank_Account)
            .values(accounts)
            .on_conflict_do_update(
                index_elements=["bank_account_hash"],
                set_=dict(
                    bank_account_name=excluded.bank_account_name,
                    bank_id=excluded.bank_id,
                    currency=excluded.currency,
                    balance=excluded.balance,
                    updated_at=excluded.updated_at
                )
            )
        )
        result = await self.db.execute(stmt)
        return result.rowcount

    async def upsert_transactions(self, transactions: list) -> int:
        """Добавление транзакций"""
        if not transactions:
            return 0
        stmt = insert(Transaction).values(
            transactions).on_conflict_do_nothing(index_elements=["id"])
        res = await self.db.execute(stmt)
        return res.rowcount
    
    async def sync_by_account(self, bank_account_hash: str) -> Dict[str, int]:
        """Синхронизация данных банковского счёта"""

        result = await self.db.execute(
            select(Bank_Account.last_synced_at)
            .where(Bank_Account.bank_account_hash == bank_account_hash)
        )
        last_synced = result.scalar()

        # Формируем URL с параметром since
        url = f"http://localhost:8004/pseudo_bank/account/{bank_account_hash}/export"
        if last_synced:
            url += f"?since={last_synced.isoformat().replace('+00:00', 'Z')}"

        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(url)
            if resp.status_code == 404:
                raise ValueError(
                    f"Account {bank_account_hash} not found in pseudo_bank")
            resp.raise_for_status()
            data = resp.json()

        stats = {
            "categories": await self.upsert_categories(data.get("categories", [])),
            "mcc": await self.upsert_mcc(data.get("mcc_categories", [])),
            "merchants": await self.upsert_merchants(data.get("merchants", [])),
            "banks": await self.upsert_banks([data["bank"]] if data.get("bank") else []),
            "bank_accounts": await self.upsert_bank_accounts([data["bank_account"]]),
            "transactions": await self.upsert_transactions(data.get("transactions", []))
        }

        if data.get("transactions"):
            newest_time = None
            for tx in data["transactions"]:
                tx_time = datetime.fromisoformat(
                    tx["created_at"].replace("Z", "+00:00"))
                if newest_time is None or tx_time > newest_time:
                    newest_time = tx_time

            if newest_time:
                await self.db.execute(
                    update(Bank_Account)
                    .where(Bank_Account.bank_account_hash == bank_account_hash)
                    .values(last_synced_at=newest_time)
                )

        await self.db.commit()
        return stats
    
    async def get_all_active_account_hashes(self) -> list[tuple[str, int]]:
        """Возвращает [(bank_account_hash, user_id)]"""
        result = await self.db.execute(
            select(Bank_Account.bank_account_hash, Bank_Account.user_id)
            .where(Bank_Account.is_deleted.is_(False))
        )
        return result.fetchall()


    async def sync_incremental(self) -> dict:
        accounts = await self.get_all_active_account_hashes()
        total = {"processed": len(accounts), "success": 0, "failed": 0}

        for acc_hash, user_id in accounts:
            try:
                await self.sync_by_account(acc_hash)
                total["success"] += 1
            except Exception as e:
                print(f"Failed to sync {acc_hash} for user {user_id}: {e}")
                total["failed"] += 1

        return {"synced": total}
