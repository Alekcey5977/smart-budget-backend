"""
Интеграционные тесты API endpoints purposes_service.

Используют тестовую SQLite БД + мок EventPublisher (из conftest.py).
Проверяют полный путь: HTTP-запрос -> роутер -> репозиторий -> БД -> ответ.

1. Каждый endpoint — отдельный класс
2. Happy path + все ошибочные сценарии
3. Проверяем и HTTP-код, и тело ответа
4. Проверяем вызовы EventPublisher через mock
"""

import sys
from datetime import datetime, timedelta
from decimal import Decimal
from pathlib import Path

from httpx import AsyncClient

PROJECT_ROOT = Path(__file__).parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


# ---------------------------------------------------------------------------
# Хелперы для создания тестовых данных
# ---------------------------------------------------------------------------
FUTURE_DATE = (datetime.now() + timedelta(days=90)).isoformat()
USER_ID = 1
OTHER_USER_ID = 999


def purpose_payload(title="Отпуск", total_amount="100000", deadline=None):
    """Генерирует валидный JSON для создания цели."""
    return {
        "title": title,
        "deadline": deadline or FUTURE_DATE,
        "total_amount": total_amount,
    }


def auth_headers(user_id: int = USER_ID):
    """Заголовок авторизации X-User-ID."""
    return {"X-User-ID": str(user_id)}


# ==================== Health Check ====================


class TestHealthCheck:
    async def test_health_returns_ok(self, client: AsyncClient):
        """GET /health -> 200, service: purposes-service."""
        response = await client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "purposes-service"


# ==================== POST /purpose/create ====================


class TestCreatePurpose:
    async def test_create_success(self, client: AsyncClient, mock_event_publisher):
        """Создание цели — 200, amount=0, событие опубликовано."""
        response = await client.post(
            "/purpose/create",
            json=purpose_payload(),
            headers=auth_headers(),
        )
        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "Отпуск"
        assert Decimal(data["total_amount"]) == Decimal("100000")
        assert Decimal(data["amount"]) == Decimal("0")
        assert data["user_id"] == USER_ID
        assert "id" in data

        # EventPublisher.publish вызван (purpose.created)
        mock_event_publisher.publish.assert_called()
        call_args = mock_event_publisher.publish.call_args[0][0]
        assert call_args.event_type == "purpose.created"

    async def test_create_without_user_id_header(self, client: AsyncClient):
        """Без X-User-ID -> 422."""
        response = await client.post(
            "/purpose/create",
            json=purpose_payload(),
        )
        assert response.status_code == 422

    async def test_create_with_invalid_total_amount(self, client: AsyncClient):
        """total_amount = 0 -> 422."""
        response = await client.post(
            "/purpose/create",
            json=purpose_payload(total_amount="0"),
            headers=auth_headers(),
        )
        assert response.status_code == 422

    async def test_create_with_past_deadline(self, client: AsyncClient):
        """Дедлайн в прошлом -> 422."""
        response = await client.post(
            "/purpose/create",
            json=purpose_payload(deadline="2020-01-01T00:00:00"),
            headers=auth_headers(),
        )
        assert response.status_code == 422


# ==================== GET /purpose/my ====================


