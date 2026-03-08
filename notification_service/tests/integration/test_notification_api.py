import sys
from pathlib import Path
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

PROJECT_ROOT = Path(__file__).parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.repository.notification_repository import NotificationRepository  # noqa: E402
from app.schemas import NotificationCreate  # noqa: E402


# ---------------------------------------------------------------------------
# Хелперы для создания тестовых данных
# ---------------------------------------------------------------------------
USER_ID = 1
OTHER_USER_ID = 999


def auth_headers(user_id: int = USER_ID) -> dict:
    """Заголовок авторизации X-User-ID."""
    return {"X-User-ID": str(user_id)}


async def create_notification(
    db_session: AsyncSession,
    user_id: int = USER_ID,
    title: str = "Тест",
    body: str = "Тело уведомления",
):
    """Создаёт уведомление в БД напрямую (нет POST-эндпоинта в API)."""
    repo = NotificationRepository(db_session)
    return await repo.create_notification(
        NotificationCreate(user_id=user_id, title=title, body=body)
    )


# ==================== Health Check ====================

class TestHealthCheck:

    async def test_health_returns_ok(self, client: AsyncClient):
        """GET /health → 200, service: notification-service."""
        response = await client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "notification-service"


# ==================== GET /notifications/user/me ====================

class TestGetNotifications:

    async def test_empty_list(self, client: AsyncClient, db_session: AsyncSession):
        """Нет уведомлений у пользователя → пустой список."""
        response = await client.get(
            "/notifications/user/me",
            headers=auth_headers(user_id=777),
        )
        assert response.status_code == 200
        assert response.json() == []

    async def test_returns_user_notifications(self, client: AsyncClient, db_session: AsyncSession):
        """Возвращает только свои уведомления."""
        await create_notification(db_session, title="Моё уведомление")

        response = await client.get("/notifications/user/me", headers=auth_headers())
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 1
        assert any(n["title"] == "Моё уведомление" for n in data)

    async def test_does_not_return_other_user_notifications(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """Не возвращает чужие уведомления."""
        await create_notification(db_session, user_id=USER_ID, title="Чужое")

        response = await client.get(
            "/notifications/user/me",
            headers=auth_headers(user_id=OTHER_USER_ID),
        )
        assert response.status_code == 200
        data = response.json()
        assert all(n["title"] != "Чужое" for n in data)

    async def test_pagination_limit(self, client: AsyncClient, db_session: AsyncSession):
        """limit=1 → возвращается не больше 1 уведомления."""
        for i in range(3):
            await create_notification(db_session, title=f"Уведомление {i}")

        response = await client.get(
            "/notifications/user/me",
            headers=auth_headers(),
            params={"limit": 1},
        )
        assert response.status_code == 200
        assert len(response.json()) <= 1

    async def test_pagination_skip(self, client: AsyncClient, db_session: AsyncSession):
        """skip=1000 → пустой список."""
        await create_notification(db_session)

        response = await client.get(
            "/notifications/user/me",
            headers=auth_headers(),
            params={"skip": 1000},
        )
        assert response.status_code == 200
        assert response.json() == []

    async def test_missing_user_id_header(self, client: AsyncClient):
        """Без X-User-ID → 422."""
        response = await client.get("/notifications/user/me")
        assert response.status_code == 422

    async def test_invalid_user_id_header(self, client: AsyncClient):
        """Нечисловой X-User-ID → 400."""
        response = await client.get(
            "/notifications/user/me",
            headers={"X-User-ID": "not-a-number"},
        )
        assert response.status_code == 400
        assert "Invalid user ID" in response.json()["detail"]



# ==================== GET /notifications/user/me/unread/count ====================

class TestGetUnreadCount:

    async def test_returns_zero_when_no_notifications(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """Нет уведомлений → count=0."""
        response = await client.get(
            "/notifications/user/me/unread/count",
            headers=auth_headers(user_id=888),
        )
        assert response.status_code == 200
        assert response.json()["count"] == 0

    async def test_returns_correct_unread_count(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """Создали 2 непрочитанных уведомления → count=2."""
        await create_notification(db_session, user_id=2)
        await create_notification(db_session, user_id=2)

        response = await client.get(
            "/notifications/user/me/unread/count",
            headers=auth_headers(user_id=2),
        )
        assert response.status_code == 200
        assert response.json()["count"] == 2

    async def test_missing_user_id_header(self, client: AsyncClient):
        """Без X-User-ID → 422."""
        response = await client.get("/notifications/user/me/unread/count")
        assert response.status_code == 422

    async def test_unread_count_decreases_after_mark_read(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """Прочитанное уведомление не считается непрочитанным."""
        notif = await create_notification(db_session, user_id=10)
        await client.post(
            f"/notifications/{notif.id}/mark-as-read",
            headers=auth_headers(10),
        )
        response = await client.get(
            "/notifications/user/me/unread/count",
            headers=auth_headers(10),
        )
        assert response.status_code == 200
        assert response.json()["count"] == 0


# ==================== GET /notifications/{id} ====================

class TestGetNotificationById:

    async def test_returns_notification(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """Существующее уведомление → 200 с данными."""
        notif = await create_notification(db_session, title="По ID")

        response = await client.get(f"/notifications/{notif.id}")
        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "По ID"
        assert str(notif.id) == data["id"]

    async def test_returns_404_for_nonexistent(self, client: AsyncClient):
        """Несуществующий ID → 404."""
        fake_id = "00000000-0000-0000-0000-000000000000"
        response = await client.get(f"/notifications/{fake_id}")
        assert response.status_code == 404

    async def test_no_user_auth_required(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """GET /notifications/{id} не требует X-User-ID (любой может получить по ID)."""
        notif = await create_notification(db_session)
        response = await client.get(f"/notifications/{notif.id}")
        assert response.status_code == 200


# ==================== POST /notifications/{id}/mark-as-read ====================

class TestMarkAsRead:

    async def test_marks_notification_as_read(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """Отметить уведомление как прочитанное → success."""
        notif = await create_notification(db_session)

        response = await client.post(
            f"/notifications/{notif.id}/mark-as-read",
            headers=auth_headers(),
        )
        assert response.status_code == 200
        assert response.json()["status"] == "success"

    async def test_404_for_nonexistent(self, client: AsyncClient):
        """Несуществующий ID → 404."""
        fake_id = "00000000-0000-0000-0000-000000000000"
        response = await client.post(
            f"/notifications/{fake_id}/mark-as-read",
            headers=auth_headers(),
        )
        assert response.status_code == 404

    async def test_404_for_other_user_notification(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """Отмечаем чужое уведомление → 404 (изоляция по user_id)."""
        notif = await create_notification(db_session, user_id=USER_ID)

        response = await client.post(
            f"/notifications/{notif.id}/mark-as-read",
            headers=auth_headers(user_id=OTHER_USER_ID),
        )
        assert response.status_code == 404

    async def test_missing_user_id_header(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """Без X-User-ID → 422."""
        notif = await create_notification(db_session)
        response = await client.post(f"/notifications/{notif.id}/mark-as-read")
        assert response.status_code == 422


# ==================== POST /notifications/mark-all-as-read ====================

class TestMarkAllAsRead:

    async def test_marks_all_as_read(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """Отметить все как прочитанные → success."""
        await create_notification(db_session)
        await create_notification(db_session)

        response = await client.post(
            "/notifications/mark-all-as-read",
            headers=auth_headers(),
        )
        assert response.status_code == 200
        assert response.json()["status"] == "success"

    async def test_works_when_no_notifications(self, client: AsyncClient):
        """Нет уведомлений — не падает."""
        response = await client.post(
            "/notifications/mark-all-as-read",
            headers=auth_headers(user_id=555),
        )
        assert response.status_code == 200

    async def test_missing_user_id_header(self, client: AsyncClient):
        """Без X-User-ID → 422."""
        response = await client.post("/notifications/mark-all-as-read")
        assert response.status_code == 422


# ==================== DELETE /notifications/{id} ====================

class TestDeleteNotification:

    async def test_delete_success(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """Удаление своего уведомления → success."""
        notif = await create_notification(db_session)

        response = await client.delete(
            f"/notifications/{notif.id}",
            headers=auth_headers(),
        )
        assert response.status_code == 200
        assert response.json()["status"] == "success"

    async def test_delete_then_not_found(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """После удаления уведомление недоступно по ID."""
        notif = await create_notification(db_session)
        notif_id = str(notif.id)

        await client.delete(f"/notifications/{notif_id}", headers=auth_headers())

        response = await client.get(f"/notifications/{notif_id}")
        assert response.status_code == 404

    async def test_404_for_nonexistent(self, client: AsyncClient):
        """Несуществующий ID → 404."""
        fake_id = "00000000-0000-0000-0000-000000000000"
        response = await client.delete(
            f"/notifications/{fake_id}",
            headers=auth_headers(),
        )
        assert response.status_code == 404

    async def test_404_for_other_user_notification(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """Удаление чужого уведомления → 404."""
        notif = await create_notification(db_session, user_id=USER_ID)

        response = await client.delete(
            f"/notifications/{notif.id}",
            headers=auth_headers(user_id=OTHER_USER_ID),
        )
        assert response.status_code == 404

    async def test_missing_user_id_header(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """Без X-User-ID → 422."""
        notif = await create_notification(db_session)
        response = await client.delete(f"/notifications/{notif.id}")
        assert response.status_code == 422
