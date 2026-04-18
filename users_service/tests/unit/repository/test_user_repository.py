from unittest.mock import AsyncMock, MagicMock

import pytest

from shared.event_schema import DomainEvent
from users_service.app.repository.user_repository import UserRepository
from users_service.app.schemas import UserCreate, UserUpdate


@pytest.mark.asyncio
async def test_create_user_success(
    user_repo: UserRepository,
    mock_db_session,
    mock_event_publisher,
):
    """Тест создания пользователя"""
    # Arrange
    user_data = UserCreate(
        email="test@test.com",
        first_name="Ivan",
        last_name="Ivanov",
        middle_name="Ivanovich",
        password="SecurePassword123!",
    )

    fake_saved_user = MagicMock()
    fake_saved_user.id = 1
    fake_saved_user.email = user_data.email
    fake_saved_user.first_name = user_data.first_name

    def side_effect_refresh(obj):
        obj.id = 1

    mock_db_session.add = MagicMock()
    mock_db_session.commit = AsyncMock()
    mock_db_session.refresh = AsyncMock(side_effect=side_effect_refresh)

    # Act
    result = await user_repo.create(user_data, "hashed_pwd_123")

    # Assert
    assert result.id == 1
    assert result.email == "test@test.com"

    # Проверка вызовов БД
    mock_db_session.add.assert_called_once()
    added_obj = mock_db_session.add.call_args[0][0]
    assert added_obj.email == "test@test.com"

    mock_db_session.commit.assert_called_once()
    mock_db_session.refresh.assert_called_once()

    # Проверка события
    mock_event_publisher.publish.assert_called_once()
    event_call_args = mock_event_publisher.publish.call_args[0][0]

    assert isinstance(event_call_args, DomainEvent)
    assert event_call_args.event_type == "user.registered"
    assert event_call_args.payload["first_name"] == "Ivan"
    assert event_call_args.payload["user_id"] == 1


@pytest.mark.asyncio
async def test_get_by_id_success(user_repo: UserRepository, mock_db_session):
    """Тест получения пользователя по ID"""
    # Arrange
    mock_user = MagicMock()
    # Эмулируем цепочку: execute -> scalar_one_or_none
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_user
    mock_db_session.execute.return_value = mock_result

    # Act
    result = await user_repo.get_by_id(1)

    # Assert
    assert result == mock_user

    mock_db_session.execute.assert_called_once()


@pytest.mark.asyncio
async def test_get_by_id_not_found(user_repo: UserRepository, mock_db_session):
    """Тест: пользователь не найден по ID"""
    # Arrange
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_db_session.execute.return_value = mock_result

    # Act
    result = await user_repo.get_by_id(999)

    # Assert
    assert result is None


@pytest.mark.asyncio
async def test_get_by_email_success(user_repo: UserRepository, mock_db_session):
    """Тест получения пользователя по email"""
    # Arrange
    mock_user = MagicMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_user
    mock_db_session.execute.return_value = mock_result

    # Act
    result = await user_repo.get_by_email("test@test.com")

    # Assert
    assert result == mock_user


@pytest.mark.asyncio
async def test_update_user_success(user_repo: UserRepository, mock_db_session, mock_event_publisher):
    """Тест успешного обновления пользователя"""
    # Arrange
    mock_existing_user = MagicMock(id=1, first_name="Old", last_name="Old", middle_name="Old", email="old@test.com")

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_existing_user
    mock_db_session.execute.return_value = mock_result

    mock_db_session.commit = AsyncMock()
    mock_db_session.refresh = AsyncMock()

    update_data = UserUpdate(first_name="New")

    # Act
    result = await user_repo.update(1, update_data)

    # Assert
    assert result is not None
    assert result.first_name == "New"

    mock_db_session.commit.assert_called_once()
    mock_db_session.refresh.assert_called_once()

    # Проверяем событие
    mock_event_publisher.publish.assert_called_once()
    event = mock_event_publisher.publish.call_args[0][0]
    assert event.event_type == "user.updated"
    assert event.payload["first_name"] == "New"


@pytest.mark.asyncio
async def test_update_user_not_found(user_repo: UserRepository, mock_db_session, mock_event_publisher):
    """Тест: обновление несуществующего пользователя"""
    # Arrange
    # Возвращаем None при попытке найти пользователя
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_db_session.execute.return_value = mock_result

    update_data = UserUpdate(first_name="New")

    # Act
    result = await user_repo.update(999, update_data)

    # Assert
    assert result is None
    # Событие НЕ должно публиковаться, если пользователь не найден
    mock_event_publisher.publish.assert_not_called()
    mock_db_session.commit.assert_not_called()


@pytest.mark.asyncio
async def test_update_middle_name_empty_to_null(user_repo: UserRepository, mock_db_session):
    """Тест: middle_name="" преобразуется в None"""
    # Arrange
    mock_existing_user = MagicMock(middle_name="Old", id=1, first_name="Test", last_name="Test", email="t@t.com")

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_existing_user
    mock_db_session.execute.return_value = mock_result

    mock_db_session.commit = AsyncMock()
    mock_db_session.refresh = AsyncMock()

    update_data = UserUpdate(middle_name="")

    # Act
    result = await user_repo.update(1, update_data)

    # Assert
    assert result.middle_name is None
    assert mock_db_session.commit.called


@pytest.mark.asyncio
async def test_exists_with_email_true(user_repo: UserRepository, mock_db_session):
    """Тест: пользователь с email существует"""
    # Arrange
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = MagicMock()
    mock_db_session.execute.return_value = mock_result

    # Act
    result = await user_repo.exists_with_email("test@test.com")

    # Assert
    assert result is True


@pytest.mark.asyncio
async def test_exists_with_email_false(user_repo: UserRepository, mock_db_session):
    """Тест: пользователь с email не существует"""
    # Arrange
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_db_session.execute.return_value = mock_result

    # Act
    result = await user_repo.exists_with_email("unknown@test.com")

    # Assert
    assert result is False
