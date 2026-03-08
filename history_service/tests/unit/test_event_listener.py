import sys
from pathlib import Path
from datetime import datetime
from uuid import uuid4
from unittest.mock import AsyncMock

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
    """EventListener с замоканным _create_and_broadcast_entry."""
    inst = EventListener()
    inst._create_and_broadcast_entry = AsyncMock()
    return inst


# ==================== build_entry_payload ====================

class TestBuildEntryPayload:
    """Тесты чистой функции построения payload записи истории."""

    def test_returns_all_required_fields(self):
        """Возвращает id, user_id, title, body, created_at."""

        class FakeSaved:
            id = uuid4()
            user_id = 1
            title = "Цель создана"
            body = "Цель «Отпуск» на сумму 50000 руб. создана"
            created_at = datetime.now()

        result = EventListener().build_entry_payload(FakeSaved())
        assert set(result.keys()) == {"id", "user_id", "title", "body", "created_at"}

    def test_id_is_string(self):
        """id сериализуется в строку (UUID → str)."""

        class FakeSaved:
            id = uuid4()
            user_id = 1
            title = "T"
            body = "B"
            created_at = datetime.now()

        result = EventListener().build_entry_payload(FakeSaved())
        assert isinstance(result["id"], str)

    def test_created_at_is_isoformat_string(self):
        """created_at сериализуется через isoformat()."""
        now = datetime.now()

        class FakeSaved:
            id = uuid4()
            user_id = 1
            title = "T"
            body = "B"
            created_at = now

        result = EventListener().build_entry_payload(FakeSaved())
        assert result["created_at"] == now.isoformat()

    def test_user_id_is_int(self):
        """user_id возвращается как int."""

        class FakeSaved:
            id = uuid4()
            user_id = 42
            title = "T"
            body = "B"
            created_at = datetime.now()

        result = EventListener().build_entry_payload(FakeSaved())
        assert result["user_id"] == 42
        assert isinstance(result["user_id"], int)


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


# ==================== handle_event (диспетчеризация) ====================

class TestHandleEvent:
    """Тесты диспетчеризации событий на обработчики."""

    async def test_dispatches_user_updated(self, listener):
        """user.updated → вызывает _handle_user_updated."""
        listener._handle_user_updated = AsyncMock()
        event = make_event("user.updated", {"user_id": 1, "first_name": "Иван"})
        await listener.handle_event(event)
        listener._handle_user_updated.assert_called_once_with(event)

    async def test_dispatches_user_avatar_updated(self, listener):
        """user.avatar.updated → вызывает _handle_user_avatar_updated."""
        listener._handle_user_avatar_updated = AsyncMock()
        event = make_event("user.avatar.updated", {"user_id": 1})
        await listener.handle_event(event)
        listener._handle_user_avatar_updated.assert_called_once_with(event)

    async def test_dispatches_purpose_created(self, listener):
        """purpose.created → вызывает _handle_purpose_created."""
        listener._handle_purpose_created = AsyncMock()
        event = make_event("purpose.created", {"user_id": 1, "name": "Отпуск", "target_amount": "50000"})
        await listener.handle_event(event)
        listener._handle_purpose_created.assert_called_once_with(event)

    async def test_dispatches_purpose_deleted(self, listener):
        """purpose.deleted → вызывает _handle_purpose_deleted."""
        listener._handle_purpose_deleted = AsyncMock()
        event = make_event("purpose.deleted", {"user_id": 1, "name": "Отпуск"})
        await listener.handle_event(event)
        listener._handle_purpose_deleted.assert_called_once_with(event)

    async def test_dispatches_purpose_updated(self, listener):
        """purpose.updated → вызывает _handle_purpose_updated."""
        listener._handle_purpose_updated = AsyncMock()
        event = make_event("purpose.updated", {"user_id": 1, "name": "Отпуск"})
        await listener.handle_event(event)
        listener._handle_purpose_updated.assert_called_once_with(event)

    async def test_dispatches_bank_account_added(self, listener):
        """bank_account.added → вызывает _handle_bank_account_added."""
        listener._handle_bank_account_added = AsyncMock()
        event = make_event("bank_account.added", {"user_id": 1, "bank_name": "Сбербанк"})
        await listener.handle_event(event)
        listener._handle_bank_account_added.assert_called_once_with(event)

    async def test_dispatches_bank_account_deleted(self, listener):
        """bank_account.deleted → вызывает _handle_bank_account_deleted."""
        listener._handle_bank_account_deleted = AsyncMock()
        event = make_event("bank_account.deleted", {"user_id": 1, "bank_name": "Сбербанк"})
        await listener.handle_event(event)
        listener._handle_bank_account_deleted.assert_called_once_with(event)

    async def test_unknown_event_type_ignored(self, listener):
        """Неизвестный тип события → не падает, _create_and_broadcast_entry не вызывается."""
        event = make_event("unknown.event", {"user_id": 1})
        await listener.handle_event(event)
        listener._create_and_broadcast_entry.assert_not_called()

    async def test_missing_user_id_does_not_call_create(self, listener):
        """Если user_id отсутствует — запись не создаётся."""
        event = make_event("user.updated", {"first_name": "Без юзера"})
        await listener.handle_event(event)
        listener._create_and_broadcast_entry.assert_not_called()


