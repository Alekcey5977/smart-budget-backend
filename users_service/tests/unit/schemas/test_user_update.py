import pytest
from pydantic import ValidationError

from users_service.app.schemas import UserUpdate


class TestUserUpdate:
    """Тесты схемы обновления пользователя"""

    def test_user_update_single_field(self):
        """Тест: обновление одного поля"""
        update = UserUpdate(first_name="NewName")
        assert update.first_name == "NewName"
        assert update.last_name is None
        assert update.middle_name is None

    def test_user_update_multiple_fields(self):
        """Тест: обновление нескольких полей"""
        update = UserUpdate(first_name="New", last_name="NewLast")
        assert update.first_name == "New"
        assert update.last_name == "NewLast"
        assert update.middle_name is None

    def test_user_update_all_fields(self):
        """Тест: обновление всех полей"""
        update = UserUpdate(first_name="New", last_name="NewLast", middle_name="NewMiddle")
        assert update.first_name == "New"
        assert update.last_name == "NewLast"
        assert update.middle_name == "NewMiddle"

    def test_user_update_no_fields_raises_error(self):
        """Тест: обновление без полей вызывает ошибку"""
        with pytest.raises(ValidationError) as exc_info:
            UserUpdate()
        assert "At least one field must be provided" in str(exc_info.value)

    def test_user_update_all_none_raises_error(self):
        """Тест: все поля None вызывают ошибку"""
        with pytest.raises(ValidationError) as exc_info:
            UserUpdate(first_name=None, last_name=None, middle_name=None)
        assert "At least one field must be provided" in str(exc_info.value)

    def test_user_update_middle_name_empty_string(self):
        """Тест: middle_name='' означает удаление (возвращает '')"""
        update = UserUpdate(middle_name="")
        assert update.middle_name == ""

    def test_user_update_middle_name_whitespace_only(self):
        """Тест: middle_name с пробелами становится пустой строкой"""
        update = UserUpdate(middle_name="   ")
        assert update.middle_name == ""

    def test_user_update_middle_name_none_with_other_field(self):
        """Тест: middle_name=None допустим, если есть другие поля"""
        update = UserUpdate(first_name="New", middle_name=None)
        assert update.first_name == "New"
        assert update.middle_name is None

    def test_user_update_name_strips_whitespace(self):
        """Тест: имена обрезаются от пробелов"""
        update = UserUpdate(first_name="  NewName  ")
        assert update.first_name == "NewName"

    @pytest.mark.parametrize(
        "field, value, error_msg",
        [
            ("first_name", "", "Name cannot be empty"),
            ("first_name", "   ", "Name cannot be empty"),
            ("first_name", "A", "Name must be at least 2 characters long"),
            ("last_name", "A" * 51, "Name must be less than 50 characters"),
            ("middle_name", "A", "Middle name must be at least 2 characters long"),
        ],
    )
    def test_user_update_validation_errors(self, field, value, error_msg):
        """Тест: ошибки валидации в UserUpdate"""
        data = {field: value}

        with pytest.raises(ValidationError) as exc_info:
            UserUpdate(**data)

        assert error_msg in str(exc_info.value)

    def test_user_update_middle_name_valid(self):
        """Тест: валидное middle_name"""
        update = UserUpdate(middle_name="Ivanovich")
        assert update.middle_name == "Ivanovich"

    def test_user_update_middle_name_too_long(self):
        """Тест: middle_name слишком длинный"""
        with pytest.raises(ValidationError):
            UserUpdate(middle_name="A" * 51)
