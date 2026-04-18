# tests/unit/routers/test_pseudo_bank.py
from unittest.mock import MagicMock

import pytest
from app.models import Bank, Bank_Account, Category, Transaction


@pytest.mark.asyncio
class TestValidateAccount:
    async def test_validate_account_success(self, client):
        """Успешная валидация счета"""
        mock_account = MagicMock(spec=Bank_Account)
        mock_account.balance = 1000.50
        mock_account.currency = "RUB"
        client.mock_repo.get_account_bank.return_value = mock_account

        response = await client.post("/pseudo_bank/validate_account", json={"bank_account_hash": "valid_hash_123"})

        assert response.status_code == 200
        assert response.json() == {"balance": "1000.5", "currency": "RUB"}
        client.mock_repo.get_account_bank.assert_awaited_once_with("valid_hash_123")

    async def test_validate_account_not_found(self, client):
        """Счет не найден (404)"""
        client.mock_repo.get_account_bank.return_value = None

        response = await client.post("/pseudo_bank/validate_account", json={"bank_account_hash": "invalid_hash"})

        assert response.status_code == 404
        assert response.json()["detail"] == "Account not found"


@pytest.mark.asyncio
class TestExportData:
    async def test_export_success(self, client):
        """Успешный экспорт данных"""
        mock_acc = MagicMock(spec=Bank_Account)
        mock_acc.id = 1
        mock_acc.balance = 500

        mock_bank = MagicMock(spec=Bank)
        mock_bank.id = 1
        mock_bank.name = "TestBank"

        client.mock_repo.to_dict.side_effect = lambda obj: {
            "id": obj.id,
            "name": getattr(obj, "name", None),
            "balance": getattr(obj, "balance", None),
        }

        client.mock_repo.export_account_data.return_value = {
            "account": mock_acc,
            "bank": mock_bank,
            "transactions": [],
            "merchants": [],
            "categories": [],
            "mccs": [],
        }

        response = await client.get("/pseudo_bank/account/some_hash/export")

        assert response.status_code == 200
        data = response.json()

        assert data["bank"]["id"] == 1
        assert data["transactions"] == []

    async def test_export_not_found(self, client):
        """Экспорт для несуществующего счета"""
        client.mock_repo.export_account_data.return_value = None
        response = await client.get("/pseudo_bank/account/unknown/export")
        assert response.status_code == 404


@pytest.mark.asyncio
class TestCreateEndpoints:
    async def test_create_category(self, client):
        mock_obj = MagicMock(spec=Category, id=1, name="Food")
        client.mock_repo.create_category.return_value = mock_obj

        response = await client.post("/pseudo_bank/categories", json={"id": 1, "name": "Food"})
        assert response.status_code == 201
        # Проверяем, что был вызов репозитория
        assert client.mock_repo.create_category.await_count == 1

    async def test_create_bank(self, client):
        mock_obj = MagicMock(spec=Bank, id=10, name="Sber")
        client.mock_repo.create_bank.return_value = mock_obj
        response = await client.post("/pseudo_bank/banks", json={"id": 10, "name": "Sber"})
        assert response.status_code == 201

    async def test_create_transaction(self, client):
        mock_obj = MagicMock(spec=Transaction, id=100, amount=100.0)
        client.mock_repo.create_transaction.return_value = mock_obj
        payload = {"user_id": 1, "category_id": 1, "bank_account_id": 1, "amount": 100.0, "type": "income"}
        response = await client.post("/pseudo_bank/transactions", json=payload)
        assert response.status_code == 201


@pytest.mark.asyncio
class TestBulkEndpoints:
    async def test_bulk_create_categories(self, client):
        client.mock_repo.bulk_create_categories.return_value = {"created": 2}
        payload = [{"id": 1, "name": "A"}, {"id": 2, "name": "B"}]
        response = await client.post("/pseudo_bank/categories/bulk", json=payload)
        assert response.status_code == 201
        assert response.json() == {"created": 2}

    async def test_bulk_create_transactions(self, client):
        client.mock_repo.bulk_create_transactions.return_value = {"created": 3}
        payload = [
            {"user_id": 1, "category_id": 1, "bank_account_id": 1, "amount": "10.0", "type": "exp"},
            {"user_id": 1, "category_id": 1, "bank_account_id": 1, "amount": "20.0", "type": "exp"},
        ]
        response = await client.post("/pseudo_bank/transactions/bulk", json=payload)
        assert response.status_code == 201


@pytest.mark.asyncio
class TestValidation:
    async def test_create_category_validation_error(self, client):
        response = await client.post("/pseudo_bank/categories", json={"id": "not_an_int", "name": "Test"})
        assert response.status_code == 422

    async def test_validate_account_missing_field(self, client):
        response = await client.post("/pseudo_bank/validate_account", json={})
        assert response.status_code == 422