# ==================== Event Handlers ====================

class TestEventHandlers:
    """Тесты обработчиков событий — правильные title/body и user_id."""

    async def test_handle_user_updated(self, listener):
        """user.updated → title='Профиль обновлён', body о профиле."""
        event = make_event("user.updated", {"user_id": 1, "first_name": "Иван"})
        await listener._handle_user_updated(event)
        listener._create_and_broadcast_entry.assert_called_once()
        user_id, title, body = listener._create_and_broadcast_entry.call_args[0]
        assert user_id == 1
        assert title == "Профиль обновлён"
        assert "профил" in body.lower()

    async def test_handle_user_avatar_updated(self, listener):
        """user.avatar.updated → title='Аватар обновлён'."""
        event = make_event("user.avatar.updated", {"user_id": 2})
        await listener._handle_user_avatar_updated(event)
        listener._create_and_broadcast_entry.assert_called_once()
        user_id, title, body = listener._create_and_broadcast_entry.call_args[0]
        assert user_id == 2
        assert title == "Аватар обновлён"

    async def test_handle_purpose_created(self, listener):
        """purpose.created → title='Цель создана', body содержит название и сумму."""
        event = make_event("purpose.created", {
            "user_id": 3, "name": "Отпуск", "target_amount": "50000",
        })
        await listener._handle_purpose_created(event)
        listener._create_and_broadcast_entry.assert_called_once()
        user_id, title, body = listener._create_and_broadcast_entry.call_args[0]
        assert user_id == 3
        assert title == "Цель создана"
        assert "Отпуск" in body
        assert "50000" in body

    async def test_handle_purpose_deleted(self, listener):
        """purpose.deleted → title='Цель удалена', body содержит название цели."""
        event = make_event("purpose.deleted", {
            "user_id": 4, "name": "Машина", "target_amount": "300000",
        })
        await listener._handle_purpose_deleted(event)
        listener._create_and_broadcast_entry.assert_called_once()
        user_id, title, body = listener._create_and_broadcast_entry.call_args[0]
        assert user_id == 4
        assert title == "Цель удалена"
        assert "Машина" in body

    async def test_handle_purpose_updated(self, listener):
        """purpose.updated → title='Цель изменена', body содержит название цели."""
        event = make_event("purpose.updated", {"user_id": 5, "name": "Квартира"})
        await listener._handle_purpose_updated(event)
        listener._create_and_broadcast_entry.assert_called_once()
        user_id, title, body = listener._create_and_broadcast_entry.call_args[0]
        assert user_id == 5
        assert title == "Цель изменена"
        assert "Квартира" in body

    async def test_handle_bank_account_added(self, listener):
        """bank_account.added → title='Счёт добавлен', body содержит название банка."""
        event = make_event("bank_account.added", {"user_id": 6, "bank_name": "Сбербанк"})
        await listener._handle_bank_account_added(event)
        listener._create_and_broadcast_entry.assert_called_once()
        user_id, title, body = listener._create_and_broadcast_entry.call_args[0]
        assert user_id == 6
        assert title == "Счёт добавлен"
        assert "Сбербанк" in body

    async def test_handle_bank_account_deleted(self, listener):
        """bank_account.deleted → title='Счёт удалён', body содержит название банка."""
        event = make_event("bank_account.deleted", {"user_id": 7, "bank_name": "Тинькофф"})
        await listener._handle_bank_account_deleted(event)
        listener._create_and_broadcast_entry.assert_called_once()
        user_id, title, body = listener._create_and_broadcast_entry.call_args[0]
        assert user_id == 7
        assert title == "Счёт удалён"
        assert "Тинькофф" in body
