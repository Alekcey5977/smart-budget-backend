# tests/test_repository.py
from unittest.mock import MagicMock

import pytest

# Импорты вашего приложения
from app.models import Bank, Bank_Account, Category, Merchant, Transaction
from app.schemas import BankAccountCreate, CategoryCreate, TransactionCreate


class TestTransactionRepositoryCRUD:
    """Тесты для простых методов создания (Create)"""

    @pytest.mark.asyncio
    async def test_create_category_success(self, transaction_repository, mock_db_session, sample_category_create):
        """Тест успешного создания категории"""

        await transaction_repository.create_category(sample_category_create)

        # Проверяем, что add был вызван
        mock_db_session.add.assert_called_once()

        # Проверяем аргумент, переданный в add
        added_obj = mock_db_session.add.call_args[0][0]
        assert isinstance(added_obj, Category)
        assert added_obj.name == "Food"

        # Проверяем commit и refresh
        mock_db_session.commit.assert_awaited_once()
        mock_db_session.refresh.assert_awaited_once_with(added_obj)

    @pytest.mark.asyncio
    async def test_create_bank_account_defaults(self, transaction_repository, mock_db_session):
        """Проверка, что схема корректно передается в модель"""
        acc_data = BankAccountCreate(user_id=1, bank_account_hash="h1", bank_account_name="n1", bank_id=1)

        await transaction_repository.create_bank_account(acc_data)

        mock_db_session.add.assert_called_once()
        added_obj = mock_db_session.add.call_args[0][0]
        assert isinstance(added_obj, Bank_Account)
        # Проверяем дефолтное значение из схемы
        assert added_obj.currency == "RUB"


class TestTransactionRepositoryExport:
    """Тесты для сложного метода export_account_data"""

    @pytest.mark.asyncio
    async def test_export_account_not_found(self, transaction_repository, mock_db_session):
        """Если счет не найден, должен вернуть None"""
        # Мокаем результат execute для получения счета
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db_session.execute.return_value = mock_result

        result = await transaction_repository.export_account_data("non_existent_hash")

        assert result is None
        # Проверяем, что select был вызван для bank_accounts
        call_args = mock_db_session.execute.call_args[0][0]

        # Проверяем наличие "FROM bank_accounts"
        compiled_query = str(call_args.compile())
        assert "FROM bank_accounts" in compiled_query

    @pytest.mark.asyncio
    async def test_export_account_success(self, transaction_repository, mock_db_session):
        """Успешный экспорт данных"""
        # 1. Подготовка моков (ORM объектов)
        mock_account = MagicMock(spec=Bank_Account)
        mock_account.id = 1
        mock_account.bank_id = 10

        mock_bank = MagicMock(spec=Bank)
        mock_bank.id = 10

        # Мок транзакции
        mock_transaction = MagicMock(spec=Transaction)
        mock_transaction.category_id = 5
        mock_transaction.merchant_id = 20
        mock_transaction.merchant = MagicMock(spec=Merchant)

        # !!! ИСПРАВЛЕНИЕ: Устанавливаем category в None, чтобы код попытался загрузить её из БД !!!
        # Это нужно, чтобы убедиться, что запрос категорий действительно выполняется.
        mock_transaction.category = None

        # 2. Настройка цепочки вызовов execute
        # Порядок вызовов в export_account_data:
        # 1. get_account (Bank_Account)
        # 2. get Bank
        # 3. get Transactions
        # 4. (if merchant_ids) get Merchant categories -> В коде используется для обновления category_ids
        # 5. get Categories (так как у mock_transaction.category = None)
        # 6. get MCCs

        # result для Account
        res_account = MagicMock()
        res_account.scalar_one_or_none.return_value = mock_account

        # result для Bank
        res_bank = MagicMock()
        res_bank.scalar_one.return_value = mock_bank

        # result для Transactions
        res_trans = MagicMock()
        res_trans.scalars.return_value.all.return_value = [mock_transaction]

        # result для Merchant Cats (возвращает category_id мерчанта)
        res_merch_cat = MagicMock()
        res_merch_cat.fetchall.return_value = [(99,)]  # (category_id,)

        # result для Categories (возвращает категорию, которой не было в транзакции)
        mock_db_category = MagicMock(spec=Category)
        mock_db_category.id = 5
        res_cats = MagicMock()
        res_cats.scalars.return_value.all.return_value = [mock_db_category]

        # result для MCC
        res_mccs = MagicMock()
        res_mccs.scalars.return_value.all.return_value = []

        # Настраиваем side_effect для session.execute
        mock_db_session.execute.side_effect = [
            res_account,  # 1. get account
            res_bank,  # 2. get bank
            res_trans,  # 3. get transactions
            res_merch_cat,  # 4. get merchant category ids (update logic)
            res_cats,  # 5. get categories (так как в trans их не было)
            res_mccs,  # 6. get mccs
        ]

        # 3. Вызов метода
        result = await transaction_repository.export_account_data("hash123")

        # 4. Проверки (Asserts)
        assert result is not None
        assert result["account"] == mock_account
        assert result["bank"] == mock_bank
        assert result["transactions"] == [mock_transaction]
        # Проверяем, что категория подтянулась
        assert result["categories"][0] == mock_db_category

        # Проверяем количество вызовов (с учетом измененной логики мока)
        assert mock_db_session.execute.call_count == 6


class TestTransactionRepositoryBulk:
    """Тесты для массового создания (Bulk Create)"""

    @pytest.mark.asyncio
    async def test_bulk_create_categories(self, transaction_repository, mock_db_session):
        """Тест массовой вставки категорий с on_conflict_do_nothing"""
        categories = [CategoryCreate(id=1, name="A"), CategoryCreate(id=2, name="B")]

        result = await transaction_repository.bulk_create_categories(categories)

        assert result["created"] == 2

        mock_db_session.execute.assert_awaited_once()
        mock_db_session.commit.assert_awaited_once()

        stmt = mock_db_session.execute.call_args[0][0]
        assert "INSERT" in str(stmt.compile()) or "insert" in str(type(stmt)).lower()

    @pytest.mark.asyncio
    async def test_bulk_create_transactions(self, transaction_repository, mock_db_session):
        """Тест массовой вставки транзакций (через цикл add)"""
        transactions = [
            TransactionCreate(user_id=1, category_id=1, bank_account_id=1, amount=10, type="exp"),
            TransactionCreate(user_id=1, category_id=1, bank_account_id=1, amount=20, type="exp"),
        ]

        result = await transaction_repository.bulk_create_transactions(transactions)

        assert result["created"] == 2
        assert mock_db_session.add.call_count == 2
        mock_db_session.commit.assert_awaited_once()
