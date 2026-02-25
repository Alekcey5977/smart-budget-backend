"""
Unit-тесты для логики прогресса целей (get_crossed_thresholds).

Чистая математика — без БД, Redis, HTTP.
Паттерн: тестируем каждый граничный случай отдельным тестом.
"""
import sys
from pathlib import Path
from decimal import Decimal

PROJECT_ROOT = Path(__file__).parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.utils import get_crossed_thresholds  # noqa: E402


class TestGetCrossedThresholds:
    """Тесты расчёта пересечённых порогов прогресса."""

    def test_cross_25_percent(self):
        """0% → 30% = пересечён порог 25%."""
        result = get_crossed_thresholds(0, 1000, 300, 1000)
        assert result == [25]

    def test_cross_25_and_50_percent(self):
        """0% → 60% = пересечены пороги 25% и 50%."""
        result = get_crossed_thresholds(0, 1000, 600, 1000)
        assert result == [25, 50]

    def test_cross_all_thresholds(self):
        """0% → 100% = все пороги пересечены."""
        result = get_crossed_thresholds(0, 1000, 1000, 1000)
        assert result == [25, 50, 80, 100]

    def test_cross_only_100(self):
        """80% → 100% = только порог 100%."""
        result = get_crossed_thresholds(800, 1000, 1000, 1000)
        assert result == [100]

    def test_no_threshold_crossed(self):
        """20% → 24% = ни один порог не пересечён."""
        result = get_crossed_thresholds(200, 1000, 240, 1000)
        assert result == []

    def test_same_progress_no_crossing(self):
        """50% → 50% = прогресс не изменился, порогов нет."""
        result = get_crossed_thresholds(500, 1000, 500, 1000)
        assert result == []

    def test_zero_total_amount_returns_empty(self):
        """total_amount = 0 → пустой список (деление на ноль)."""
        result = get_crossed_thresholds(0, 0, 100, 0)
        assert result == []

    def test_old_total_zero_returns_empty(self):
        """Старый total = 0 → пустой список."""
        result = get_crossed_thresholds(0, 0, 500, 1000)
        assert result == []

    def test_exact_threshold_value(self):
        """Ровно 25% = порог пересечён (включительно)."""
        result = get_crossed_thresholds(0, 1000, 250, 1000)
        assert result == [25]

    def test_just_below_threshold(self):
        """24.99% → не пересекает порог 25%."""
        result = get_crossed_thresholds(0, 10000, 2499, 10000)
        assert result == []

    def test_decimal_amounts(self):
        """Работает с Decimal (как в реальном коде)."""
        result = get_crossed_thresholds(
            Decimal("0"), Decimal("1000"),
            Decimal("500"), Decimal("1000")
        )
        assert result == [25, 50]

    def test_total_amount_changed(self):
        """Изменение total_amount тоже может пересечь порог.
        Было 500/2000=25%, стало 500/1000=50% → пересечён порог 50%.
        """
        result = get_crossed_thresholds(500, 2000, 500, 1000)
        assert 50 in result

    def test_progress_decreased_no_crossing(self):
        """Прогресс уменьшился (80% → 40%) → порогов не пересечено."""
        result = get_crossed_thresholds(800, 1000, 400, 1000)
        assert result == []