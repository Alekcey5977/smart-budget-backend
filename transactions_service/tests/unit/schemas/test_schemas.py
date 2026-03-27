import uuid
from datetime import datetime

import pytest
from app.models import Category, Merchant
from app.schemas import (
    CategoryResponse,
    MerchantResponse,
    TransactionFilterRequest,
    TransactionResponse,
)
from pydantic import ValidationError


class TestTransactionFilterRequest:
    """Тесты для схемы фильтрации транзакций"""

    def test_valid_data(self):
        """Успешное создание с валидными данными"""
        data = {
            "transaction_type": "income",
            "category_ids": [1, 2],
            "min_amount": 10.5,
            "max_amount": 100.0,
            "limit": 50,
            "offset": 0
        }
        schema = TransactionFilterRequest(**data)
        assert schema.transaction_type == "income"
        assert schema.category_ids == [1, 2]
        assert schema.limit == 50

    def test_required_fields_validation(self):
        """Проверка того, что limit обязателен"""
        with pytest.raises(ValidationError) as exc_info:
            TransactionFilterRequest()

        errors = exc_info.value.errors()
        assert any(error['loc'][0] == 'limit' for error in errors)

    def test_invalid_transaction_type(self):
        """Неверный тип транзакции"""
        data = {
            "limit": 10,
            "transaction_type": "invalid_type"
        }
        with pytest.raises(ValidationError) as exc_info:
            TransactionFilterRequest(**data)

        assert 'Type must be "income" or "expense"' in str(exc_info.value)

    def test_invalid_limit_range(self):
        """Лимит вне допустимого диапазона"""
        data = {"limit": 0}
        with pytest.raises(ValidationError):
            TransactionFilterRequest(**data)

        data = {"limit": 1001}
        with pytest.raises(ValidationError):
            TransactionFilterRequest(**data)

    def test_negative_amount(self):
        """Отрицательная сумма (min_amount ge=0)"""
        data = {"limit": 10, "min_amount": -5.0}
        with pytest.raises(ValidationError):
            TransactionFilterRequest(**data)


class TestTransactionResponse:
    """Тесты для схемы ответа транзакции"""

    def test_from_dict_with_manual_mapping(self):
        """
        Проверка создания схемы из словаря.
        Имитирует ситуацию, где Service слой вручную достал имена из связей.
        """
        tx_id = uuid.uuid4()
        now = datetime.now()

        response_data = {
            "id": tx_id,
            "user_id": 1,
            "bank_account_id": 1,
            "category_id": 1,
            "amount": 100.0,
            "created_at": now,
            "type": "expense",
            "description": "Test",
            "merchant_id": None,
            "category_name": "Food",
            "merchant_name": None
        }

        response = TransactionResponse.model_validate(response_data)

        assert response.id == tx_id
        assert response.category_name == "Food"
        assert response.type == "expense"

    def test_manual_creation(self):
        """Ручное создание схемы"""
        tx_id = uuid.uuid4()
        now = datetime.now()

        data = {
            "id": tx_id,
            "user_id": 1,
            "bank_account_id": 1,
            "category_id": 1,
            "amount": 500.0,
            "created_at": now,
            "type": "income",
            "category_name": "Salary"
        }

        response = TransactionResponse(**data)
        assert response.amount == 500.0
        assert response.category_name == "Salary"


class TestCategoryResponse:
    """Тесты для схемы ответа категории"""

    def test_from_orm(self):
        """Проверка маппинга из ORM модели категории"""
        # Создаем реальный объект ORM модели
        category_orm = Category(id=5, name="Transport")

        # Проверяем, что Pydantic может считать данные прямо из объекта
        response = CategoryResponse.model_validate(category_orm)

        assert response.id == 5
        assert response.name == "Transport"


class TestMerchantResponse:
    """Тесты для схемы ответа мерчанта"""

    def test_from_orm(self):
        """Проверка маппинга из ORM модели"""
        merch = Merchant(id=10, name="Shop", inn="000", category_id=1)

        response = MerchantResponse.model_validate(merch)

        assert response.id == 10
        assert response.name == "Shop"
        assert response.mcc_id is None
