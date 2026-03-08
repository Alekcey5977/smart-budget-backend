import sys
from pathlib import Path
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

PROJECT_ROOT = Path(__file__).parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.repository.history_repository import HistoryRepository  # noqa: E402
from app.schemas import HistoryEntryCreate  # noqa: E402


# ---------------------------------------------------------------------------
# Хелперы
# ---------------------------------------------------------------------------
USER_ID = 1
OTHER_USER_ID = 999


def auth_headers(user_id: int = USER_ID) -> dict:
    """Заголовок авторизации X-User-ID."""
    return {"X-User-ID": str(user_id)}


async def create_entry(
    db_session: AsyncSession,
    user_id: int = USER_ID,
    title: str = "Тест",
    body: str = "Тело записи истории",
):
    """Создаёт запись истории в БД напрямую через репозиторий."""
    repo = HistoryRepository(db_session)
    return await repo.create_entry(
        HistoryEntryCreate(user_id=user_id, title=title, body=body)
    )


# ==================== Health Check ====================

class TestHealthCheck:

    async def test_health_returns_ok(self, client: AsyncClient):
        """GET /health → 200, service: history-service."""
        response = await client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "history-service"


# ==================== GET /history/user/me ====================

class TestGetUserHistory:

    async def test_empty_list(self, client: AsyncClient, db_session: AsyncSession):
        """Нет записей у пользователя → пустой список."""
        response = await client.get(
            "/history/user/me",
            headers=auth_headers(user_id=777),
        )
        assert response.status_code == 200
        assert response.json() == []

    async def test_returns_user_entries(self, client: AsyncClient, db_session: AsyncSession):
        """Возвращает только свои записи."""
        await create_entry(db_session, title="Моя запись")

        response = await client.get("/history/user/me", headers=auth_headers())
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 1
        assert any(e["title"] == "Моя запись" for e in data)

    async def test_does_not_return_other_user_entries(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """Не возвращает чужие записи."""
        await create_entry(db_session, user_id=USER_ID, title="Чужая запись")

        response = await client.get(
            "/history/user/me",
            headers=auth_headers(user_id=OTHER_USER_ID),
        )
        assert response.status_code == 200
        data = response.json()
        assert all(e["title"] != "Чужая запись" for e in data)

    async def test_pagination_limit(self, client: AsyncClient, db_session: AsyncSession):
        """limit=1 → возвращается не больше 1 записи."""
        for i in range(3):
            await create_entry(db_session, title=f"Запись {i}")

        response = await client.get(
            "/history/user/me",
            headers=auth_headers(),
            params={"limit": 1},
        )
        assert response.status_code == 200
        assert len(response.json()) <= 1

    async def test_pagination_skip(self, client: AsyncClient, db_session: AsyncSession):
        """skip=1000 → пустой список."""
        await create_entry(db_session)

        response = await client.get(
            "/history/user/me",
            headers=auth_headers(),
            params={"skip": 1000},
        )
        assert response.status_code == 200
        assert response.json() == []

    async def test_missing_user_id_header(self, client: AsyncClient):
        """Без X-User-ID → 422."""
        response = await client.get("/history/user/me")
        assert response.status_code == 422

    async def test_invalid_user_id_header(self, client: AsyncClient):
        """Нечисловой X-User-ID → 400."""
        response = await client.get(
            "/history/user/me",
            headers={"X-User-ID": "not-a-number"},
        )
        assert response.status_code == 400
        assert "Invalid user ID" in response.json()["detail"]


# ==================== GET /history/{entry_id} ====================

class TestGetEntryById:

    async def test_returns_entry(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """Существующая запись → 200 с данными."""
        entry = await create_entry(db_session, title="По ID")

        response = await client.get(f"/history/{entry.id}")
        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "По ID"
        assert str(entry.id) == data["id"]

    async def test_returns_404_for_nonexistent(self, client: AsyncClient):
        """Несуществующий ID → 404."""
        fake_id = "00000000-0000-0000-0000-000000000000"
        response = await client.get(f"/history/{fake_id}")
        assert response.status_code == 404

    async def test_no_user_auth_required(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """GET /history/{id} не требует X-User-ID."""
        entry = await create_entry(db_session)
        response = await client.get(f"/history/{entry.id}")
        assert response.status_code == 200


# ==================== DELETE /history/{entry_id} ====================

class TestDeleteEntry:

    async def test_delete_success(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """Удаление своей записи → success."""
        entry = await create_entry(db_session)

        response = await client.delete(
            f"/history/{entry.id}",
            headers=auth_headers(),
        )
        assert response.status_code == 200
        assert response.json()["status"] == "success"

    async def test_delete_then_not_found(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """После удаления запись недоступна по ID."""
        entry = await create_entry(db_session)
        entry_id = str(entry.id)

        await client.delete(f"/history/{entry_id}", headers=auth_headers())

        response = await client.get(f"/history/{entry_id}")
        assert response.status_code == 404

    async def test_404_for_nonexistent(self, client: AsyncClient):
        """Несуществующий ID → 404."""
        fake_id = "00000000-0000-0000-0000-000000000000"
        response = await client.delete(
            f"/history/{fake_id}",
            headers=auth_headers(),
        )
        assert response.status_code == 404

    async def test_404_for_other_user_entry(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """Удаление чужой записи → 404 (изоляция по user_id)."""
        entry = await create_entry(db_session, user_id=USER_ID)

        response = await client.delete(
            f"/history/{entry.id}",
            headers=auth_headers(user_id=OTHER_USER_ID),
        )
        assert response.status_code == 404

    async def test_missing_user_id_header(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """Без X-User-ID → 422."""
        entry = await create_entry(db_session)
        response = await client.delete(f"/history/{entry.id}")
        assert response.status_code == 422
