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
        assert data[0]["bank_account_id"] == 1
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


class TestUpdateTransactionCategory:
    """Тесты для изменения категории транзакции"""

    @pytest.fixture
    def mock_db_session(self):
        return AsyncMock()

    @pytest.fixture
    def client(self, mock_db_session):
        test_app = FastAPI()
        test_app.include_router(transactions.router)
        test_app.dependency_overrides[get_db] = lambda: mock_db_session
        test_app.dependency_overrides[get_user_id_from_header] = lambda: 123
        return TestClient(test_app)

    @pytest.fixture
    def sample_transaction(self):
        tx_id = uuid.uuid4()
        tx = Transaction(
            id=tx_id, user_id=123, category_id=2,
            bank_account_id=1, amount=100.50,
            created_at=datetime.now(), type="expense"
        )
        tx.category = Category(id=2, name="Transport")
        tx.merchant = None
        return tx

    @pytest.mark.asyncio
    async def test_update_category_success(self, client, mock_db_session, sample_transaction):
        """Тест: успешное изменение категории"""
        mock_repo = MagicMock()
        mock_repo.get_category_by_id = AsyncMock(return_value=Category(id=2, name="Transport"))
        mock_repo.update_transaction_category = AsyncMock(return_value=sample_transaction)

        with patch('app.routers.transactions.TransactionRepository', return_value=mock_repo):
            response = client.patch(
                f"/transactions/{sample_transaction.id}/category",
                json={"category_id": 2}
            )

        assert response.status_code == 200
        data = response.json()
        assert data["category_id"] == 2
        assert data["category_name"] == "Transport"

    @pytest.mark.asyncio
    async def test_update_category_transaction_not_found(self, client, mock_db_session):
        """Тест: транзакция не найдена → 404"""
        mock_repo = MagicMock()
        mock_repo.get_category_by_id = AsyncMock(return_value=Category(id=1, name="Food"))
        mock_repo.update_transaction_category = AsyncMock(return_value=None)

        with patch('app.routers.transactions.TransactionRepository', return_value=mock_repo):
            response = client.patch(
                f"/transactions/{uuid.uuid4()}/category",
                json={"category_id": 1}
            )

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_update_category_category_not_found(self, client, mock_db_session):
        """Тест: категория не существует → 404"""
        mock_repo = MagicMock()
        mock_repo.get_category_by_id = AsyncMock(return_value=None)

        with patch('app.routers.transactions.TransactionRepository', return_value=mock_repo):
            response = client.patch(
                f"/transactions/{uuid.uuid4()}/category",
                json={"category_id": 999}
            )

        assert response.status_code == 404
        mock_repo.update_transaction_category.assert_not_called()

    @pytest.mark.asyncio
    async def test_update_category_invalid_category_id(self, client, mock_db_session):
        """Тест: category_id <= 0 → 422"""
        response = client.patch(
            f"/transactions/{uuid.uuid4()}/category",
            json={"category_id": 0}
        )
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_update_category_missing_body(self, client, mock_db_session):
        """Тест: отсутствует category_id → 422"""
        response = client.patch(
            f"/transactions/{uuid.uuid4()}/category",
            json={}
        )
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_update_category_internal_error(self, client, mock_db_session):
        """Тест: неожиданная ошибка → 500"""
        mock_repo = MagicMock()
        mock_repo.get_category_by_id = AsyncMock(side_effect=Exception("DB error"))

        with patch('app.routers.transactions.TransactionRepository', return_value=mock_repo):
            response = client.patch(
                f"/transactions/{uuid.uuid4()}/category",
                json={"category_id": 1}
            )

        assert response.status_code == 500
        assert "Internal server error" in response.json()["detail"]


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
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    @pytest.mark.asyncio
    async def test_invalid_transaction_type(self, client):
        """Тест: некорректный тип транзакции"""
        response = client.post(
            "/transactions/",
            json={"limit": 10, "transaction_type": "invalid_type"}
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


class TestGetTransactionById:
    """Тесты для получения транзакции по ID"""

    @pytest.fixture
    def mock_db_session(self):
        return AsyncMock()

    @pytest.fixture
    def client(self, mock_db_session):
        test_app = FastAPI()
        test_app.include_router(transactions.router)
        test_app.dependency_overrides[get_db] = lambda: mock_db_session
        test_app.dependency_overrides[get_user_id_from_header] = lambda: 123
        return TestClient(test_app)

    @pytest.fixture
    def sample_transaction(self):
        tx_id = uuid.uuid4()
        tx = Transaction(
            id=tx_id,
            user_id=123,
            category_id=1,
            bank_account_id=1,
            amount=300.00,
            created_at=datetime.now(),
            type="expense",
            description="Test",
            merchant_id=None
        )
        tx.category = Category(id=1, name="Food")
        tx.merchant = None
        return tx

    @pytest.mark.asyncio
    async def test_get_transaction_by_id_success(self, client, mock_db_session, sample_transaction):
        """Тест: успешное получение транзакции"""
        mock_repo_instance = MagicMock()
        mock_repo_instance.get_transaction_by_id = AsyncMock(return_value=sample_transaction)

        with patch('app.routers.transactions.TransactionRepository', return_value=mock_repo_instance):
            response = client.get(f"/transactions/{sample_transaction.id}")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert str(data["id"]) == str(sample_transaction.id)
        assert data["user_id"] == 123
        assert data["bank_account_id"] == 1
        assert data["category_name"] == "Food"

    @pytest.mark.asyncio
    async def test_get_transaction_by_id_not_found(self, client, mock_db_session):
        """Тест: транзакция не найдена → 404"""
        mock_repo_instance = MagicMock()
        mock_repo_instance.get_transaction_by_id = AsyncMock(return_value=None)

        with patch('app.routers.transactions.TransactionRepository', return_value=mock_repo_instance):
            response = client.get(f"/transactions/{uuid.uuid4()}")

        assert response.status_code == status.HTTP_404_NOT_FOUND

    @pytest.mark.asyncio
    async def test_get_transaction_missing_user_id_header(self, mock_db_session):
        """Тест: отсутствует X-User-ID → 422"""
        test_app = FastAPI()
        test_app.include_router(transactions.router)
        test_app.dependency_overrides[get_db] = lambda: mock_db_session
        # Не переопределяем get_user_id_from_header — должна вернуть 422
        client_no_header = TestClient(test_app, raise_server_exceptions=False)

        response = client_no_header.get(f"/transactions/{uuid.uuid4()}")
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


class TestGetCategoryById:
    """Тесты для получения категории по ID"""

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
    async def test_get_category_by_id_success(self, client, mock_db_session):
        """Тест: успешное получение категории"""
        mock_category = Category(id=5, name="Transport")
        mock_repo_instance = MagicMock()
        mock_repo_instance.get_category_by_id = AsyncMock(return_value=mock_category)

        with patch('app.routers.transactions.TransactionRepository', return_value=mock_repo_instance):
            response = client.get("/transactions/categories/5")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["id"] == 5
        assert data["name"] == "Transport"

    @pytest.mark.asyncio
    async def test_get_category_by_id_not_found(self, client, mock_db_session):
        """Тест: категория не найдена → 404"""
        mock_repo_instance = MagicMock()
        mock_repo_instance.get_category_by_id = AsyncMock(return_value=None)

        with patch('app.routers.transactions.TransactionRepository', return_value=mock_repo_instance):
            response = client.get("/transactions/categories/9999")

        assert response.status_code == status.HTTP_404_NOT_FOUND
