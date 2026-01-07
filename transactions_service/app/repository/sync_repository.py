import httpx
from typing import Dict
from sqlalchemy import insert, text
from sqlalchemy.ext.asyncio import AsyncSession
from app.models import Category, MCC_Category, Merchant, Bank, Bank_Account, Transaction

class SyncRepository:
    def __init__(self, db):
        self.db = db
    
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
                    balance=excluded.balance,
                    updated_at=excluded.updated_at,
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
        """Сохранение новых данных в БД"""
        async with httpx.AsyncClient(timeout=5) as client:
            url = f"http://localhost:8004/pseudo_bank/account/{bank_account_hash}/export"
            try:
                resp = await client.get(url)
                if resp.status_code == 404:
                    raise ValueError(
                        f"Account {bank_account_hash} not found in pseudo_bank")
                resp.raise_for_status()
                data = resp.json()
            except httpx.HTTPError as e:
                raise RuntimeError(
                    f"Failed to fetch data from pseudo_bank: {e}")
            
        stats = {}
        stats["categories"] = await self.upsert_categories(data.get("categories", []))
        stats["mcc"] = await self.upsert_mcc(data.get("mcc_categories", []))
        stats["merchants"] = await self.upsert_merchants(data.get("merchants", []))
        stats["banks"] = await self.upsert_banks([data["bank"]] if data.get("bank") else [])
        stats["bank_accounts"] = await self.upsert_bank_accounts([data["bank_account"]])
        stats["transactions"] = await self.upsert_transactions(data.get("transactions", []))

        await self.db.commit()
        
        return stats