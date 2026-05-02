import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

PSEUDO_URL = os.getenv("PSEUDO_BANK_SERVICE_URL")


def _make_redis_mock(lock_acquired=True):
    """Возвращает мок Redis с настроенным SET NX и DELETE"""
    mock_redis = AsyncMock()
    mock_redis.set = AsyncMock(return_value=lock_acquired)
    mock_redis.delete = AsyncMock()
    return mock_redis


class TestSyncRepository:
    """Тесты для SyncRepository"""

    @pytest.mark.asyncio
    async def test_get_user_account_hashes(self, sync_repository, mock_db_session):
        """Тест получения хешей счетов пользователя"""
        # Настраиваем мок результата БД
        mock_result = MagicMock()
        mock_result.fetchall.return_value = [("hash1",), ("hash2",)]
        mock_db_session.execute.return_value = mock_result

        hashes = await sync_repository.get_user_account_hashes(123)

        assert hashes == ["hash1", "hash2"]
        mock_db_session.execute.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_upsert_empty_list(self, sync_repository, mock_db_session):
        """Тест: upsert не должен вызывать БД при пустом списке"""
        count = await sync_repository.upsert_categories([])
        assert count == 0
        mock_db_session.execute.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_upsert_bank_accounts(self, sync_repository, mock_db_session):
        """Тест upsert для банковских счетов"""
        mock_result = MagicMock()
        mock_result.rowcount = 1
        mock_db_session.execute.return_value = mock_result

        accounts = [{"bank_account_hash": "h1", "user_id": 1, "balance": 100}]
        count = await sync_repository.upsert_bank_accounts(accounts)

        assert count == 1
        mock_db_session.execute.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_sync_by_account_success_full_data(self, sync_repository, mock_db_session):
        """Тест успешной синхронизации с полными данными"""
        acc_hash = "test_hash"
        user_id = 123

        # Настраиваем последовательность возвратов для execute
        # Порядок вызовов в sync_by_account:
        # 1. Select last_synced
        # 2. Insert Category
        # 3. Insert MCC
        # 4. Insert Merchant
        # 5. Insert Bank
        # 6. Insert Bank Account
        # 7. Insert Transaction
        # 8. Update last_synced

        mock_result_ok = MagicMock()
        mock_result_ok.rowcount = 1
        mock_result_ok.scalar.return_value = None

        # Формируем список из 8 результатов
        results = [mock_result_ok] + [mock_result_ok for _ in range(7)]
        mock_db_session.execute.side_effect = results

        # Мокируем HTTP запрос
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "bank": {"id": 1, "name": "TestBank"},
            "bank_account": {
                "bank_account_hash": acc_hash,
                "user_id": 999,  # Должен замениться на 123
                "created_at": "2023-01-01T00:00:00Z",
                "updated_at": "2023-01-01T00:00:00Z",
            },
            "categories": [{"id": 1, "name": "Food"}],
            "mcc_categories": [{"mcc": 1, "name": "Test"}],
            "merchants": [{"id": 1, "name": "Shop"}],
            "transactions": [
                {
                    "id": "uuid-tx-1",
                    "user_id": 999,  # Должен замениться на 123
                    "created_at": "2023-01-01T12:00:00Z",
                    "category_id": 1,
                    "bank_account_id": 1,
                    "amount": 100.0,
                    "type": "expense",
                }
            ],
        }

        # Мокируем httpx.AsyncClient
        mock_client_instance = AsyncMock()
        mock_client_instance.get.return_value = mock_response

        mock_redis = _make_redis_mock(lock_acquired=True)

        with (
            patch("app.repository.sync_repository.httpx.AsyncClient") as mock_async_client,
            patch("app.repository.sync_repository.cache_client") as mock_cache,
            patch("app.repository.sync_repository.EventPublisher") as mock_publisher_cls,
        ):
            mock_async_client.return_value.__aenter__.return_value = mock_client_instance
            mock_cache.redis = mock_redis
            mock_publisher = AsyncMock()
            mock_publisher.publish = AsyncMock()
            mock_publisher_cls.return_value = mock_publisher

            stats = await sync_repository.sync_by_account(acc_hash, user_id)

        # Проверки результата
        assert stats["transactions"] == 1
        assert stats["categories"] == 1
        mock_db_session.commit.assert_awaited_once()

        # Проверяем URL
        expected_url = f"{PSEUDO_URL}/pseudo_bank/account/{acc_hash}/export"
        mock_client_instance.get.assert_awaited_once_with(expected_url)

        # Проверяем Redis lock: SET NX → DELETE
        mock_redis.set.assert_awaited_once_with(f"sync:lock:{acc_hash}", 1, nx=True, ex=60)
        mock_redis.delete.assert_awaited_once_with(f"sync:lock:{acc_hash}")

        # Проверяем публикацию sync.completed
        mock_publisher.publish.assert_awaited_once()
        published_event = mock_publisher.publish.await_args.args[0]
        assert published_event.event_type == "sync.completed"
        assert published_event.payload["user_id"] == user_id
        assert published_event.payload["new_transactions_count"] == 1

    @pytest.mark.asyncio
    async def test_sync_by_account_skips_when_lock_taken(self, sync_repository, mock_db_session):
        """Если Redis lock занят — sync не выполняется, возвращается пустой результат"""
        mock_redis = _make_redis_mock(lock_acquired=False)

        with patch("app.repository.sync_repository.cache_client") as mock_cache:
            mock_cache.redis = mock_redis
            stats = await sync_repository.sync_by_account("locked_hash", 123)

        assert stats["transactions"] == 0
        assert stats["categories"] == 0
        mock_db_session.execute.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_sync_by_account_not_found(self, sync_repository, mock_db_session):
        """Тест: счет не найден в pseudo_bank (404)"""
        mock_select_result = MagicMock()
        mock_select_result.scalar.return_value = None
        mock_db_session.execute.return_value = mock_select_result

        mock_response = MagicMock()
        mock_response.status_code = 404

        mock_client_instance = AsyncMock()
        mock_client_instance.get.return_value = mock_response

        mock_redis = _make_redis_mock(lock_acquired=True)

        with (
            patch("app.repository.sync_repository.httpx.AsyncClient") as mock_async_client,
            patch("app.repository.sync_repository.cache_client") as mock_cache,
        ):
            mock_async_client.return_value.__aenter__.return_value = mock_client_instance
            mock_cache.redis = mock_redis

            with pytest.raises(ValueError, match="not found in pseudo_bank"):
                await sync_repository.sync_by_account("missing_hash", 123)

        mock_redis.delete.assert_awaited_once_with("sync:lock:missing_hash")

    @pytest.mark.asyncio
    async def test_sync_by_account_updates_last_synced(self, sync_repository, mock_db_session):
        """Тест обновления времени последней синхронизации"""
        # Сценарий: есть только транзакции, нет категорий/банков

        # 1. Результат для SELECT last_synced
        mock_select_result = MagicMock()
        mock_select_result.scalar.return_value = None

        # 2. Результат для INSERT transaction
        mock_insert_result = MagicMock()
        mock_insert_result.rowcount = 1

        # 3. Результат для UPDATE last_synced
        mock_update_result = MagicMock()

        # Ожидаем всего 3 вызова execute:
        # 1. Select
        # 2. Insert Transaction (остальные upsert вернут 0, так как списки пусты)
        # 3. Update last_synced
        mock_db_session.execute.side_effect = [mock_select_result, mock_insert_result, mock_update_result]

        tx_time = "2023-05-20T15:00:00Z"
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "bank": None,
            "bank_account": None,
            "categories": [],
            "mcc_categories": [],
            "merchants": [],
            "transactions": [
                {
                    "id": "uuid",
                    "user_id": 1,
                    "created_at": tx_time,
                    "category_id": 1,
                    "bank_account_id": 1,
                    "amount": 10,
                    "type": "exp",
                }
            ],
        }

        mock_client_instance = AsyncMock()
        mock_client_instance.get.return_value = mock_response

        mock_redis = _make_redis_mock(lock_acquired=True)

        with (
            patch("app.repository.sync_repository.httpx.AsyncClient") as mock_async_client,
            patch("app.repository.sync_repository.cache_client") as mock_cache,
            patch("app.repository.sync_repository.EventPublisher") as mock_publisher_cls,
        ):
            mock_async_client.return_value.__aenter__.return_value = mock_client_instance
            mock_cache.redis = mock_redis
            mock_publisher_cls.return_value.publish = AsyncMock()

            await sync_repository.sync_by_account("h1", 1)

        # Проверяем количество вызовов
        assert mock_db_session.execute.await_count == 3

        # Проверяем, что последний вызов был UPDATE
        last_call = mock_db_session.execute.await_args_list[-1]
        statement_str = str(last_call.args[0])
        assert "UPDATE" in statement_str.upper()

    @pytest.mark.asyncio
    async def test_sync_incremental(self, sync_repository):
        """Тест периодической синхронизации всех счетов"""
        accounts = [("hash1", 1), ("hash2", 2)]

        # Используем patch.object для мокирования методов внутри класса
        with (
            patch.object(sync_repository, "get_all_active_account_hashes", new_callable=AsyncMock) as mock_get_hashes,
            patch.object(sync_repository, "sync_by_account", new_callable=AsyncMock) as mock_sync_account,
        ):
            mock_get_hashes.return_value = accounts
            mock_sync_account.return_value = {"transactions": 1}

            result = await sync_repository.sync_incremental()

        assert result["synced"]["success"] == 2
        assert result["synced"]["processed"] == 2

        # Проверяем вызовы
        mock_sync_account.assert_any_await("hash1", 1)
        mock_sync_account.assert_any_await("hash2", 2)

    @pytest.mark.asyncio
    async def test_sync_user_accounts(self, sync_repository):
        """sync_user_accounts вызывает _do_sync для каждого счёта"""
        user_id = 555
        hashes = ["acc1", "acc2"]

        with (
            patch.object(sync_repository, "get_user_account_hashes", new_callable=AsyncMock) as mock_get_hashes,
            patch.object(sync_repository, "_do_sync", new_callable=AsyncMock) as mock_do_sync,
            patch("app.repository.sync_repository.EventPublisher") as mock_publisher_cls,
        ):
            mock_get_hashes.return_value = hashes
            mock_do_sync.return_value = {"transactions": 3, "categories": 0, "mcc": 0, "merchants": 0, "banks": 0, "bank_accounts": 0}
            mock_publisher_cls.return_value.publish = AsyncMock()

            result = await sync_repository.sync_user_accounts(user_id)

        assert result["success"] == 2
        assert result["transactions"] == 6
        mock_get_hashes.assert_awaited_once_with(user_id)
        mock_do_sync.assert_any_await("acc1", user_id)
        mock_do_sync.assert_any_await("acc2", user_id)

    async def test_sync_user_accounts_publishes_single_event(self, sync_repository):
        """sync_user_accounts публикует ровно одно sync.completed со суммарной статистикой"""
        user_id = 42
        hashes = ["h1", "h2", "h3"]

        with (
            patch.object(sync_repository, "get_user_account_hashes", new_callable=AsyncMock) as mock_get_hashes,
            patch.object(sync_repository, "_do_sync", new_callable=AsyncMock) as mock_do_sync,
            patch("app.repository.sync_repository.EventPublisher") as mock_publisher_cls,
        ):
            mock_get_hashes.return_value = hashes
            mock_do_sync.return_value = {"transactions": 5, "categories": 0, "mcc": 0, "merchants": 0, "banks": 0, "bank_accounts": 0}
            mock_publisher = AsyncMock()
            mock_publisher.publish = AsyncMock()
            mock_publisher_cls.return_value = mock_publisher

            await sync_repository.sync_user_accounts(user_id)

        mock_publisher.publish.assert_awaited_once()
        event = mock_publisher.publish.await_args.args[0]
        assert event.event_type == "sync.completed"
        assert event.payload["user_id"] == user_id
        assert event.payload["new_transactions_count"] == 15  # 3 счёта × 5

    async def test_sync_user_accounts_no_event_when_all_failed(self, sync_repository):
        """sync.completed не публикуется если все счета упали с ошибкой"""
        user_id = 7
        hashes = ["bad1", "bad2"]

        with (
            patch.object(sync_repository, "get_user_account_hashes", new_callable=AsyncMock) as mock_get_hashes,
            patch.object(sync_repository, "_do_sync", new_callable=AsyncMock) as mock_do_sync,
            patch("app.repository.sync_repository.EventPublisher") as mock_publisher_cls,
        ):
            mock_get_hashes.return_value = hashes
            mock_do_sync.side_effect = Exception("pseudo_bank down")
            mock_publisher = AsyncMock()
            mock_publisher_cls.return_value = mock_publisher

            result = await sync_repository.sync_user_accounts(user_id)

        assert result["success"] == 0
        mock_publisher.publish.assert_not_awaited()
