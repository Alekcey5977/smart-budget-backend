import uuid
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from app.database import get_db
from app.dependencies import get_user_id_from_header
from app.models import Category, Merchant, Transaction
from app.routers import transactions
from fastapi import FastAPI, status
from fastapi.testclient import TestClient


class TestGetTransactions:
    """Тесты для получения транзакций"""

    @pytest.fixture
    def mock_db_session(self):
        """Фикстура для мокирования AsyncSession."""
        return AsyncMock()

    @pytest.fixture
    def client(self, mock_db_session):
        """
        Создает тестовый клиент с переопределенными зависимостями.
        Используем отдельный экземпляр FastAPI, чтобы избежать запуска life_span из main.py.
        """
        test_app = FastAPI()
        test_app.include_router(transactions.router)

        # Переопределяем зависимости
        test_app.dependency_overrides[get_db] = lambda: mock_db_session
        test_app.dependency_overrides[get_user_id_from_header] = lambda: 123

        return TestClient(test_app)

    @pytest.fixture
    def sample_transaction(self):
        """Создание примера транзакции с заполненными связями."""
        tx_id = uuid.uuid4()
        tx = Transaction(
            id=tx_id,
            user_id=123,
            category_id=1,
            bank_account_id=1,
            amount=100.50,
            created_at=datetime.now(),
            type="expense",
            description="Groceries",
            merchant_id=10
        )

        tx.category = Category(id=1, name="Products")
        tx.merchant = Merchant(id=10, name="Supermarket")
        return tx

    @pytest.mark.asyncio
    async def test_get_transactions_success(self, client, mock_db_session, sample_transaction):
        """Тест: успешное получение списка транзакций"""
        # Настраиваем мок репозитория
        mock_repo_instance = MagicMock()
        mock_repo_instance.get_transactions_with_filters = AsyncMock(
            return_value=[sample_transaction]
        )

        with patch('app.routers.transactions.TransactionRepository', return_value=mock_repo_instance):
            response = client.post(
                "/transactions/",
                json={"limit": 10, "offset": 0}
            )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data) == 1
        assert data[0]["user_id"] == 123
        assert data[0]["category_name"] == "Products"
        assert data[0]["merchant_name"] == "Supermarket"
        assert float(data[0]["amount"]) == 100.50

    @pytest.mark.asyncio
    async def test_get_transactions_empty_list(self, client, mock_db_session):
        """Тест: транзакции не найдены (пустой список)"""
        mock_repo_instance = MagicMock()
        mock_repo_instance.get_transactions_with_filters = AsyncMock(
            return_value=[])

        with patch('app.routers.transactions.TransactionRepository', return_value=mock_repo_instance):
            response = client.post(
                "/transactions/",
                json={"limit": 10, "offset": 0}
            )

        assert response.status_code == status.HTTP_200_OK
        assert response.json() == []

    @pytest.mark.asyncio
    async def test_get_transactions_filter_params_passed(self, client, mock_db_session):
        """Тест: параметры фильтрации передаются в репозиторий"""
        mock_repo_instance = MagicMock()
        mock_repo_instance.get_transactions_with_filters = AsyncMock(
            return_value=[])

        with patch('app.routers.transactions.TransactionRepository', return_value=mock_repo_instance):
            response = client.post(
                "/transactions/",
                json={
                    "limit": 5,
                    "transaction_type": "expense",
                    "min_amount": 50.0,
                    "category_ids": [1, 2]
                }
            )

        assert response.status_code == status.HTTP_200_OK

        # Проверяем, что метод репозитория был вызван с правильными аргументами
        called_kwargs = mock_repo_instance.get_transactions_with_filters.call_args.kwargs
        assert called_kwargs['limit'] == 5
        assert called_kwargs['transaction_type'] == "expense"
        assert called_kwargs['min_amount'] == 50.0
        assert called_kwargs['category_ids'] == [1, 2]

    @pytest.mark.asyncio
    async def test_get_transactions_internal_error(self, client, mock_db_session):
        """Тест: внутренняя ошибка сервера (Exception -> HTTP 500)"""
        mock_repo_instance = MagicMock()
        mock_repo_instance.get_transactions_with_filters = AsyncMock(
            side_effect=Exception("DB connection lost")
        )

        with patch('app.routers.transactions.TransactionRepository', return_value=mock_repo_instance):
            response = client.post(
                "/transactions/",
                json={"limit": 10}
            )

        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert "Internal server error" in response.json()["detail"]


class TestGetCategories:
    """Тесты для получения категорий"""

    @pytest.fixture
    def mock_db_session(self):
        return AsyncMock()

    @pytest.fixture
    def client(self, mock_db_session):
        test_app = FastAPI()
        test_app.include_router(transactions.router)
        test_app.dependency_overrides[get_db] = lambda: mock_db_session
        return TestClient(test_app)

    @pytest.mark.asyncio
    async def test_get_categories_success(self, client, mock_db_session):
        """Тест: успешное получение категорий"""
        mock_category = Category(id=1, name="Food")

        mock_repo_instance = MagicMock()
        mock_repo_instance.get_all_categories = AsyncMock(
            return_value=[mock_category])

        with patch('app.routers.transactions.TransactionRepository', return_value=mock_repo_instance):
            response = client.get("/transactions/categories")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data) == 1
        assert data[0]["name"] == "Food"

    @pytest.mark.asyncio
    async def test_get_categories_empty(self, client, mock_db_session):
        """Тест: список категорий пуст"""
        mock_repo_instance = MagicMock()
        mock_repo_instance.get_all_categories = AsyncMock(return_value=[])

        with patch('app.routers.transactions.TransactionRepository', return_value=mock_repo_instance):
            response = client.get("/transactions/categories")

        assert response.status_code == status.HTTP_200_OK
        assert response.json() == []


class TestValidation:
    """Тесты валидации данных запроса"""

    @pytest.fixture
    def mock_db_session(self):
        return AsyncMock()

    @pytest.fixture
    def client(self, mock_db_session):
        test_app = FastAPI()
        test_app.include_router(transactions.router)
        test_app.dependency_overrides[get_db] = lambda: mock_db_session
        return TestClient(test_app)

    @pytest.mark.asyncio
    async def test_invalid_limit_value(self, client):
        """Тест: некорректное значение limit (отрицательное)"""
        response = client.post(
            "/transactions/",
            json={"limit": -5}
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT

    @pytest.mark.asyncio
    async def test_invalid_transaction_type(self, client):
        """Тест: некорректный тип транзакции"""
        response = client.post(
            "/transactions/",
            json={"limit": 10, "transaction_type": "invalid_type"}
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
