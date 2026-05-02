from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from app.models import Bank, Bank_Accounts
from app.schemas import Bank_AccountCreate
from fastapi import HTTPException

pytestmark = pytest.mark.asyncio

# Натсройка моков


def setup_execute_mocks(mock_db_session, side_effects: list):
    """Настройка side_effect для execute()."""
    mock_results = []
    for return_value in side_effects:
        mock_scalar_result = MagicMock()
        mock_scalar_result.first.return_value = return_value

        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalar_result
        mock_results.append(mock_result)

    mock_db_session.execute = AsyncMock(side_effect=mock_results)
    return mock_results


def setup_add_mock_with_ids(mock_db_session, bank_id: int, account_id: int):
    """Настраивает mock_db_session.add для авто-присвоения ID объектам"""

    def mock_add(obj):
        if isinstance(obj, Bank) and getattr(obj, "id", None) is None:
            obj.id = bank_id
        if isinstance(obj, Bank_Accounts):
            if getattr(obj, "bank_account_id", None) is None:
                obj.bank_account_id = account_id
            if getattr(obj, "bank_id", None) is None:
                obj.bank_id = bank_id
        return MagicMock()

    mock_db_session.add = MagicMock(side_effect=mock_add)


# ТЕСТЫ


@patch("app.repository.bank_account_repository.EventPublisher")
async def test_create_success(
    mock_event_publisher_class, mock_db_session, mock_hash_function, bank_account_create_schema, mock_httpx_async_client
):
    """Успешное создание банковского счёта"""
    from app.repository.bank_account_repository import Bank_AccountRepository

    user_id = 1
    expected_hash = "a" * 64
    mock_hash_function.return_value = expected_hash

    # 1. Настройка БД: [account not found, bank not found]
    setup_execute_mocks(mock_db_session, [None, None])

    # 2. Настройка HTTP ответа
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"balance": "1500.50", "currency": "RUB"}

    client_instance = mock_httpx_async_client.return_value.__aenter__.return_value
    client_instance.post.return_value = mock_response

    # 3. Настройка ID
    setup_add_mock_with_ids(mock_db_session, bank_id=99, account_id=123)

    # 4. Мок refresh
    def mock_refresh(obj, attrs=None):
        if isinstance(obj, Bank_Accounts) and (not hasattr(obj, "bank") or obj.bank is None):
            obj.bank = MagicMock(name="Сбербанк", id=99)

    mock_db_session.refresh.side_effect = mock_refresh

    # 5. Event publisher mock
    mock_publisher_instance = AsyncMock()
    mock_event_publisher_class.return_value = mock_publisher_instance

    repo = Bank_AccountRepository(db=mock_db_session)

    # Act
    result_account, result_hash = await repo.create(user_id, bank_account_create_schema)

    # Assert
    assert result_hash == expected_hash
    assert result_account.bank_account_id == 123
    assert result_account.bank_id == 99
    assert result_account.currency == "RUB"
    assert result_account.balance == Decimal("1500.50")

    mock_db_session.commit.assert_called_once()
    mock_publisher_instance.publish.assert_called_once()


async def test_create_duplicate_account(mock_db_session, mock_hash_function, bank_account_create_schema):
    """Попытка создать дубликат счёта"""
    from app.repository.bank_account_repository import Bank_AccountRepository

    user_id = 1

    # Мок: счёт уже существует
    existing_account = MagicMock(spec=Bank_Accounts)
    setup_execute_mocks(mock_db_session, [existing_account])

    repo = Bank_AccountRepository(db=mock_db_session)

    with pytest.raises(HTTPException) as exc_info:
        await repo.create(user_id, bank_account_create_schema)

    assert exc_info.value.status_code == 400
    assert "already exists" in exc_info.value.detail
    mock_db_session.commit.assert_not_called()


