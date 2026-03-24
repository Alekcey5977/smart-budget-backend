"""
Юнит-тесты для Pydantic-схем gateway.
Нет HTTP и БД — только логика валидации.
"""
import pytest
from app.schemas.authorization_schemas import RegisterRequest, UserLogin, UserUpdateRequest
from pydantic import ValidationError

VALID_PASSWORD = "StrongPass1!"
VALID_EMAIL = "user@example.com"
VALID_FIRST = "Иван"
VALID_LAST = "Иванов"


# ──────────────────────────────────────────────────────────────
# RegisterRequest
# ──────────────────────────────────────────────────────────────
class TestRegisterRequest:
    def test_valid_full(self):
        req = RegisterRequest(
            email=VALID_EMAIL,
            password=VALID_PASSWORD,
            first_name=VALID_FIRST,
            last_name=VALID_LAST,
            middle_name="Иванович",
        )
        assert req.email == VALID_EMAIL

    def test_valid_no_middle_name(self):
        req = RegisterRequest(
            email=VALID_EMAIL,
            password=VALID_PASSWORD,
            first_name=VALID_FIRST,
            last_name=VALID_LAST,
        )
        assert req.middle_name is None

    def test_password_too_short(self):
        with pytest.raises(ValidationError) as exc_info:
            RegisterRequest(
                email=VALID_EMAIL,
                password="Ab1!",
                first_name=VALID_FIRST,
                last_name=VALID_LAST,
            )
        assert "8 characters" in str(exc_info.value)

    def test_password_too_long(self):
        with pytest.raises(ValidationError):
            RegisterRequest(
                email=VALID_EMAIL,
                password="A" * 65 + "a" * 65 + "1!",  # 132 chars > 128 limit
                first_name=VALID_FIRST,
                last_name=VALID_LAST,
            )

    def test_password_no_uppercase(self):
        with pytest.raises(ValidationError) as exc_info:
            RegisterRequest(
                email=VALID_EMAIL,
                password="weakpass1!",
                first_name=VALID_FIRST,
                last_name=VALID_LAST,
            )
        assert "uppercase" in str(exc_info.value)

    def test_password_no_lowercase(self):
        with pytest.raises(ValidationError) as exc_info:
            RegisterRequest(
                email=VALID_EMAIL,
                password="WEAKPASS1!",
                first_name=VALID_FIRST,
                last_name=VALID_LAST,
            )
        assert "lowercase" in str(exc_info.value)

    def test_password_no_digit(self):
        with pytest.raises(ValidationError) as exc_info:
            RegisterRequest(
                email=VALID_EMAIL,
                password="WeakPass!",
                first_name=VALID_FIRST,
                last_name=VALID_LAST,
            )
        assert "digit" in str(exc_info.value)

    def test_password_no_special_char(self):
        with pytest.raises(ValidationError) as exc_info:
            RegisterRequest(
                email=VALID_EMAIL,
                password="WeakPass1",
                first_name=VALID_FIRST,
                last_name=VALID_LAST,
            )
        assert "special character" in str(exc_info.value)

    def test_invalid_email(self):
        with pytest.raises(ValidationError):
            RegisterRequest(
                email="not-an-email",
                password=VALID_PASSWORD,
                first_name=VALID_FIRST,
                last_name=VALID_LAST,
            )

    def test_first_name_empty(self):
        with pytest.raises(ValidationError):
            RegisterRequest(
                email=VALID_EMAIL,
                password=VALID_PASSWORD,
                first_name="",
                last_name=VALID_LAST,
            )

    def test_first_name_too_long(self):
        with pytest.raises(ValidationError):
            RegisterRequest(
                email=VALID_EMAIL,
                password=VALID_PASSWORD,
                first_name="А" * 51,
                last_name=VALID_LAST,
            )


# ──────────────────────────────────────────────────────────────
# UserLogin
# ──────────────────────────────────────────────────────────────
class TestUserLogin:
    def test_valid(self):
        req = UserLogin(email=VALID_EMAIL, password=VALID_PASSWORD)
        assert req.email == VALID_EMAIL

    def test_invalid_email(self):
        with pytest.raises(ValidationError):
            UserLogin(email="bad-email", password=VALID_PASSWORD)

    def test_password_too_short(self):
        with pytest.raises(ValidationError):
            UserLogin(email=VALID_EMAIL, password="Ab1!")

    def test_password_no_uppercase(self):
        with pytest.raises(ValidationError) as exc_info:
            UserLogin(email=VALID_EMAIL, password="weakpass1!")
        assert "uppercase" in str(exc_info.value)

    def test_password_no_special_char(self):
        with pytest.raises(ValidationError) as exc_info:
            UserLogin(email=VALID_EMAIL, password="WeakPass1")
        assert "special character" in str(exc_info.value)


# ──────────────────────────────────────────────────────────────
# UserUpdateRequest
# ──────────────────────────────────────────────────────────────
class TestUserUpdateRequest:
    def test_only_first_name(self):
        req = UserUpdateRequest(first_name="Петр")
        assert req.first_name == "Петр"
        assert req.last_name is None

    def test_only_last_name(self):
        req = UserUpdateRequest(last_name="Петров")
        assert req.last_name == "Петров"

    def test_all_none_raises(self):
        with pytest.raises(ValidationError) as exc_info:
            UserUpdateRequest()
        assert "At least one field" in str(exc_info.value)

    def test_first_name_empty_string_raises(self):
        with pytest.raises(ValidationError):
            UserUpdateRequest(first_name="")

    def test_middle_name_empty_string_ok(self):
        # Empty string means "delete middle name"
        req = UserUpdateRequest(middle_name="")
        assert req.middle_name == ""

    def test_all_fields(self):
        req = UserUpdateRequest(
            first_name="Петр",
            last_name="Петров",
            middle_name="Петрович",
        )
        assert req.first_name == "Петр"
        assert req.last_name == "Петров"
        assert req.middle_name == "Петрович"
