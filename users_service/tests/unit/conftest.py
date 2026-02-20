# Добавляем корень проекта в sys.path ДО импортов
import sys
from pathlib import Path

CURRENT_FILE = Path(__file__).resolve()
PROJECT_ROOT = CURRENT_FILE.parents[3]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

from shared.event_publisher import EventPublisher
from users_service.app.repository.user_repository import UserRepository


@pytest.fixture
def mock_db_session():
    session = AsyncMock()
    session.execute = AsyncMock()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()
    session.add = MagicMock()
    return session


@pytest.fixture
def mock_event_publisher():
    publisher = AsyncMock(spec=EventPublisher)
    publisher.publish = AsyncMock()
    return publisher


@pytest.fixture
def user_repo(mock_db_session, mock_event_publisher):
    return UserRepository(db=mock_db_session, event_publisher=mock_event_publisher)
