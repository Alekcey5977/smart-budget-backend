"""
Unit-тесты для Pydantic-схем purposes_service.

Эти тесты НЕ зависят от БД, Redis, HTTP — только чистая валидация.
Паттерн: для каждого поля проверяем валидный ввод + каждое правило валидации.
"""
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from datetime import datetime, timedelta  # noqa: E402
from decimal import Decimal  # noqa: E402
from uuid import uuid4  # noqa: E402

import pytest  # noqa: E402
from pydantic import ValidationError  # noqa: E402

from app.schemas import PurposeCreate, PurposeResponse, PurposeUpdate  # noqa: E402


# ==================== PurposeCreate ====================

class TestPurposeCreate:
    """Тесты схемы создания цели."""

    def test_valid_data(self):
        """Валидные данные — схема создаётся без ошибок."""
        schema = PurposeCreate(
            title="Отпуск",
            deadline=datetime.now() + timedelta(days=30),
            total_amount=Decimal("100000"),
        )
        assert schema.title == "Отпуск"
        assert schema.total_amount == Decimal("100000")

    def test_total_amount_must_be_positive(self):
        """total_amount <= 0 -> ошибка валидации."""
        with pytest.raises(ValidationError) as exc_info:
            PurposeCreate(
                title="Тест",
                deadline=datetime.now() + timedelta(days=30),
                total_amount=Decimal("0"),
            )
        assert "total_amount" in str(exc_info.value)

    def test_total_amount_negative(self):
        """Отрицательная сумма -> ошибка валидации."""
        with pytest.raises(ValidationError):
            PurposeCreate(
                title="Тест",
                deadline=datetime.now() + timedelta(days=30),
                total_amount=Decimal("-100"),
            )

    def test_deadline_in_past_rejected(self):
        """Дедлайн в прошлом -> ошибка валидации."""
        with pytest.raises(ValidationError) as exc_info:
            PurposeCreate(
                title="Тест",
                deadline=datetime(2020, 1, 1),
                total_amount=Decimal("1000"),
            )
        assert "Дедлайн должен быть в будущем" in str(exc_info.value)

    def test_title_required(self):
        """Без title -> ошибка валидации."""
        with pytest.raises(ValidationError):
            PurposeCreate(
                deadline=datetime.now() + timedelta(days=30),
                total_amount=Decimal("1000"),
            )


# ==================== PurposeUpdate ====================

class TestPurposeUpdate:
    """Тесты схемы обновления цели."""

    def test_partial_update_title_only(self):
        """Можно обновить только title, остальное None."""
        schema = PurposeUpdate(title="Новое название")
        assert schema.title == "Новое название"
        assert schema.amount is None
        assert schema.total_amount is None
        assert schema.deadline is None

    def test_all_fields_none_is_valid(self):
        """Все поля None — валидно (проверка в роутере, не в схеме)."""
        schema = PurposeUpdate()
        assert schema.title is None

    def test_amount_cannot_be_negative(self):
        """Отрицательная сумма -> ошибка."""
        with pytest.raises(ValidationError):
            PurposeUpdate(amount=Decimal("-10"))

    def test_amount_greater_than_total_rejected(self):
        """amount > total_amount -> ошибка валидации."""
        with pytest.raises(ValidationError) as exc_info:
            PurposeUpdate(
                amount=Decimal("500"),
                total_amount=Decimal("100"),
            )
        assert "Накопленная сумма не может превышать целевую" in str(exc_info.value)

    def test_amount_equals_total_is_valid(self):
        """amount == total_amount -> валидно (цель выполнена на 100%)."""
        schema = PurposeUpdate(
            amount=Decimal("1000"),
            total_amount=Decimal("1000"),
        )
        assert schema.amount == schema.total_amount

    def test_deadline_in_past_rejected(self):
        """Дедлайн в прошлом -> ошибка."""
        with pytest.raises(ValidationError):
            PurposeUpdate(deadline=datetime(2020, 1, 1))

    def test_deadline_in_future_valid(self):
        """Дедлайн в будущем -> ок."""
        future = datetime.now() + timedelta(days=60)
        schema = PurposeUpdate(deadline=future)
        assert schema.deadline == future


# ==================== PurposeResponse ====================

class TestPurposeResponse:
    """Тесты схемы ответа."""

    def test_valid_response(self):
        """Корректная сериализация из словаря."""
        data = {
            "id": uuid4(),
            "user_id": 1,
            "title": "Отпуск",
            "deadline": datetime.now() + timedelta(days=30),
            "amount": Decimal("250.50"),
            "total_amount": Decimal("1000"),
            "created_at": datetime.now(),
            "updated_at": None,
        }
        schema = PurposeResponse(**data)
        assert schema.user_id == 1
        assert schema.amount == Decimal("250.50")

    def test_updated_at_optional(self):
        """updated_at может быть None (цель ещё не обновляли)."""
        data = {
            "id": uuid4(),
            "user_id": 1,
            "title": "Тест",
            "deadline": datetime.now() + timedelta(days=30),
            "amount": Decimal("0"),
            "total_amount": Decimal("1000"),
            "created_at": datetime.now(),
        }
        schema = PurposeResponse(**data)
        assert schema.updated_at is None
