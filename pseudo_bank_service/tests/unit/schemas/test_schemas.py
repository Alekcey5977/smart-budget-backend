from decimal import Decimal

import pytest
from app.schemas import (
    BankAccountCreate,
    BankCreate,
    CategoryCreate,
    MCCCategoryCreate,
    MerchantCreate,
    TransactionCreate,
    Validate_Bank_Account,
)
from pydantic import ValidationError


class TestValidateBankAccount:
    """Тесты для простой схемы валидации хэша"""

    def test_valid_hash(self):
        schema = Validate_Bank_Account(bank_account_hash="some_hash_string")
        assert schema.bank_account_hash == "some_hash_string"

    def test_missing_hash(self):
        with pytest.raises(ValidationError) as exc:
            Validate_Bank_Account()
        assert "bank_account_hash" in str(exc.value)


class TestCategorySchemas:
    """Тесты CategoryCreate"""

    def test_create_success(self, category_data):
        category = CategoryCreate(**category_data)
        assert category.id == 1
        assert category.name == "Продукты"

    def test_name_max_length(self, category_data):
        # Генерируем строку длиной 101 символ
        long_name = "a" * 101
        data = {**category_data, "name": long_name}

        with pytest.raises(ValidationError):
            CategoryCreate(**data)


class TestMCCCategorySchemas:
    """Тесты MCCCategoryCreate"""

    def test_create_success(self, mcc_data):
        mcc = MCCCategoryCreate(**mcc_data)
        assert mcc.mcc == 5411
        assert mcc.name == "Супермаркеты"

    def test_name_validation(self, mcc_data):
        data = {**mcc_data, "name": "b" * 101}  # Слишком длинное имя
        with pytest.raises(ValidationError):
            MCCCategoryCreate(**data)


class TestMerchantSchemas:
    """Тесты MerchantCreate"""

    def test_create_success(self, merchant_data):
        merchant = MerchantCreate(**merchant_data)
        assert merchant.inn == "7701234567"

    def test_inn_max_length(self, merchant_data):
        data = {**merchant_data, "inn": "1" * 101}  # Слишком длинный ИНН
        with pytest.raises(ValidationError):
            MerchantCreate(**data)


class TestBankSchemas:
    """Тесты BankCreate"""

    def test_create_success(self, bank_data):
        bank = BankCreate(**bank_data)
        assert bank.name == "ТестБанк"

    def test_name_max_length(self, bank_data):
        data = {**bank_data, "name": "b" * 51}  # Max 50
        with pytest.raises(ValidationError):
            BankCreate(**data)


class TestBankAccountSchemas:
    """Тесты BankAccountCreate"""

    def test_create_success_defaults(self, bank_account_data):
        """Проверка создания и дефолтных значений"""
        account = BankAccountCreate(**bank_account_data)

        assert account.user_id == 1
        # Проверяем дефолты
        assert account.currency == "RUB"
        assert account.balance == Decimal("0.00")
        # Проверка хэша
        assert len(account.bank_account_hash) == 64

    def test_hash_max_length(self, bank_account_data):
        """Хэш не может быть длиннее 64 символов"""
        data = {**bank_account_data, "bank_account_hash": "a" * 65}
        with pytest.raises(ValidationError):
            BankAccountCreate(**data)

    def test_custom_balance_and_currency(self, bank_account_data):
        """Проверка явной передачи баланса и валюты"""
        data = {**bank_account_data, "currency": "USD", "balance": Decimal("999.99")}
        account = BankAccountCreate(**data)
        assert account.currency == "USD"
        assert account.balance == Decimal("999.99")


class TestTransactionSchemas:
    """Тесты TransactionCreate"""

    def test_create_success(self, transaction_data):
        """Успешное создание, проверка приведения типов"""
        tx = TransactionCreate(**transaction_data)

        # Проверяем, что строка суммы стала Decimal
        assert tx.amount == Decimal("100.50")
        assert isinstance(tx.amount, Decimal)
        assert tx.type == "expense"

    def test_optional_fields_none(self, transaction_data):
        """Опциональные поля могут быть None"""
        data = {"user_id": 1, "category_id": 1, "bank_account_id": 1, "amount": 10, "type": "income"}
        tx = TransactionCreate(**data)

        assert tx.description is None
        assert tx.merchant_id is None
        assert tx.created_at is None

    def test_type_max_length(self, transaction_data):
        """Длина типа транзакции ограничена 30 символами"""
        data = {**transaction_data, "type": "a" * 31}
        with pytest.raises(ValidationError):
            TransactionCreate(**data)

    def test_description_max_length(self, transaction_data):
        """Длина описания ограничена 200 символами"""
        data = {**transaction_data, "description": "d" * 201}
        with pytest.raises(ValidationError):
            TransactionCreate(**data)