async def test_create_account_not_found_in_bank(
    mock_db_session, mock_hash_function, bank_account_create_schema, mock_httpx_async_client
):
    """Счёт не найден в банковской системе (404)"""
    from app.repository.bank_account_repository import Bank_AccountRepository

    user_id = 1

    setup_execute_mocks(mock_db_session, [None, None])

    # Настраиваем ответ 404
    mock_response = MagicMock()
    mock_response.status_code = 404

    client_instance = mock_httpx_async_client.return_value.__aenter__.return_value
    client_instance.post.return_value = mock_response

    repo = Bank_AccountRepository(db=mock_db_session)

    with pytest.raises(HTTPException) as exc_info:
        await repo.create(user_id, bank_account_create_schema)

    assert exc_info.value.status_code == 400
    assert "does not exist" in exc_info.value.detail
    mock_db_session.commit.assert_not_called()


async def test_create_bank_validation_error(
    mock_db_session, mock_hash_function, bank_account_create_schema, mock_httpx_async_client
):
    """Ошибка валидации от банка (non-200, non-404)"""
    from app.repository.bank_account_repository import Bank_AccountRepository

    user_id = 1

    setup_execute_mocks(mock_db_session, [None, None])

    mock_response = MagicMock()
    mock_response.status_code = 500
    mock_response.json.return_value = {"detail": "Bank service unavailable"}

    client_instance = mock_httpx_async_client.return_value.__aenter__.return_value
    client_instance.post.return_value = mock_response

    repo = Bank_AccountRepository(db=mock_db_session)

    with pytest.raises(HTTPException) as exc_info:
        await repo.create(user_id, bank_account_create_schema)

    assert exc_info.value.status_code == 400
    assert "Bank validation failed" in exc_info.value.detail


@patch("app.repository.bank_account_repository.EventPublisher")
async def test_create_invalid_balance_fallback(
    mock_event_publisher_class, mock_db_session, mock_hash_function, bank_account_create_schema, mock_httpx_async_client
):
    """Некорректный balance в ответе банка -> fallback на 0.00"""
    from app.repository.bank_account_repository import Bank_AccountRepository

    user_id = 1

    setup_execute_mocks(mock_db_session, [None, None])

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"balance": "invalid_string", "currency": "USD"}

    client_instance = mock_httpx_async_client.return_value.__aenter__.return_value
    client_instance.post.return_value = mock_response

    setup_add_mock_with_ids(mock_db_session, bank_id=5, account_id=456)

    def mock_refresh(obj, attrs=None):
        if isinstance(obj, Bank_Accounts) and (not hasattr(obj, "bank") or obj.bank is None):
            obj.bank = MagicMock(name="TestBank", id=5)

    mock_db_session.refresh.side_effect = mock_refresh

    # ВАЖНО: Возвращаем AsyncMock
    mock_publisher_instance = AsyncMock()
    mock_event_publisher_class.return_value = mock_publisher_instance

    repo = Bank_AccountRepository(db=mock_db_session)

    result_account, _ = await repo.create(user_id, bank_account_create_schema)

    assert result_account.balance == Decimal("0.00")
    assert result_account.currency == "USD"


@patch("app.repository.bank_account_repository.EventPublisher")
async def test_create_bank_auto_created(
    mock_event_publisher_class, mock_db_session, mock_hash_function, bank_account_create_schema, mock_httpx_async_client
):
    """Банк не существует - создаётся автоматически"""
    from app.repository.bank_account_repository import Bank_AccountRepository

    user_id = 1

    # 1. Account check -> None, Bank check -> None
    setup_execute_mocks(mock_db_session, [None, None])

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"balance": "100.00", "currency": "RUB"}

    client_instance = mock_httpx_async_client.return_value.__aenter__.return_value
    client_instance.post.return_value = mock_response

    setup_add_mock_with_ids(mock_db_session, bank_id=777, account_id=888)

    def mock_refresh(obj, attrs=None):
        if isinstance(obj, Bank_Accounts):
            obj.bank = MagicMock(name=bank_account_create_schema.bank, id=777)

    mock_db_session.refresh.side_effect = mock_refresh

    mock_publisher_instance = AsyncMock()
    mock_event_publisher_class.return_value = mock_publisher_instance

    repo = Bank_AccountRepository(db=mock_db_session)

    result_account, _ = await repo.create(user_id, bank_account_create_schema)

    assert result_account.bank_id == 777
    assert result_account.bank_account_id == 888

    added_objects = [c[0][0] for c in mock_db_session.add.call_args_list]
    assert any(isinstance(obj, Bank) for obj in added_objects), "Bank object should be added to session"


