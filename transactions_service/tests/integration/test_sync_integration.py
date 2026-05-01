import uuid
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from app.models import Bank, Bank_Account, Category
from httpx import AsyncClient
from sqlalchemy import select


class TestSyncIntegration:
    """Интеграционные тесты для синхронизации"""

    @pytest.mark.asyncio
    async def test_trigger_sync_endpoint_success(self, client: AsyncClient, db_session):
        """Тест эндпоинта /trigger_sync: полная цепочка"""

        # 1. Подготовка: мокаем httpx ответ от pseudo_bank
        acc_hash = "test_hash_123"
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "bank": {"id": 1, "name": "Test Bank"},
            "bank_account": {
                "bank_account_hash": acc_hash,
                "user_id": 999,
                "bank_account_name": "My Acc",
                "bank_id": 1,
                "currency": "RUB",
                "balance": "100.00",
                "created_at": "2023-01-01T00:00:00Z",
            },
            "categories": [{"id": 10, "name": "Food"}],
            "mcc_categories": [],
            "merchants": [],
            "transactions": [
                {
                    "id": str(uuid.uuid4()),
                    "user_id": 999,
                    "category_id": 10,
                    "bank_account_id": 1,
                    "amount": "50.00",
                    "type": "expense",
                    "created_at": "2023-01-01T12:00:00Z",
                }
            ],
        }

        mock_client_instance = AsyncMock()
        mock_client_instance.get.return_value = mock_response

        with patch("app.repository.sync_repository.httpx.AsyncClient", return_value=mock_client_instance) as mock_http:
            mock_http.return_value.__aenter__.return_value = mock_client_instance

            response = await client.post(
                "/transactions/trigger_sync", json={"bank_account_hash": acc_hash, "user_id": 123}
            )

        # Проверки
        assert response.status_code == 200, f"Response: {response.text}"
        data = response.json()
        assert data["status"] == "success"
        assert data["synced"]["categories"] == 1
        assert data["synced"]["transactions"] == 1

        # Проверяем, что данные записались в БД
        result = await db_session.execute(select(Category))
        categories = result.scalars().all()
        assert len(categories) == 1
        assert categories[0].name == "Food"

        result = await db_session.execute(select(Bank_Account))
        accounts = result.scalars().all()
        assert len(accounts) == 1
        assert accounts[0].user_id == 123
        assert accounts[0].bank_account_hash == acc_hash

    @pytest.mark.asyncio
    async def test_trigger_sync_not_found(self, client: AsyncClient):
        """Тест обработки 404 от внешнего сервиса"""
        mock_response = MagicMock()
        mock_response.status_code = 404

        mock_client_instance = AsyncMock()
        mock_client_instance.get.return_value = mock_response

        with patch("app.repository.sync_repository.httpx.AsyncClient") as mock_http:
            mock_http.return_value.__aenter__.return_value = mock_client_instance

            response = await client.post(
                "/transactions/trigger_sync", json={"bank_account_hash": "missing", "user_id": 123}
            )

        assert response.status_code == 404
        assert "not found" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_sync_user_accounts_endpoint(self, client: AsyncClient, db_session):
        """Тест синхронизации всех счетов пользователя"""

        # 1. Создаем счет в БД, который нужно синхронизировать
        existing_acc = Bank_Account(
            id=1,
            user_id=123,
            bank_account_hash="acc_to_sync",
            bank_account_name="Old Name",
            bank_id=99,
            currency="RUB",
            balance=0,
            is_deleted=False,
        )
        db_session.add(existing_acc)
        await db_session.flush()

        # 2. Мокаем внешнюю синхронизацию
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "bank": {"id": 99, "name": "Bank"},
            "bank_account": {
                "bank_account_hash": "acc_to_sync",
                "user_id": 999,
                "bank_account_name": "New Name",  # Обновили имя
                "bank_id": 99,
                "currency": "RUB",
                "balance": "500.00",
                "created_at": "2023-01-01T00:00:00Z",
            },
            "categories": [],
            "mcc_categories": [],
            "merchants": [],
            "transactions": [],
        }

        mock_client_instance = AsyncMock()
        mock_client_instance.get.return_value = mock_response

        with (
            patch("app.repository.sync_repository.httpx.AsyncClient") as mock_http,
            patch("app.repository.sync_repository.EventPublisher") as mock_publisher_cls,
        ):
            mock_http.return_value.__aenter__.return_value = mock_client_instance
            mock_publisher = AsyncMock()
            mock_publisher.publish = AsyncMock()
            mock_publisher_cls.return_value = mock_publisher

            response = await client.post("/transactions/sync_user_accounts", json={"user_id": 123})

        # 3. Проверки
        assert response.status_code == 200
        assert response.json()["success"] == 1

        # Проверяем что счет обновился
        await db_session.refresh(existing_acc)
        assert existing_acc.bank_account_name == "New Name"
        assert float(existing_acc.balance) == 500.00

        # Проверяем ровно одно событие sync.completed на весь batch
        mock_publisher.publish.assert_awaited_once()
        event = mock_publisher.publish.await_args.args[0]
        assert event.event_type == "sync.completed"
        assert event.payload["user_id"] == 123

    @pytest.mark.asyncio
    async def test_sync_incremental_logic(self, client: AsyncClient, db_session):
        """Тест логики обновления last_synced_at"""
        from app.repository.sync_repository import SyncRepository

        repo = SyncRepository(db_session)
        acc_hash = "logic_test_hash"

        # 1. Мок данных
        tx_time_str = "2023-05-20T15:00:00Z"
        mock_json = {
            "bank": None,
            "bank_account": None,
            "categories": [],
            "mcc_categories": [],
            "merchants": [],
            "transactions": [
                {
                    "id": str(uuid.uuid4()),
                    "user_id": 1,
                    "category_id": 1,
                    "bank_account_id": 1,
                    "amount": "100.00",
                    "type": "expense",
                    "created_at": tx_time_str,
                }
            ],
        }

        # Создаем зависимости для транзакции
        cat = Category(id=1, name="Cat")

        acc = Bank_Account(
            id=1,
            user_id=123,
            bank_account_hash=acc_hash,
            bank_account_name="Test Account",
            bank_id=1,
            currency="RUB",
            balance=0,
        )

        bank = Bank(id=1, name="B")
        db_session.add_all([cat, acc, bank])
        await db_session.flush()

        # 2. Вызов
        mock_resp = MagicMock(status_code=200)
        mock_resp.json.return_value = mock_json

        mock_client = AsyncMock()
        mock_client.get.return_value = mock_resp

        with patch("app.repository.sync_repository.httpx.AsyncClient", return_value=mock_client):
            mock_client.__aenter__.return_value = mock_client
            await repo.sync_by_account(acc_hash, 123)

        # 3. Проверка времени
        await db_session.refresh(acc)
        assert acc.last_synced_at is not None

        expected_time = datetime.fromisoformat(tx_time_str.replace("Z", "+00:00"))
        assert acc.last_synced_at.replace(tzinfo=None) == expected_time.replace(tzinfo=None)
