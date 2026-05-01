import os
import pathlib
import sys
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

SERVICE_ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
PROJECT_ROOT = SERVICE_ROOT.parent
for p in (str(SERVICE_ROOT), str(PROJECT_ROOT)):
    if p not in sys.path:
        sys.path.insert(0, p)

os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://user:pass@localhost/test")
os.environ.setdefault("PSEUDO_BANK_SERVICE_URL", "http://fake-bank-service")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379")

from shared.event_schema import DomainEvent  # noqa: E402


def _make_event(event_type: str, payload: dict) -> DomainEvent:
    return DomainEvent(
        event_id="00000000-0000-0000-0000-000000000001",
        event_type=event_type,
        source="test",
        timestamp="2024-01-01T00:00:00",
        payload=payload,
    )


class TestEventListener:
    @pytest.mark.asyncio
    async def test_handle_bank_account_added_calls_sync(self):
        """При получении bank_account.added вызывается sync_by_account"""
        from app.event_listener import EventListener

        event = _make_event(
            "bank_account.added",
            {"user_id": 42, "bank_account_hash": "abc123", "bank_name": "Sber"},
        )

        mock_repo = AsyncMock()
        mock_repo.sync_by_account = AsyncMock(return_value={"transactions": 5})

        with (
            patch("app.event_listener.AsyncSessionLocal") as mock_session_local,
            patch("app.event_listener.SyncRepository", return_value=mock_repo),
        ):
            mock_session_local.return_value.__aenter__ = AsyncMock(return_value=MagicMock())
            mock_session_local.return_value.__aexit__ = AsyncMock(return_value=False)

            listener = EventListener()
            await listener._handle_bank_account_added(event)

        mock_repo.sync_by_account.assert_awaited_once_with("abc123", 42)

    @pytest.mark.asyncio
    async def test_handle_bank_account_added_missing_hash(self):
        """Если bank_account_hash отсутствует — sync не вызывается"""
        from app.event_listener import EventListener

        event = _make_event("bank_account.added", {"user_id": 42})

        mock_repo = AsyncMock()

        with (
            patch("app.event_listener.AsyncSessionLocal"),
            patch("app.event_listener.SyncRepository", return_value=mock_repo),
        ):
            listener = EventListener()
            await listener._handle_bank_account_added(event)

        mock_repo.sync_by_account.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_handle_bank_account_added_invalid_user_id(self):
        """Если user_id невалиден — sync не вызывается"""
        from app.event_listener import EventListener

        event = _make_event(
            "bank_account.added",
            {"user_id": "not-a-number", "bank_account_hash": "abc123"},
        )

        mock_repo = AsyncMock()

        with (
            patch("app.event_listener.AsyncSessionLocal"),
            patch("app.event_listener.SyncRepository", return_value=mock_repo),
        ):
            listener = EventListener()
            await listener._handle_bank_account_added(event)

        mock_repo.sync_by_account.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_handle_event_unknown_type_is_ignored(self):
        """Неизвестный тип события не вызывает ошибки"""
        from app.event_listener import EventListener

        event = _make_event("unknown.event", {"user_id": 1})
        listener = EventListener()
        await listener.handle_event(event)

    @pytest.mark.asyncio
    async def test_handle_bank_account_renamed_calls_rename(self):
        """При получении bank_account.renamed вызывается rename_bank_account"""
        from app.event_listener import EventListener

        event = _make_event(
            "bank_account.renamed",
            {"user_id": 1, "bank_account_hash": "abc123", "new_name": "Новое имя"},
        )

        mock_repo = AsyncMock()
        mock_repo.rename_bank_account = AsyncMock(return_value=True)

        with (
            patch("app.event_listener.AsyncSessionLocal") as mock_session_local,
            patch("app.event_listener.SyncRepository", return_value=mock_repo),
        ):
            mock_session_local.return_value.__aenter__ = AsyncMock(return_value=MagicMock())
            mock_session_local.return_value.__aexit__ = AsyncMock(return_value=False)

            listener = EventListener()
            await listener._handle_bank_account_renamed(event)

        mock_repo.rename_bank_account.assert_awaited_once_with("abc123", "Новое имя")

    @pytest.mark.asyncio
    async def test_handle_bank_account_renamed_missing_fields(self):
        """Если отсутствует hash или new_name — rename не вызывается"""
        from app.event_listener import EventListener

        event = _make_event("bank_account.renamed", {"user_id": 1})

        mock_repo = AsyncMock()

        with (
            patch("app.event_listener.AsyncSessionLocal"),
            patch("app.event_listener.SyncRepository", return_value=mock_repo),
        ):
            listener = EventListener()
            await listener._handle_bank_account_renamed(event)

        mock_repo.rename_bank_account.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_handle_bank_account_renamed_account_not_found(self):
        """Если счёт не найден в transactions DB — ошибки нет"""
        from app.event_listener import EventListener

        event = _make_event(
            "bank_account.renamed",
            {"user_id": 1, "bank_account_hash": "unknown_hash", "new_name": "Имя"},
        )

        mock_repo = AsyncMock()
        mock_repo.rename_bank_account = AsyncMock(return_value=False)

        with (
            patch("app.event_listener.AsyncSessionLocal") as mock_session_local,
            patch("app.event_listener.SyncRepository", return_value=mock_repo),
        ):
            mock_session_local.return_value.__aenter__ = AsyncMock(return_value=MagicMock())
            mock_session_local.return_value.__aexit__ = AsyncMock(return_value=False)

            listener = EventListener()
            await listener._handle_bank_account_renamed(event)

        mock_repo.rename_bank_account.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_handle_bank_account_added_sync_error_is_caught(self):
        """Ошибка sync_by_account не пробрасывается наружу"""
        from app.event_listener import EventListener

        event = _make_event(
            "bank_account.added",
            {"user_id": 1, "bank_account_hash": "hash1"},
        )

        mock_repo = AsyncMock()
        mock_repo.sync_by_account = AsyncMock(side_effect=Exception("DB error"))

        with (
            patch("app.event_listener.AsyncSessionLocal") as mock_session_local,
            patch("app.event_listener.SyncRepository", return_value=mock_repo),
        ):
            mock_session_local.return_value.__aenter__ = AsyncMock(return_value=MagicMock())
            mock_session_local.return_value.__aexit__ = AsyncMock(return_value=False)

            listener = EventListener()
            await listener._handle_bank_account_added(event)