class TestGetPurposes:
    async def test_empty_list(self, client: AsyncClient):
        """Нет целей -> пустой список."""
        response = await client.get(
            "/purpose/my",
            headers=auth_headers(user_id=777),
        )
        assert response.status_code == 200
        assert response.json() == []

    async def test_returns_user_purposes(self, client: AsyncClient):
        """Возвращает только свои цели."""
        # Создаём цель
        await client.post(
            "/purpose/create",
            json=purpose_payload(title="Моя цель"),
            headers=auth_headers(),
        )

        # Запрашиваем свои цели
        response = await client.get(
            "/purpose/my",
            headers=auth_headers(),
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 1
        assert any(p["title"] == "Моя цель" for p in data)

    async def test_does_not_return_other_user_purposes(self, client: AsyncClient):
        """Не возвращает чужие цели."""
        # Создаём цель для user_id=1
        await client.post(
            "/purpose/create",
            json=purpose_payload(title="Чужая цель"),
            headers=auth_headers(user_id=USER_ID),
        )

        # Запрашиваем от имени другого пользователя
        response = await client.get(
            "/purpose/my",
            headers=auth_headers(user_id=OTHER_USER_ID),
        )
        assert response.status_code == 200
        data = response.json()
        assert all(p["title"] != "Чужая цель" for p in data)

    async def test_missing_user_id_header(self, client: AsyncClient):
        """Без X-User-ID -> 422."""
        response = await client.get("/purpose/my")
        assert response.status_code == 422

    async def test_invalid_user_id_header(self, client: AsyncClient):
        """Нечисловой X-User-ID -> 400."""
        response = await client.get(
            "/purpose/my",
            headers={"X-User-ID": "not-a-number"},
        )
        assert response.status_code == 400
        assert "Invalid user ID" in response.json()["detail"]


# ==================== PUT /purpose/update/{id} ====================


class TestUpdatePurpose:
    async def _create_purpose(self, client: AsyncClient, user_id: int = USER_ID):
        """Хелпер: создаёт цель и возвращает её ID."""
        response = await client.post(
            "/purpose/create",
            json=purpose_payload(total_amount="1000"),
            headers=auth_headers(user_id),
        )
        return response.json()["id"]

    async def test_update_title(self, client: AsyncClient):
        """Обновление title — 200, title изменился."""
        purpose_id = await self._create_purpose(client)

        response = await client.put(
            f"/purpose/update/{purpose_id}",
            json={"title": "Новое название"},
            headers=auth_headers(),
        )
        assert response.status_code == 200
        assert response.json()["title"] == "Новое название"

    async def test_update_amount_triggers_progress_event(self, client: AsyncClient, mock_event_publisher):
        """Обновление amount с пересечением порога -> событие progress."""
        purpose_id = await self._create_purpose(client)

        # Сбрасываем счётчик вызовов после create
        mock_event_publisher.publish.reset_mock()

        # Обновляем amount до 300 из 1000 (30%) -> пересекаем порог 25%
        response = await client.put(
            f"/purpose/update/{purpose_id}",
            json={"amount": "300"},
            headers=auth_headers(),
        )
        assert response.status_code == 200

        # Проверяем что событие progress опубликовано
        calls = mock_event_publisher.publish.call_args_list
        progress_events = [c for c in calls if c[0][0].event_type == "purpose.progress"]
        assert len(progress_events) >= 1

    async def test_update_nonexistent_purpose(self, client: AsyncClient):
        """Несуществующий ID -> 404."""
        fake_id = "00000000-0000-0000-0000-000000000000"
        response = await client.put(
            f"/purpose/update/{fake_id}",
            json={"title": "Тест"},
            headers=auth_headers(),
        )
        assert response.status_code == 404

    async def test_update_other_user_purpose(self, client: AsyncClient):
        """Обновление чужой цели -> 404."""
        purpose_id = await self._create_purpose(client, user_id=USER_ID)

        response = await client.put(
            f"/purpose/update/{purpose_id}",
            json={"title": "Хакер"},
            headers=auth_headers(user_id=OTHER_USER_ID),
        )
        assert response.status_code == 404

    async def test_update_empty_body(self, client: AsyncClient):
        """Пустое тело запроса -> 400 'No fields to update'."""
        purpose_id = await self._create_purpose(client)

        response = await client.put(
            f"/purpose/update/{purpose_id}",
            json={},
            headers=auth_headers(),
        )
        assert response.status_code == 400
        assert "No fields to update" in response.json()["detail"]

    async def test_update_deadline(self, client: AsyncClient):
        """Обновление deadline — 200, deadline изменился."""
        purpose_id = await self._create_purpose(client)
        new_deadline = (datetime.now() + timedelta(days=180)).isoformat()

        response = await client.put(
            f"/purpose/update/{purpose_id}",
            json={"deadline": new_deadline},
            headers=auth_headers(),
        )
        assert response.status_code == 200

    async def test_update_missing_user_id_header(self, client: AsyncClient):
        """Без X-User-ID -> 422."""
        purpose_id = await self._create_purpose(client)
        response = await client.put(
            f"/purpose/update/{purpose_id}",
            json={"title": "Тест"},
        )
        assert response.status_code == 422

    async def test_update_invalid_schema_amount_exceeds_total(self, client: AsyncClient):
        """amount > total_amount в одном запросе -> 422 (валидация схемы)."""
        purpose_id = await self._create_purpose(client)

        response = await client.put(
            f"/purpose/update/{purpose_id}",
            json={"amount": "9999", "total_amount": "100"},
            headers=auth_headers(),
        )
        assert response.status_code == 422


# ==================== DELETE /purpose/delete/{id} ====================


class TestDeletePurpose:
    async def _create_purpose(self, client: AsyncClient, user_id: int = USER_ID):
        """Хелпер: создаёт цель и возвращает её ID."""
        response = await client.post(
            "/purpose/create",
            json=purpose_payload(),
            headers=auth_headers(user_id),
        )
        return response.json()["id"]

    async def test_delete_success(self, client: AsyncClient, mock_event_publisher):
        """Удаление цели — 200, событие опубликовано."""
        purpose_id = await self._create_purpose(client)

        mock_event_publisher.publish.reset_mock()

        response = await client.delete(
            f"/purpose/delete/{purpose_id}",
            headers=auth_headers(),
        )
        assert response.status_code == 200

        # Проверяем что событие purpose.deleted опубликовано
        calls = mock_event_publisher.publish.call_args_list
        delete_events = [c for c in calls if c[0][0].event_type == "purpose.deleted"]
        assert len(delete_events) == 1

    async def test_delete_nonexistent(self, client: AsyncClient):
        """Несуществующий ID -> 404."""
        fake_id = "00000000-0000-0000-0000-000000000000"
        response = await client.delete(
            f"/purpose/delete/{fake_id}",
            headers=auth_headers(),
        )
        assert response.status_code == 404

    async def test_delete_other_user_purpose(self, client: AsyncClient):
        """Удаление чужой цели -> 404."""
        purpose_id = await self._create_purpose(client, user_id=USER_ID)

        response = await client.delete(
            f"/purpose/delete/{purpose_id}",
            headers=auth_headers(user_id=OTHER_USER_ID),
        )
        assert response.status_code == 404

    async def test_delete_then_get_returns_empty(self, client: AsyncClient):
        """После удаления цель не возвращается в списке."""
        purpose_id = await self._create_purpose(client)

        # Удаляем
        await client.delete(
            f"/purpose/delete/{purpose_id}",
            headers=auth_headers(),
        )

        # Проверяем что пропала из списка
        response = await client.get(
            "/purpose/my",
            headers=auth_headers(),
        )
        data = response.json()
        assert all(p["id"] != purpose_id for p in data)

    async def test_delete_missing_user_id_header(self, client: AsyncClient):
        """Без X-User-ID -> 422."""
        purpose_id = await self._create_purpose(client)
        response = await client.delete(f"/purpose/delete/{purpose_id}")
        assert response.status_code == 422
