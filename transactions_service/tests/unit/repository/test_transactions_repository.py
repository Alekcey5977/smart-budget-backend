from datetime import datetime
from unittest.mock import MagicMock

import pytest


class TestTransactionRepository:
    @pytest.mark.asyncio
    async def test_get_transactions_with_filters_default(
        self, transaction_repository, mock_db_session, sample_transaction
    ):
        """
        Тест получения транзакций с базовыми параметрами (только user_id).
        """
        # Настройка мока результата
        mock_scalars = MagicMock()
        mock_scalars.unique.return_value.all.return_value = [sample_transaction]

        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalars

        mock_db_session.execute.return_value = mock_result

        # Вызов метода
        user_id = 123
        result = await transaction_repository.get_transactions_with_filters(user_id=user_id)

        # Проверки
        mock_db_session.execute.assert_awaited_once()

        # Проверяем, что результат тот, который вернул мок
        assert len(result) == 1
        assert result[0].user_id == user_id
        assert result[0].category.name == "Products"

    @pytest.mark.asyncio
    async def test_get_transactions_with_filters_dates(self, transaction_repository, mock_db_session):
        """
        Тест фильтрации по датам. Проверяем, что фильтры применяются.
        """
        mock_scalars = MagicMock()
        mock_scalars.unique.return_value.all.return_value = []
        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalars
        mock_db_session.execute.return_value = mock_result

        start = datetime(2023, 1, 1)
        end = datetime(2023, 1, 31)

        await transaction_repository.get_transactions_with_filters(user_id=1, start_date=start, end_date=end)

        mock_db_session.execute.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_get_transactions_with_filters_amount_range(self, transaction_repository, mock_db_session):
        """
        Тест фильтрации по диапазону суммы.
        """
        mock_result = MagicMock()
        mock_result.scalars.return_value.unique.return_value.all.return_value = []
        mock_db_session.execute.return_value = mock_result

        await transaction_repository.get_transactions_with_filters(user_id=1, min_amount=10.0, max_amount=100.0)

        mock_db_session.execute.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_get_all_categories(self, transaction_repository, mock_db_session, sample_category):
        """
        Тест получения всех категорий.
        """
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = [sample_category]

        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalars

        mock_db_session.execute.return_value = mock_result

        categories = await transaction_repository.get_all_categories()

        assert len(categories) == 1
        assert categories[0].name == "Products"
        mock_db_session.execute.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_get_transaction_by_id_found(self, transaction_repository, mock_db_session, sample_transaction):
        """
        Тест получения транзакции по ID (найдено).
        """
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_transaction
        mock_db_session.execute.return_value = mock_result

        tx = await transaction_repository.get_transaction_by_id(transaction_id=str(sample_transaction.id), user_id=123)

        assert tx is not None
        assert tx.id == sample_transaction.id
        assert tx.merchant.name == "Supermarket"

    @pytest.mark.asyncio
    async def test_get_transaction_by_id_not_found(self, transaction_repository, mock_db_session):
        """
        Тест получения транзакции по ID (не найдено).
        """
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db_session.execute.return_value = mock_result

        tx = await transaction_repository.get_transaction_by_id(transaction_id="some-uuid", user_id=999)

        assert tx is None

    @pytest.mark.asyncio
    async def test_get_category_by_id(self, transaction_repository, mock_db_session, sample_category):
        """
        Тест получения категории по ID.
        """
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_category
        mock_db_session.execute.return_value = mock_result

        cat = await transaction_repository.get_category_by_id(1)

        assert cat.id == 1
        assert cat.name == "Products"
