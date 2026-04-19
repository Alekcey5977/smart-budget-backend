import logging
import os
from datetime import datetime
from typing import Dict
from uuid import uuid4

import httpx
from app.cache import cache_client
from app.models import Bank, Bank_Account, Category, MCC_Category, Merchant, Transaction
from sqlalchemy import select, update
from sqlalchemy.dialects.postgresql import insert

from shared.event_publisher import EventPublisher
from shared.event_schema import DomainEvent

logger = logging.getLogger(__name__)
PSEUDO_BANK_SERVICE_URL = os.getenv("PSEUDO_BANK_SERVICE_URL")


class SyncRepository:
    def __init__(self, db):
        self.db = db

    async def get_user_account_hashes(self, user_id: int) -> list[str]:
        """Получить все хеши счетов пользователя из users-service БД"""
        # Примечание: в transactions-service нет связи с users-service БД
        # Поэтому мы получаем хеши из уже синхронизированных счетов
        result = await self.db.execute(
            select(Bank_Account.bank_account_hash)
            .where(Bank_Account.user_id == user_id)
            .where(Bank_Account.is_deleted.is_(False))
        )
        return [row[0] for row in result.fetchall()]

    async def upsert_categories(self, categories: list) -> int:
        """Добавление категорий"""
        if not categories:
            return 0
        stmt = insert(Category).values(categories).on_conflict_do_nothing(index_elements=["id"])
        res = await self.db.execute(stmt)
        return res.rowcount

    async def upsert_mcc(self, mcc_list: list) -> int:
        """Добавление MCC"""
        if not mcc_list:
            return 0
        stmt = insert(MCC_Category).values(mcc_list).on_conflict_do_nothing(index_elements=["mcc"])
        res = await self.db.execute(stmt)
        return res.rowcount

    async def upsert_merchants(self, merchants: list) -> int:
        """Добавление мерчантов"""
        if not merchants:
            return 0
        stmt = insert(Merchant).values(merchants).on_conflict_do_nothing(index_elements=["id"])
        res = await self.db.execute(stmt)
        return res.rowcount

    async def upsert_banks(self, banks: list) -> int:
        """Добавление банков"""
        if not banks:
            return 0
        stmt = insert(Bank).values(banks).on_conflict_do_nothing(index_elements=["id"])
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
                    user_id=excluded.user_id,
                    bank_account_name=excluded.bank_account_name,
                    bank_id=excluded.bank_id,
                    currency=excluded.currency,
                    balance=excluded.balance,
                    updated_at=excluded.updated_at,
                    # Сбрасываем last_synced_at при смене владельца,
                    # чтобы следующий sync забрал всю историю заново
                    last_synced_at=None,
                ),
            )
        )
        result = await self.db.execute(stmt)
        return result.rowcount

    async def upsert_transactions(self, transactions: list) -> int:
        """Добавление транзакций"""
        if not transactions:
            return 0
        excluded = insert(Transaction).excluded
        stmt = (
            insert(Transaction)
            .values(transactions)
            .on_conflict_do_update(
                index_elements=["id"],
                # При смене владельца счёта транзакции переходят новому пользователю
                set_=dict(user_id=excluded.user_id),
            )
        )
        res = await self.db.execute(stmt)
        return res.rowcount

    async def sync_by_account(self, bank_account_hash: str, user_id: int) -> Dict[str, int]:
        """
        Синхронизация данных банковского счёта с заменой user_id.

        Pseudo bank хранит все данные с user_id=999 (тестовые данные).
        Мы заменяем 999 на реальный user_id при сохранении в нашу БД.
        """
        lock_key = f"sync:lock:{bank_account_hash}"
        try:
            acquired = await cache_client.redis.set(lock_key, 1, nx=True, ex=60)
        except Exception:
            acquired = True  # при недоступности Redis не блокируем sync

        if not acquired:
            logger.info(f"[SYNC] Lock занят для {bank_account_hash}, пропускаем дублирующий запрос")
            return {"categories": 0, "mcc": 0, "merchants": 0, "banks": 0, "bank_accounts": 0, "transactions": 0}

        try:
            return await self._do_sync(bank_account_hash, user_id)
        finally:
            try:
                await cache_client.redis.delete(lock_key)
            except Exception:
                pass

    async def _do_sync(self, bank_account_hash: str, user_id: int) -> Dict[str, int]:
        logger.info(f"[SYNC] Starting sync for account {bank_account_hash}, user_id={user_id}")

        result = await self.db.execute(
            select(Bank_Account.last_synced_at).where(Bank_Account.bank_account_hash == bank_account_hash)
        )
        last_synced = result.scalar()
        logger.info(f"[SYNC] Last synced: {last_synced}")

        # Формируем URL с параметром since
        url = f"{PSEUDO_BANK_SERVICE_URL}/pseudo_bank/account/{bank_account_hash}/export"
        if last_synced:
            url += f"?since={last_synced.isoformat().replace('+00:00', 'Z')}"

        logger.info(f"[SYNC] Fetching data from: {url}")
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(url)
            if resp.status_code == 404:
                raise ValueError(f"Account {bank_account_hash} not found in pseudo_bank")
            resp.raise_for_status()
            data = resp.json()

        logger.info(
            f"[SYNC] Received data: categories={len(data.get('categories', []))}, mcc={len(data.get('mcc_categories', []))}, merchants={len(data.get('merchants', []))}, transactions={len(data.get('transactions', []))}"
        )
        logger.info(f"[SYNC] Bank data: {data.get('bank')}")
        logger.info(f"[SYNC] Bank account data: {data.get('bank_account')}")

        # Заменяем user_id в bank_account (999 → реальный user_id)
        bank_account = data.get("bank_account", {})
        if bank_account:
            bank_account["user_id"] = user_id
            # Конвертируем строковые даты в datetime объекты
            if "created_at" in bank_account and isinstance(bank_account["created_at"], str):
                bank_account["created_at"] = datetime.fromisoformat(bank_account["created_at"].replace("Z", "+00:00"))
            if "updated_at" in bank_account and isinstance(bank_account["updated_at"], str):
                bank_account["updated_at"] = datetime.fromisoformat(bank_account["updated_at"].replace("Z", "+00:00"))

        # Заменяем user_id во всех транзакциях (999 → реальный user_id)
        transactions = data.get("transactions", [])
        for tx in transactions:
            tx["user_id"] = user_id
            # Конвертируем строковые даты в datetime объекты
            if "created_at" in tx and isinstance(tx["created_at"], str):
                tx["created_at"] = datetime.fromisoformat(tx["created_at"].replace("Z", "+00:00"))

        logger.info("[SYNC] Upserting data...")
        stats = {
            "categories": await self.upsert_categories(data.get("categories", [])),
            "mcc": await self.upsert_mcc(data.get("mcc_categories", [])),
            "merchants": await self.upsert_merchants(data.get("merchants", [])),
            "banks": await self.upsert_banks([data["bank"]] if data.get("bank") else []),
            "bank_accounts": await self.upsert_bank_accounts([bank_account] if bank_account else []),
            "transactions": await self.upsert_transactions(transactions),
        }
        logger.info(f"[SYNC] Upsert stats: {stats}")

        if transactions:
            newest_time = None
            for tx in transactions:
                # created_at уже datetime объект после конвертации выше
                tx_time = tx["created_at"]
                if newest_time is None or tx_time > newest_time:
                    newest_time = tx_time

            if newest_time:
                await self.db.execute(
                    update(Bank_Account)
                    .where(Bank_Account.bank_account_hash == bank_account_hash)
                    .values(last_synced_at=newest_time)
                )

        await self.db.commit()

        try:
            publisher = EventPublisher()
            event = DomainEvent(
                event_id=str(uuid4()),
                event_type="sync.completed",
                source="transactions-service",
                timestamp=datetime.now(),
                payload={
                    "user_id": user_id,
                    "bank_account_hash": bank_account_hash,
                    "new_transactions_count": stats["transactions"],
                    "synced_at": datetime.now().isoformat(),
                },
            )
            await publisher.publish(event)
        except Exception as e:
            logger.warning(f"[SYNC] Не удалось опубликовать sync.completed: {e}")

        return stats

    async def get_all_active_account_hashes(self) -> list[tuple[str, int]]:
        """Возвращает [(bank_account_hash, user_id)]"""
        result = await self.db.execute(
            select(Bank_Account.bank_account_hash, Bank_Account.user_id).where(Bank_Account.is_deleted.is_(False))
        )
        return result.fetchall()

    async def sync_user_accounts(self, user_id: int) -> dict:
        """
        Синхронизация всех счетов конкретного пользователя.

        Получает хеши всех счетов пользователя из users-service БД
        (через Gateway), затем синхронизирует каждый счет.
        """
        # ВАЖНО: На данный момент мы можем синхронизировать только те счета,
        # которые УЖЕ есть в transactions-service БД.
        # Новые счета появятся после первого вызова trigger_sync.
        account_hashes = await self.get_user_account_hashes(user_id)

        total = {"processed": len(account_hashes), "success": 0, "failed": 0}

        for acc_hash in account_hashes:
            try:
                await self.sync_by_account(acc_hash, user_id)
                total["success"] += 1
            except Exception as e:
                print(f"Failed to sync {acc_hash} for user {user_id}: {e}")
                total["failed"] += 1

        return total

    async def sync_incremental(self) -> dict:
        """
        Синхронизация всех активных счетов в системе.
        Используется планировщиком каждые 10 минут.
        """
        accounts = await self.get_all_active_account_hashes()
        total = {"processed": len(accounts), "success": 0, "failed": 0}

        for acc_hash, user_id in accounts:
            try:
                await self.sync_by_account(acc_hash, user_id)
                total["success"] += 1
            except Exception as e:
                print(f"Failed to sync {acc_hash} for user {user_id}: {e}")
                total["failed"] += 1

        return {"synced": total}
