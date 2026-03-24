import sys
from datetime import datetime
from pathlib import Path
from unittest.mock import AsyncMock
from uuid import uuid4

PROJECT_ROOT = Path(__file__).parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import pytest  # noqa: E402
from app.event_listener import EventListener  # noqa: E402

from shared.event_schema import DomainEvent  # noqa: E402


def make_event(event_type: str, payload: dict) -> DomainEvent:
    """Хелпер: создаёт DomainEvent с заданным типом и payload."""
    return DomainEvent(
        event_id=str(uuid4()),
        event_type=event_type,
        source="test-service",
        timestamp=datetime.now(),
        payload=payload,
    )


@pytest.fixture
def listener() -> EventListener:
    """EventListener с замоканным _create_and_broadcast_notification."""
    inst = EventListener()
    inst._create_and_broadcast_notification = AsyncMock()
    return inst


# ==================== build_notification_payload ====================

class TestBuildNotificationPayload:
    """Тесты чистой функции построения payload уведомления."""

    def test_returns_all_required_fields(self):
        """Возвращает id, user_id, title, body, is_read, created_at."""

        class FakeSaved:
            id = uuid4()
            user_id = 1
            title = "Порог цели"
            body = "Цель достигла 25%"
            created_at = datetime.now()

        result = EventListener().build_notification_payload(FakeSaved())
        assert set(result.keys()) == {"id", "user_id", "title", "body", "created_at", "is_read"}

    def test_is_read_defaults_to_false(self):
        """is_read по умолчанию False."""

        class FakeSaved:
            id = uuid4()
            user_id = 1
            title = "T"
            body = "B"
            created_at = datetime.now()

        result = EventListener().build_notification_payload(FakeSaved())
        assert result["is_read"] is False

    def test_is_read_can_be_overridden(self):
        """is_read можно передать явно."""

        class FakeSaved:
            id = uuid4()
            user_id = 1
            title = "T"
            body = "B"
            created_at = datetime.now()

        result = EventListener().build_notification_payload(FakeSaved(), is_read=True)
        assert result["is_read"] is True

    def test_id_is_string(self):
        """id сериализуется в строку."""

        class FakeSaved:
            id = uuid4()
            user_id = 1
            title = "T"
            body = "B"
            created_at = datetime.now()

        result = EventListener().build_notification_payload(FakeSaved())
        assert isinstance(result["id"], str)


# ==================== _extract_user_id ====================

class TestExtractUserId:
    """Тесты извлечения user_id из payload события."""

    def test_integer_user_id(self):
        """Целое число → возвращает как int."""
        assert EventListener()._extract_user_id({"user_id": 42}) == 42

    def test_string_user_id(self):
        """Строка с числом → конвертируется в int."""
        assert EventListener()._extract_user_id({"user_id": "42"}) == 42

    def test_missing_user_id_returns_none(self):
        """Нет поля user_id → None."""
        assert EventListener()._extract_user_id({}) is None

    def test_non_numeric_user_id_returns_none(self):
        """Строка 'abc' → None."""
        assert EventListener()._extract_user_id({"user_id": "abc"}) is None

    def test_none_user_id_returns_none(self):
        """user_id=None → None."""
        assert EventListener()._extract_user_id({"user_id": None}) is None


# ==================== handle_event ====================

class TestHandleEvent:
    """Тесты диспетчеризации событий."""

    async def test_dispatches_purpose_progress(self, listener):
        """purpose.progress → вызывает _handle_purpose_progress."""
        listener._handle_purpose_progress = AsyncMock()
        event = make_event("purpose.progress", {
            "user_id": 1, "purpose_name": "Отпуск",
            "progress_percent": 25.0, "threshold": 25,
        })
        await listener.handle_event(event)
        listener._handle_purpose_progress.assert_called_once_with(event)

    async def test_dispatches_user_registered(self, listener):
        """user.registered → вызывает _handle_user_registered."""
        listener._handle_user_registered = AsyncMock()
        event = make_event("user.registered", {"user_id": 1, "first_name": "Алексей"})
        await listener.handle_event(event)
        listener._handle_user_registered.assert_called_once_with(event)

    async def test_unknown_event_type_ignored(self, listener):
        """Неизвестный тип события → не падает, _create_and_broadcast не вызывается."""
        event = make_event("unknown.event", {"user_id": 1})
        await listener.handle_event(event)
        listener._create_and_broadcast_notification.assert_not_called()

    async def test_purpose_created_ignored(self, listener):
        """purpose.created перенесён в history_service — не обрабатывается."""
        event = make_event("purpose.created", {"user_id": 1, "name": "Отпуск"})
        await listener.handle_event(event)
        listener._create_and_broadcast_notification.assert_not_called()

    async def test_purpose_deleted_ignored(self, listener):
        """purpose.deleted перенесён в history_service — не обрабатывается."""
        event = make_event("purpose.deleted", {"user_id": 1, "name": "Отпуск"})
        await listener.handle_event(event)
        listener._create_and_broadcast_notification.assert_not_called()

    async def test_user_updated_ignored(self, listener):
        """user.updated перенесён в history_service — не обрабатывается."""
        event = make_event("user.updated", {"user_id": 1, "first_name": "Иван"})
        await listener.handle_event(event)
        listener._create_and_broadcast_notification.assert_not_called()

    async def test_bank_account_added_ignored(self, listener):
        """bank_account.added перенесён в history_service — не обрабатывается."""
        event = make_event("bank_account.added", {"user_id": 1, "bank_name": "Сбербанк"})
        await listener.handle_event(event)
        listener._create_and_broadcast_notification.assert_not_called()

    async def test_missing_user_id_does_not_call_create(self, listener):
        """Если user_id отсутствует — уведомление не создаётся."""
        event = make_event("purpose.progress", {
            "purpose_name": "Без юзера", "progress_percent": 25.0, "threshold": 25,
        })
        await listener.handle_event(event)
        listener._create_and_broadcast_notification.assert_not_called()


# ==================== Event Handlers ====================

class TestEventHandlers:
    """Тесты оставшихся обработчиков — правильные title/body и user_id."""

    async def test_handle_purpose_progress(self, listener):
        """purpose.progress → title содержит порог, body — прогресс."""
        event = make_event("purpose.progress", {
            "user_id": 2, "purpose_name": "Отпуск",
            "progress_percent": 50.0, "threshold": 50,
        })
        await listener._handle_purpose_progress(event)
        listener._create_and_broadcast_notification.assert_called_once()
        user_id, title, body = listener._create_and_broadcast_notification.call_args[0]
        assert user_id == 2
        assert "50" in title
        assert "Отпуск" in body

    async def test_handle_user_registered(self, listener):
        """user.registered → приветствие с именем пользователя."""
        event = make_event("user.registered", {
            "user_id": 3, "first_name": "Алексей",
        })
        await listener._handle_user_registered(event)
        user_id, title, body = listener._create_and_broadcast_notification.call_args[0]
        assert user_id == 3
        assert "Алексей" in body

    async def test_handle_event_with_both_active_types(self, listener):
        """Оба активных типа событий диспетчеризируются без исключений."""
        payloads = {
            "purpose.progress": {"user_id": 1, "purpose_name": "X", "progress_percent": 25.0, "threshold": 25},
            "user.registered": {"user_id": 1, "first_name": "X"},
        }
        for event_type, payload in payloads.items():
            listener._create_and_broadcast_notification.reset_mock()
            event = make_event(event_type, payload)
            await listener.handle_event(event)
            listener._create_and_broadcast_notification.assert_called_once()
