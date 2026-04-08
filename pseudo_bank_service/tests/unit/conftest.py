import pathlib
import sys
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

SERVICE_ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
if str(SERVICE_ROOT) not in sys.path:
    sys.path.insert(0, str(SERVICE_ROOT))

from app.main import app  # noqa: E402
from app.repository.transactions_repository import TransactionRepository  # noqa: E402
from app.schemas import BankAccountCreate, BankCreate, CategoryCreate, TransactionCreate  # noqa: E402

# --- Фикстуры данных ---


@pytest.fixture
def category_data():
    return {"id": 1, "name": "Продукты"}


@pytest.fixture
def mcc_data(category_data):
    return {"mcc": 5411, "name": "Супермаркеты", "category_id": category_data["id"]}


@pytest.fixture
def merchant_data(category_data):
    return {"id": 100, "name": "ООО Магазин", "inn": "7701234567", "category_id": category_data["id"]}


@pytest.fixture
def bank_data():
    return {"id": 10, "name": "ТестБанк"}


@pytest.fixture
def bank_account_data(bank_data):
    return {
        "user_id": 1,
        "bank_account_hash": "a" * 64,
        "bank_account_name": "Мой счет",
        "bank_id": bank_data["id"],
    }


@pytest.fixture
def transaction_data():
    return {
        "user_id": 1,
        "category_id": 1,
        "bank_account_id": 1,
        "amount": "100.50",
        "type": "expense",
        "description": "Покупки",
        "merchant_id": 100,
        "created_at": datetime.now(),
    }


# --- Фикстуры моков ---


@pytest.fixture
def mock_db_session():
    session = AsyncMock()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()
    session.add = MagicMock()
    session.execute = AsyncMock()
    return session


@pytest.fixture
def transaction_repository(mock_db_session):
    return TransactionRepository(db=mock_db_session)


# --- Фикстуры схем ---


@pytest.fixture
def sample_category_create():
    return CategoryCreate(id=1, name="Food")


@pytest.fixture
def sample_bank_create():
    return BankCreate(id=1, name="Test Bank")


@pytest.fixture
def sample_bank_account_create():
    return BankAccountCreate(user_id=1, bank_account_hash="hash123", bank_account_name="Main", bank_id=1)


@pytest.fixture
def sample_transaction_create():
    return TransactionCreate(user_id=1, category_id=1, bank_account_id=1, amount=100.00, type="expense")


# --- Фикстуры для API тестов ---


@pytest.fixture
def mock_transaction_repo():
    repo = MagicMock(spec=TransactionRepository)
    repo.get_account_bank = AsyncMock()
    repo.export_account_data = AsyncMock()
    repo.create_category = AsyncMock()
    repo.create_bank = AsyncMock()
    repo.create_bank_account = AsyncMock()
    repo.create_transaction = AsyncMock()
    repo.create_merchant = AsyncMock()
    repo.create_mcc_category = AsyncMock()
    repo.bulk_create_categories = AsyncMock(return_value={"created": 0})
    repo.bulk_create_banks = AsyncMock(return_value={"created": 0})
    repo.bulk_create_bank_accounts = AsyncMock(return_value={"created": 0})
    repo.bulk_create_transactions = AsyncMock(return_value={"created": 0})
    repo.bulk_create_merchants = AsyncMock(return_value={"created": 0})
    repo.bulk_create_mcc_categories = AsyncMock(return_value={"created": 0})

    def default_to_dict(obj):
        if hasattr(obj, "__table__"):
            return {c.name: getattr(obj, c.name) for c in obj.__table__.columns}
        return obj

    repo.to_dict = MagicMock(side_effect=default_to_dict)
    return repo


@pytest_asyncio.fixture
async def client(mock_transaction_repo):
    from app.routers.pseudo_bank import get_transactions_repository

    app.dependency_overrides[get_transactions_repository] = lambda: mock_transaction_repo

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        ac.mock_repo = mock_transaction_repo
        yield ac

    app.dependency_overrides.clear()
