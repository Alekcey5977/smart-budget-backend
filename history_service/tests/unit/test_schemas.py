import sys
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

PROJECT_ROOT = Path(__file__).parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import pytest  # noqa: E402
from app.schemas import DeleteResponse, HistoryEntryCreate, HistoryEntryResponse  # noqa: E402
from pydantic import ValidationError  # noqa: E402

# ==================== HistoryEntryCreate ====================


class TestHistoryEntryCreate:
    """Тесты схемы создания записи истории."""

    def test_valid_data(self):
        """Корректные данные → объект создаётся."""
        entry = HistoryEntryCreate(user_id=1, title="Цель создана", body="Цель «Отпуск» создана")
        assert entry.user_id == 1
        assert entry.title == "Цель создана"
        assert entry.body == "Цель «Отпуск» создана"

    def test_missing_user_id_raises(self):
        """Отсутствие user_id → ValidationError."""
        with pytest.raises(ValidationError):
            HistoryEntryCreate(title="Заголовок", body="Тело")

    def test_missing_title_raises(self):
        """Отсутствие title → ValidationError."""
        with pytest.raises(ValidationError):
            HistoryEntryCreate(user_id=1, body="Тело")

    def test_missing_body_raises(self):
        """Отсутствие body → ValidationError."""
        with pytest.raises(ValidationError):
            HistoryEntryCreate(user_id=1, title="Заголовок")


# ==================== HistoryEntryResponse ====================


class TestHistoryEntryResponse:
    """Тесты схемы ответа записи истории."""

    def test_valid_data(self):
        """Корректные данные → объект создаётся."""
        entry_id = uuid4()
        now = datetime.now(tz=timezone.utc)
        entry = HistoryEntryResponse(
            id=entry_id,
            user_id=1,
            title="Профиль обновлён",
            body="Вы обновили данные профиля",
            created_at=now,
        )
        assert entry.id == entry_id
        assert entry.user_id == 1
        assert entry.created_at == now

    def test_missing_id_raises(self):
        """Отсутствие id → ValidationError."""
        with pytest.raises(ValidationError):
            HistoryEntryResponse(
                user_id=1,
                title="Заголовок",
                body="Тело",
                created_at=datetime.now(),
            )

    def test_missing_created_at_raises(self):
        """Отсутствие created_at → ValidationError."""
        with pytest.raises(ValidationError):
            HistoryEntryResponse(
                id=uuid4(),
                user_id=1,
                title="Заголовок",
                body="Тело",
            )


# ==================== DeleteResponse ====================


class TestDeleteResponse:
    """Тесты схемы ответа на удаление."""

    def test_valid_data(self):
        """Корректные данные → объект создаётся."""
        resp = DeleteResponse(status="success", message="Запись удалена")
        assert resp.status == "success"
        assert resp.message == "Запись удалена"

    def test_missing_status_raises(self):
        """Отсутствие status → ValidationError."""
        with pytest.raises(ValidationError):
            DeleteResponse(message="Запись удалена")

    def test_missing_message_raises(self):
        """Отсутствие message → ValidationError."""
        with pytest.raises(ValidationError):
            DeleteResponse(status="success")
