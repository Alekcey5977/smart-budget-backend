from unittest.mock import MagicMock

import pytest
from app.routers.bank_account import get_current_user
from app.routers.users import get_bank_account_repository
from fastapi import status
from httpx import AsyncClient


@pytest.mark.asyncio
class TestBankAccountEndpoints:
    """
    Unit-тесты для эндпоинтов банковских счетов.
    """

    async def test_add_bank_account_success(
        self,
        client: AsyncClient,
        app,
        mock_bank_account_repo
    ):
        """
        Тест успешного создания банковского счета.
        """
        # 1. Подготовка мока авторизации
        mock_user = MagicMock()
        mock_user.id = 1

        async def override_get_current_user():
            return mock_user

        # 2. Подготовка мока репозитория
        new_account_mock = MagicMock()
        new_account_mock.bank_account_id = 123
        new_account_mock.bank_account_name = "My Salary"
        new_account_mock.currency = "RUB"
        new_account_mock.balance = "5000.00"

        bank_mock = MagicMock()
        bank_mock.name = "Тинькофф"
        new_account_mock.bank = bank_mock

        mock_bank_account_repo.create.return_value = (
            new_account_mock, "hash_123")

        # Переопределяем зависимости
        app.dependency_overrides[get_current_user] = override_get_current_user
        app.dependency_overrides[get_bank_account_repository] = lambda: mock_bank_account_repo

        # 3. Выполнение запроса
        payload = {
            "bank_account_number": "40817810099910004312",
            "bank_account_name": "My Salary",
            "bank": "Тинькофф"
        }

        response = await client.post("/me/bank_account", json=payload)

        # 4. Проверки
        assert response.status_code == status.HTTP_200_OK

        data = response.json()
        assert data["bank_account_id"] == 123
        assert data["bank_account_name"] == "My Salary"
        assert data["bank"] == "Тинькофф"
        assert data["balance"] == "5000.00"

        mock_bank_account_repo.create.assert_awaited_once()
        call_args = mock_bank_account_repo.create.call_args
        assert call_args[0][0] == 1  # user_id

    async def test_add_bank_account_invalid_number(
        self,
        client: AsyncClient,
        app,
        mock_bank_account_repo
    ):
        """
        Тест ошибки валидации номера счета (меньше 16 символов).
        """
        mock_user = MagicMock()
        mock_user.id = 1
        app.dependency_overrides[get_current_user] = lambda: mock_user
        app.dependency_overrides[get_bank_account_repository] = lambda: mock_bank_account_repo

        payload = {
            "bank_account_number": "123",  # Слишком короткий
            "bank_account_name": "Invalid",
            "bank": "Сбербанк"
        }

        response = await client.post("/me/bank_account", json=payload)

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "at least 16 digits" in response.json()["detail"]

        mock_bank_account_repo.create.assert_not_awaited()

    async def test_get_user_bank_accounts(
        self,
        client: AsyncClient,
        app,
        mock_bank_account_repo
    ):
        """
        Тест получения списка счетов пользователя.
        """
        mock_user = MagicMock()
        mock_user.id = 1
        app.dependency_overrides[get_current_user] = lambda: mock_user
        app.dependency_overrides[get_bank_account_repository] = lambda: mock_bank_account_repo

        acc1 = MagicMock()
        acc1.bank_account_id = 1
        acc1.bank_account_name = "Acc1"
        acc1.currency = "RUB"
        acc1.balance = "100"

        bank_obj = MagicMock()
        bank_obj.name = "Bank1"
        acc1.bank = bank_obj

        mock_bank_account_repo.get_all_by_user_id.return_value = [acc1]

        response = await client.get("/me/bank_accounts")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 1
        assert data[0]["bank_account_id"] == 1

        mock_bank_account_repo.get_all_by_user_id.assert_awaited_once_with(1)

    async def test_delete_bank_account_success(
        self,
        client: AsyncClient,
        app,
        mock_bank_account_repo
    ):
        """
        Тест успешного удаления счета.
        """
        mock_user = MagicMock()
        mock_user.id = 1
        app.dependency_overrides[get_current_user] = lambda: mock_user
        app.dependency_overrides[get_bank_account_repository] = lambda: mock_bank_account_repo

        mock_bank_account_repo.delete.return_value = MagicMock()

        response = await client.delete("/me/bank_account/99")

        assert response.status_code == status.HTTP_204_NO_CONTENT

        mock_bank_account_repo.delete.assert_awaited_once_with(99, 1)

    async def test_delete_bank_account_not_found(
        self,
        client: AsyncClient,
        app,
        mock_bank_account_repo
    ):
        """
        Тест удаления несуществующего счета (репозиторий возвращает None).
        """
        mock_user = MagicMock()
        mock_user.id = 1
        app.dependency_overrides[get_current_user] = lambda: mock_user
        app.dependency_overrides[get_bank_account_repository] = lambda: mock_bank_account_repo

        mock_bank_account_repo.delete.return_value = None

        response = await client.delete("/me/bank_account/999")

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert response.json()["detail"] == "Bank account not found"