async def test_rename_success(mock_db_session):
    """Успешное переименование банковского счёта"""
    from unittest.mock import MagicMock

    from app.models import Bank_Accounts
    from app.repository.bank_account_repository import Bank_AccountRepository

    existing_account = MagicMock(spec=Bank_Accounts)
    existing_account.bank_account_name = "Старое имя"

    mock_scalar_result = MagicMock()
    mock_scalar_result.first.return_value = existing_account
    mock_result = MagicMock()
    mock_result.scalars.return_value = mock_scalar_result
    mock_db_session.execute = AsyncMock(return_value=mock_result)

    repo = Bank_AccountRepository(db=mock_db_session)
    result = await repo.rename(bank_account_id=1, user_id=1, new_name="Новое имя")

    assert result is existing_account
    assert existing_account.bank_account_name == "Новое имя"
    mock_db_session.commit.assert_called_once()
    mock_db_session.refresh.assert_called_once_with(existing_account)


@patch("app.repository.bank_account_repository.EventPublisher")
async def test_rename_publishes_event(mock_event_publisher_class, mock_db_session):
    """После переименования публикуется событие bank_account.renamed"""
    from app.models import Bank_Accounts
    from app.repository.bank_account_repository import Bank_AccountRepository

    existing_account = MagicMock(spec=Bank_Accounts)
    existing_account.bank_account_hash = "abc123"

    mock_scalar_result = MagicMock()
    mock_scalar_result.first.return_value = existing_account
    mock_result = MagicMock()
    mock_result.scalars.return_value = mock_scalar_result
    mock_db_session.execute = AsyncMock(return_value=mock_result)

    mock_publisher_instance = AsyncMock()
    mock_event_publisher_class.return_value = mock_publisher_instance

    repo = Bank_AccountRepository(db=mock_db_session)
    await repo.rename(bank_account_id=1, user_id=1, new_name="Новое имя")

    mock_publisher_instance.publish.assert_awaited_once()
    published_event = mock_publisher_instance.publish.call_args[0][0]
    assert published_event.event_type == "bank_account.renamed"
    assert published_event.payload["new_name"] == "Новое имя"
    assert published_event.payload["bank_account_hash"] == "abc123"


async def test_rename_account_not_found(mock_db_session):
    """Счёт не найден — возвращает None"""
    from app.repository.bank_account_repository import Bank_AccountRepository

    mock_scalar_result = MagicMock()
    mock_scalar_result.first.return_value = None
    mock_result = MagicMock()
    mock_result.scalars.return_value = mock_scalar_result
    mock_db_session.execute = AsyncMock(return_value=mock_result)

    repo = Bank_AccountRepository(db=mock_db_session)
    result = await repo.rename(bank_account_id=999, user_id=1, new_name="Новое имя")

    assert result is None
    mock_db_session.commit.assert_not_called()


async def test_create_strips_account_number(mock_db_session, mock_hash_function, mock_httpx_async_client):
    """Проверяем, что номер счёта очищается от пробелов"""
    from app.repository.bank_account_repository import Bank_AccountRepository

    user_id = 1
    schema_with_spaces = Bank_AccountCreate(
        bank_account_number="  40817810099910004312  ", bank_account_name="Test", bank="TestBank"
    )

    setup_execute_mocks(mock_db_session, [None, None])

    client_instance = mock_httpx_async_client.return_value.__aenter__.return_value
    client_instance.post.return_value.json.return_value = {"balance": "0.00", "currency": "RUB"}

    setup_add_mock_with_ids(mock_db_session, bank_id=1, account_id=1)
    mock_db_session.refresh.return_value = None

    with patch("app.repository.bank_account_repository.EventPublisher") as mock_pub:
        # ВАЖНО: Возвращаем AsyncMock
        mock_pub.return_value = AsyncMock()

        repo = Bank_AccountRepository(db=mock_db_session)
        await repo.create(user_id, schema_with_spaces)

    mock_hash_function.assert_called_once_with("40817810099910004312")
