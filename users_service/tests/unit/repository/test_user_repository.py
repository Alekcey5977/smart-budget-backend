import pytest
from users_service.app.repository.user_repository import UserRepository


@pytest.mark.asyncio
async def test_create_user_success(
        user_repo: UserRepository,
        mock_db_session,
        mock_event_publisher,
    ):
    """Тест создания пользователя
    
    Проверяет:
    - Пользователь сохраняется в БД
    - Событие публикуется
    - Возвращается объект с ID"""
    
    # ========== Arrange ==========
    from users_service.app.schemas import UserCreate
    from unittest.mock import AsyncMock, MagicMock

    user_data = UserCreate(
        email="test@test.com",
        first_name="Ivan",
        last_name="Ivanov",
        middle_name="Ivanovich",
        password="SecurePassword123!"
    )

    mock_db_session.add = MagicMock()
    mock_db_session.commit = AsyncMock()
    mock_db_session.refresh = AsyncMock(
        side_effect=lambda obj: setattr(obj, 'id', 1)
    )

    mock_user = MagicMock(id=1, **user_data.model_dump())

    # ========== Act ==========
    result = await user_repo.create(user_data, "hashed_pwd_123")

    # ========== Assert ==========
    # Проверка результата
    assert result.id == 1
    assert result.email == "test@test.com"

    # Проверка вызовов БД
    mock_db_session.add.assert_called_once()
    mock_db_session.commit.assert_called_once()
    mock_db_session.refresh.assert_called_once()

    # Проверка события
    mock_event_publisher.publish.assert_called_once()
    event = mock_event_publisher.publish.call_args[0][0]
    assert event.event_type == "user.registered"
    assert event.payload["first_name"] == "Ivan"
    assert mock_event_publisher.publish.call_count == 1




