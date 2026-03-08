import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from datetime import datetime  # noqa: E402
from uuid import uuid4  # noqa: E402

import pytest  # noqa: E402
from pydantic import ValidationError  # noqa: E402

from app.schemas import NotificationCreate, NotificationResponse  # noqa: E402


# ==================== NotificationCreate ====================

class TestNotificationCreate:
    """Тесты схемы создания уведомления."""

    def test_valid_data(self):
        """Валидные данные — схема создаётся без ошибок."""
        schema = NotificationCreate(
            user_id=1,
            title="Цель создана",
            body="Новая цель добавлена",
        )
        assert schema.user_id == 1
        assert schema.title == "Цель создана"
        assert schema.body == "Новая цель добавлена"

    def test_user_id_required(self):
        """Без user_id → ошибка валидации."""
        with pytest.raises(ValidationError):
            NotificationCreate(title="Test", body="Body")

    def test_title_required(self):
        """Без title → ошибка валидации."""
        with pytest.raises(ValidationError):
            NotificationCreate(user_id=1, body="Body")

    def test_body_required(self):
        """Без body → ошибка валидации."""
        with pytest.raises(ValidationError):
            NotificationCreate(user_id=1, title="Test")


# ==================== NotificationResponse ====================

class TestNotificationResponse:
    """Тесты схемы ответа."""

    def test_valid_response_unread(self):
        """Непрочитанное уведомление — is_read=False."""
        schema = NotificationResponse(
            id=uuid4(),
            user_id=1,
            title="Тест",
            body="Тело",
            is_read=False,
            created_at=datetime.now(),
        )
        assert schema.is_read is False
        assert schema.user_id == 1

    def test_valid_response_read(self):
        """Прочитанное уведомление — is_read=True."""
        schema = NotificationResponse(
            id=uuid4(),
            user_id=2,
            title="Прочитано",
            body="Текст",
            is_read=True,
            created_at=datetime.now(),
        )
        assert schema.is_read is True

    def test_all_required_fields(self):
        """Без обязательных полей → ошибка валидации."""
        with pytest.raises(ValidationError):
            NotificationResponse(user_id=1, title="Test")
