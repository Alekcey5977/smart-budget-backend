import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import jwt  # noqa: E402
from app.auth import verify_websocket_token  # noqa: E402

TEST_SECRET = os.environ.get("ACCESS_SECRET_KEY", "test-secret-key-for-tests")


def make_token(
    user_id: int = 1,
    token_type: str = "access",
    secret: str = TEST_SECRET,
    expire_delta: timedelta | None = None,
) -> str:
    """Хелпер: создаёт JWT-токен с заданными параметрами."""
    payload: dict = {"sub": str(user_id), "type": token_type}
    if expire_delta is not None:
        payload["exp"] = datetime.now(tz=timezone.utc) + expire_delta
    return jwt.encode(payload, secret, algorithm="HS256")


class TestVerifyWebsocketToken:
    """Тесты верификации WebSocket-токена."""

    def test_valid_token_returns_user_id(self):
        """Валидный access-токен → возвращает user_id."""
        token = make_token(user_id=42)
        result = verify_websocket_token(token)
        assert result == 42

    def test_different_user_ids(self):
        """Разные user_id корректно декодируются."""
        for uid in [1, 100, 99999]:
            token = make_token(user_id=uid)
            assert verify_websocket_token(token) == uid

    def test_wrong_token_type_returns_none(self):
        """Токен с type='refresh' → None (не access)."""
        token = make_token(token_type="refresh")
        assert verify_websocket_token(token) is None

    def test_missing_type_field_returns_none(self):
        """Токен без поля type → None."""
        payload = {"sub": "1"}
        token = jwt.encode(payload, TEST_SECRET, algorithm="HS256")
        assert verify_websocket_token(token) is None

    def test_missing_sub_field_returns_none(self):
        """Токен без поля sub → None."""
        payload = {"type": "access"}
        token = jwt.encode(payload, TEST_SECRET, algorithm="HS256")
        assert verify_websocket_token(token) is None

    def test_expired_token_returns_none(self):
        """Просроченный токен → None."""
        token = make_token(expire_delta=timedelta(seconds=-10))
        assert verify_websocket_token(token) is None

    def test_valid_token_with_expiry_returns_user_id(self):
        """Валидный токен с будущим exp → возвращает user_id."""
        token = make_token(user_id=7, expire_delta=timedelta(hours=1))
        assert verify_websocket_token(token) == 7

    def test_wrong_secret_returns_none(self):
        """Токен, подписанный другим секретом → None."""
        token = make_token(secret="wrong-secret-key")
        assert verify_websocket_token(token) is None

    def test_invalid_token_string_returns_none(self):
        """Произвольная строка → None."""
        assert verify_websocket_token("not.a.valid.jwt") is None

    def test_empty_string_returns_none(self):
        """Пустая строка → None."""
        assert verify_websocket_token("") is None
