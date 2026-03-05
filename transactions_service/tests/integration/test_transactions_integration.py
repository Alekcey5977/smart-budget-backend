import uuid
from datetime import datetime

import pytest
from app.models import Bank, Bank_Account, Category, Merchant, Transaction
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession


@pytest.mark.asyncio
async def test_get_categories_empty(client: AsyncClient):
    """Тест: получение пустого списка категорий"""
    response = await client.get("/transactions/categories")
    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.asyncio
async def test_get_categories_success(client: AsyncClient, db_session: AsyncSession):
    """Тест: получение списка категорий из реальной БД"""
    # Arrange: добавляем данные напрямую в сессию
    cat1 = Category(id=1, name="Food")
    cat2 = Category(id=2, name="Transport")
    db_session.add_all([cat1, cat2])
    # Отправляем в БД, но не коммитим
    await db_session.flush()

    # Act: вызываем реальный эндпоинт
    response = await client.get("/transactions/categories")

    # Assert
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    assert data[0]["name"] == "Food"


@pytest.mark.asyncio
async def test_get_transactions_with_filters(client: AsyncClient, db_session: AsyncSession):
    """Тест: фильтрация транзакций (проверка связей и логики репозитория)"""
    user_id = 123

    # Arrange: создаем полную структуру данных
    bank = Bank(id=1, name="Test Bank")
    category = Category(id=10, name="Groceries")
    merchant = Merchant(id=5, name="Supermarket", inn="123", category_id=10)
    account = Bank_Account(
        id=1,
        user_id=user_id,
        bank_account_hash="hash_123",
        bank_account_name="Main",
        bank_id=1,
        currency="RUB",
        balance=1000.00
    )

    tx1 = Transaction(
        id=uuid.uuid4(),
        user_id=user_id,
        category_id=10,
        bank_account_id=1,
        merchant_id=5,
        amount=500.00,
        type="expense",
        created_at=datetime(2023, 1, 1, 12, 0, 0)
    )

    tx_other = Transaction(
        id=uuid.uuid4(),
        user_id=999,
        category_id=10,
        bank_account_id=1,
        amount=100.00,
        type="expense",
        created_at=datetime(2023, 1, 1, 13, 0, 0)
    )

    db_session.add_all([bank, category, merchant, account, tx1, tx_other])
    await db_session.flush()

    # Act: запрос с фильтром
    response = await client.post(
        "/transactions/",
        json={
            "limit": 10,
            "offset": 0,
            "min_amount": 100,
            "max_amount": 600
        }
    )

    # Assert
    assert response.status_code == 200
    data = response.json()

    # Должна вернуться только одна транзакция
    assert len(data) == 1

    tx_data = data[0]
    assert tx_data["amount"] == 500.00
    assert tx_data["category_name"] == "Groceries"
    assert tx_data["merchant_name"] == "Supermarket"
    assert tx_data["user_id"] == user_id


@pytest.mark.asyncio
async def test_sync_repository_integration(client: AsyncClient, db_session: AsyncSession):
    """Тест репозитория синхронизации (запись в БД)"""
    from unittest.mock import AsyncMock, MagicMock, patch

    from app.repository.sync_repository import SyncRepository

    repo = SyncRepository(db_session)

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "bank": {"id": 99, "name": "Synced Bank"},
        "bank_account": {
            "bank_account_hash": "sync_hash_1",
            "user_id": 999,
            "bank_account_name": "Sync Acc",
            "bank_id": 99,
            "currency": "USD",
            "balance": 100,
            "created_at": "2023-01-01T00:00:00Z"
        },
        "categories": [{"id": 50, "name": "Synced Cat"}],
        "mcc_categories": [],
        "merchants": [],
        "transactions": []
    }

    mock_client_instance = AsyncMock()
    mock_client_instance.get.return_value = mock_response

    with patch("app.repository.sync_repository.httpx.AsyncClient") as mock_http:
        mock_http.return_value.__aenter__.return_value = mock_client_instance

        # Выполняем синхронизацию
        stats = await repo.sync_by_account("sync_hash_1", user_id=123)

    # Проверяем, что данные записались в БД
    assert stats["categories"] == 1

    # Проверяем прямым запросом
    from sqlalchemy import select
    result = await db_session.execute(select(Category).where(Category.id == 50))
    cat = result.scalar_one_or_none()

    assert cat is not None
    assert cat.name == "Synced Cat"
