# tests/integration/test_transactions_integration.py
import pytest
from app.models import Bank
from sqlalchemy import select

# Указываем, что все тесты в этом модуле асинхронные
pytestmark = pytest.mark.asyncio

class TestSQLiteIntegration:
    """Интеграционные тесты на SQLite"""

    async def test_create_bank_and_verify_in_db(self, client, db_engine):
        """Тест создания банка через API и проверки в БД"""
        
        # 1. Создаем банк через API
        response = await client.post(
            "/pseudo_bank/banks",
            json={"id": 100, "name": "SQLite Bank"}        
        )

        assert response.status_code == 201
        assert response.json()["name"] == "SQLite Bank"

        # 2. Проверяем напрямую в БД
        from sqlalchemy.ext.asyncio import AsyncSession
        from sqlalchemy.orm import sessionmaker

        async_session_maker = sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)
        
        async with async_session_maker() as session:
            result = await session.execute(select(Bank).where(Bank.id == 100))
            bank = result.scalar_one_or_none()
            
            assert bank is not None
            assert bank.name == "SQLite Bank"

    async def test_full_transaction_flow(self, client):
        """Полный цикл: Банк -> Счет -> Категория -> Транзакция"""
        
        # 1. Создаем Банк
        r_bank = await client.post("/pseudo_bank/banks", json={"id": 1, "name": "Bank Test"})
        assert r_bank.status_code == 201

        # 2. Создаем Категорию
        r_cat = await client.post("/pseudo_bank/categories", json={"id": 10, "name": "Food"})
        assert r_cat.status_code == 201

        # 3. Создаем Счет
        acc_data = {
            "user_id": 1,
            "bank_account_hash": "unique_sqlite_hash_1",
            "bank_account_name": "Test Acc",
            "bank_id": 1,
            "balance": "5000.00"
        }
        r_acc = await client.post("/pseudo_bank/bank_accounts", json=acc_data)
        assert r_acc.status_code == 201
        account_id = r_acc.json()["id"]

        # 4. Создаем Транзакцию
        tx_data = {
            "user_id": 1,
            "category_id": 10,
            "bank_account_id": account_id,
            "amount": "-150.00",
            "type": "expense"
        }
        r_tx = await client.post("/pseudo_bank/transactions", json=tx_data)
        
        assert r_tx.status_code == 201

    async def test_validate_account_sqlite(self, client):
        """Проверка валидации счета на SQLite"""

        await client.post("/pseudo_bank/banks", json={"id": 2, "name": "Val Bank"})
        await client.post("/pseudo_bank/bank_accounts", json={
            "user_id": 1,
            "bank_account_hash": "check_me",
            "bank_account_name": "n",
            "bank_id": 2,
            "balance": "100.50"
        })

        # Проверяем валидацию
        response = await client.post(
            "/pseudo_bank/validate_account",
            json={"bank_account_hash": "check_me"}
        )

        assert response.status_code == 200
        data = response.json()
        
        assert data["balance"] == "100.50" 
        assert data["currency"] == "RUB"