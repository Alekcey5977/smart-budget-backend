import pathlib
import sys
from datetime import datetime
from unittest.mock import AsyncMock

SERVICE_ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
if str(SERVICE_ROOT) not in sys.path:
    sys.path.insert(0, str(SERVICE_ROOT))

from uuid import uuid4

import pytest
from app.models import Category, Merchant, Transaction


@pytest.fixture
def mock_db_session():
    """
    Фикстура для мокирования AsyncSession.
    Имитирует поведение базы данных без реального подключения.
    """
    session = AsyncMock()
    return session


@pytest.fixture
def transaction_repository(mock_db_session):
    """
    Фикстура для создания экземпляра репозитория с замоканной сессией.
    """
    from app.repository.transactions_repository import TransactionRepository
    return TransactionRepository(db=mock_db_session)


@pytest.fixture
def sample_category():
    """Создание примера категории для тестов."""
    cat = Category(id=1, name="Products")
    return cat


@pytest.fixture
def sample_merchant():
    """Создание примера мерчанта для тестов."""
    merch = Merchant(id=10, name="Supermarket",
                     inn="1234567890", category_id=1)
    return merch


@pytest.fixture
def sample_transaction(sample_category, sample_merchant):
    """Создание примера транзакции."""
    tx = Transaction(
        id=uuid4(),
        user_id=123,
        category_id=1,
        bank_account_id=1,
        amount=100.50,
        type="expense",
        description="Groceries",
        created_at=datetime.now(),
        merchant_id=10
    )
    tx.category = sample_category
    tx.merchant = sample_merchant
    return tx
