import pytest
from pydantic import ValidationError

from users_service.app.schemas import UserBase, UserCreate, UserLogin


class TestUserBase:
    """Тесты базовой схемы пользователя"""

    def test_user_base_valid(self):
        """Тест: валидные данные успешно валидируются"""
        user = UserBase(email="test@example.com", first_name="Ivan", last_name="Ivanov", middle_name="Ivanovich")
        assert user.email == "test@example.com"
        assert user.first_name == "Ivan"
        assert user.middle_name == "Ivanovich"

    def test_user_base_without_middle_name(self):
        """Тест: middle_name опционален"""
        user = UserBase(email="test@example.com", first_name="Ivan", last_name="Ivanov")
        assert user.middle_name is None

    def test_user_base_email_normalized_to_lowercase(self):
        """Тест: email нормализуется к lowercase"""
        user = UserBase(email="TEST@Example.COM", first_name="Ivan", last_name="Ivanov")
        assert user.email == "test@example.com"

    @pytest.mark.parametrize(
        "email",
        [
            "invalid-email",
            "",
            "no-at-sign.com",
            "@missing-local.com",
            "missing-domain@",
            "spaces @email.com",
        ],
    )
    def test_user_base_invalid_email(self, email):
        """Тест: невалидный email вызывает ошибку"""
        with pytest.raises(ValidationError) as exc_info:
            UserBase(email=email, first_name="Ivan", last_name="Ivanov")
        assert "email" in str(exc_info.value).lower()

    @pytest.mark.parametrize(
        "field, value, error_msg",
        [
            ("first_name", "", "Name cannot be empty"),
            ("first_name", "   ", "Name cannot be empty"),
            ("first_name", "I", "Name must be at least 2 characters long"),
            ("first_name", "A" * 51, "Name must be less than 50 characters"),
            ("last_name", "", "Name cannot be empty"),
            ("last_name", "A", "Name must be at least 2 characters long"),
        ],
    )
    def test_user_base_name_validation_errors(self, field, value, error_msg):
        """Тест: валидация имён (длина, пустые значения)"""
        data = {"email": "test@example.com", "first_name": "Ivan", "last_name": "Ivanov"}
        data[field] = value

        with pytest.raises(ValidationError) as exc_info:
            UserBase(**data)

        assert error_msg in str(exc_info.value)

    def test_user_base_name_strips_whitespace(self):
        """Тест: имена обрезаются от пробелов"""
        user = UserBase(email="test@example.com", first_name="  Ivan  ", last_name="  Ivanov  ")
        assert user.first_name == "Ivan"
        assert user.last_name == "Ivanov"

    def test_user_base_middle_name_strips_whitespace(self):
        """Тест: middle_name обрезается от пробелов"""
        user = UserBase(email="test@example.com", first_name="Ivan", last_name="Ivanov", middle_name="  Ivanovich  ")
        assert user.middle_name == "Ivanovich"

    def test_user_base_middle_name_empty_becomes_none(self):
        """Тест: middle_name с пробелами становится None"""
        user = UserBase(email="test@example.com", first_name="Ivan", last_name="Ivanov", middle_name="   ")
        assert user.middle_name is None

    def test_user_base_middle_name_too_short(self):
        """Тест: middle_name менее 2 символов вызывает ошибку"""
        with pytest.raises(ValidationError) as exc_info:
            UserBase(email="test@example.com", first_name="Ivan", last_name="Ivanov", middle_name="A")
        assert "at least 2 characters" in str(exc_info.value)


class TestUserCreate:
    """Тесты схемы создания пользователя"""

    def test_user_create_valid(self):
        """Тест: валидные данные для создания"""
        user = UserCreate(
            email="new@example.com",
            first_name="Petr",
            last_name="Petrov",
            middle_name="Petrovich",
            password="SecurePass123!",
        )
        assert user.email == "new@example.com"
        assert user.password == "SecurePass123!"

    @pytest.mark.parametrize(
        "password, error_msg",
        [
            ("short", "String should have at least 8 characters"),
            ("a", "String should have at least 8 characters"),
            ("nouppercase1!", "Password must contain at least one uppercase letter"),
            ("NOLOWERCASE1!", "Password must contain at least one lowercase letter"),
            ("NoDigitsHere!", "Password must contain at least one digit"),
            ("NoSpecial1", "Password must contain at least one special character"),
            ("a" * 129, "String should have at most 128 characters"),
            (None, "Field required"),
        ],
    )
    def test_user_create_password_validation_errors(self, password, error_msg):
        """Тест: невалидный пароль вызывает ошибку"""
        data = {
            "email": "test@example.com",
            "first_name": "Ivan",
            "last_name": "Ivanov",
        }
        if password is not None:
            data["password"] = password

        with pytest.raises(ValidationError) as exc_info:
            UserCreate(**data)

        assert error_msg in str(exc_info.value)

    def test_user_create_inherits_base_validators(self):
        """Тест: UserCreate наследует валидаторы UserBase"""
        with pytest.raises(ValidationError):
            UserCreate(email="test@example.com", first_name="A", last_name="Ivanov", password="SecurePass123!")

    def test_user_create_email_normalized(self):
        """Тест: email в UserCreate нормализуется к lowercase"""
        user = UserCreate(email="NEW@Example.COM", first_name="Ivan", last_name="Ivanov", password="SecurePass123!")
        assert user.email == "new@example.com"


class TestUserLogin:
    """Тесты схемы авторизации"""

    def test_user_login_valid(self):
        """Тест: валидные данные для входа"""
        login = UserLogin(email="user@example.com", password="SecurePass123!")
        assert login.email == "user@example.com"
        assert login.password == "SecurePass123!"

    def test_user_login_password_too_short(self):
        """Тест: пароль менее 8 символов"""
        with pytest.raises(ValidationError) as exc_info:
            UserLogin(email="user@example.com", password="short")
        assert "String should have at least 8 characters" in str(exc_info.value)

    def test_user_login_password_missing_uppercase(self):
        """Тест: пароль без заглавной буквы"""
        with pytest.raises(ValidationError) as exc_info:
            UserLogin(email="user@example.com", password="nouppercase1!")
        assert "uppercase" in str(exc_info.value).lower()

    def test_user_login_invalid_email(self):
        """Тест: невалидный email"""
        with pytest.raises(ValidationError):
            UserLogin(email="not-an-email", password="SecurePass123!")

    def test_user_login_email_normalized(self):
        """Тест: email нормализуется к lowercase"""
        login = UserLogin(email="USER@Example.COM", password="SecurePass123!")
        assert login.email == "user@example.com"
