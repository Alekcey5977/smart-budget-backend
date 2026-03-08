"""
Интеграционные тесты для эндпоинтов /notifications/*.

Все эндпоинты требуют JWT — get_current_user переопределяется через фикстуру `client`.
Downstream notification-service мокается через patch("app.routers.notifications.httpx.AsyncClient").
"""
import pytest
from unittest.mock import AsyncMock, patch

from tests.conftest import make_mock_http_response, USER_ID

NOTIF_ID = "550e8400-e29b-41d4-a716-446655440000"

MOCK_NOTIFICATION = {
    "id": NOTIF_ID,
    "user_id": 1,
    "title": "Test Notification",
    "body": "Test body",
    "is_read": False,
    "created_at": "2026-01-21T10:30:00",
}

MOCK_MARK_RESPONSE = {"status": "success", "message": "Notification marked as read"}


# ──────────────────────────────────────────────────────────────
# GET /notifications/user/me
# ──────────────────────────────────────────────────────────────
class TestGetUserNotifications:
    async def test_get_notifications_success(self, client):
        with patch("app.routers.notifications.httpx.AsyncClient") as MockClient:
            mock_http = AsyncMock()
            MockClient.return_value.__aenter__.return_value = mock_http
            mock_http.get.return_value = make_mock_http_response(
                200, json_data=[MOCK_NOTIFICATION]
            )

            response = await client.get("/notifications/user/me")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert data[0]["id"] == NOTIF_ID

    async def test_get_notifications_passes_user_id(self, client):
        with patch("app.routers.notifications.httpx.AsyncClient") as MockClient:
            mock_http = AsyncMock()
            MockClient.return_value.__aenter__.return_value = mock_http
            mock_http.get.return_value = make_mock_http_response(200, json_data=[])

            await client.get("/notifications/user/me")

        call_kwargs = mock_http.get.call_args.kwargs
        assert call_kwargs["headers"]["X-User-ID"] == str(USER_ID)

    async def test_get_notifications_service_unavailable(self, client):
        import httpx as httpx_module

        with patch("app.routers.notifications.httpx.AsyncClient") as MockClient:
            mock_http = AsyncMock()
            MockClient.return_value.__aenter__.return_value = mock_http
            mock_http.get.side_effect = httpx_module.ConnectError("Connection refused")

            response = await client.get("/notifications/user/me")

        assert response.status_code == 503

    async def test_get_notifications_requires_auth(self, client_no_auth):
        response = await client_no_auth.get("/notifications/user/me")
        assert response.status_code == 401


# ──────────────────────────────────────────────────────────────
# GET /notifications/user/me/unread/count
# ──────────────────────────────────────────────────────────────
class TestGetUnreadCount:
    async def test_get_unread_count_success(self, client):
        with patch("app.routers.notifications.httpx.AsyncClient") as MockClient:
            mock_http = AsyncMock()
            MockClient.return_value.__aenter__.return_value = mock_http
            mock_http.get.return_value = make_mock_http_response(
                200, json_data={"count": 5}
            )

            response = await client.get("/notifications/user/me/unread/count")

        assert response.status_code == 200
        assert response.json()["count"] == 5

    async def test_get_unread_count_requires_auth(self, client_no_auth):
        response = await client_no_auth.get("/notifications/user/me/unread/count")
        assert response.status_code == 401


# ──────────────────────────────────────────────────────────────
# GET /notifications/{id}
# ──────────────────────────────────────────────────────────────
class TestGetNotificationById:
    async def test_get_by_id_success(self, client):
        with patch("app.routers.notifications.httpx.AsyncClient") as MockClient:
            mock_http = AsyncMock()
            MockClient.return_value.__aenter__.return_value = mock_http
            mock_http.get.return_value = make_mock_http_response(
                200, json_data=MOCK_NOTIFICATION
            )

            response = await client.get(f"/notifications/{NOTIF_ID}")

        assert response.status_code == 200
        assert response.json()["id"] == NOTIF_ID

    async def test_get_by_id_not_found(self, client):
        with patch("app.routers.notifications.httpx.AsyncClient") as MockClient:
            mock_http = AsyncMock()
            MockClient.return_value.__aenter__.return_value = mock_http
            mock_http.get.return_value = make_mock_http_response(
                404, json_data={"detail": "Not found"}
            )

            response = await client.get(f"/notifications/{NOTIF_ID}")

        assert response.status_code == 404


# ──────────────────────────────────────────────────────────────
# POST /notifications/{id}/mark-as-read
# ──────────────────────────────────────────────────────────────
class TestMarkAsRead:
    async def test_mark_as_read_success(self, client):
        with patch("app.routers.notifications.httpx.AsyncClient") as MockClient:
            mock_http = AsyncMock()
            MockClient.return_value.__aenter__.return_value = mock_http
            mock_http.post.return_value = make_mock_http_response(
                200, json_data=MOCK_MARK_RESPONSE
            )

            response = await client.post(f"/notifications/{NOTIF_ID}/mark-as-read")

        assert response.status_code == 200
        assert response.json()["status"] == "success"

    async def test_mark_as_read_passes_user_id(self, client):
        with patch("app.routers.notifications.httpx.AsyncClient") as MockClient:
            mock_http = AsyncMock()
            MockClient.return_value.__aenter__.return_value = mock_http
            mock_http.post.return_value = make_mock_http_response(
                200, json_data=MOCK_MARK_RESPONSE
            )

            await client.post(f"/notifications/{NOTIF_ID}/mark-as-read")

        call_kwargs = mock_http.post.call_args.kwargs
        assert call_kwargs["headers"]["X-User-ID"] == str(USER_ID)

    async def test_mark_as_read_not_found(self, client):
        with patch("app.routers.notifications.httpx.AsyncClient") as MockClient:
            mock_http = AsyncMock()
            MockClient.return_value.__aenter__.return_value = mock_http
            mock_http.post.return_value = make_mock_http_response(
                404, json_data={"detail": "Not found"}
            )

            response = await client.post(f"/notifications/{NOTIF_ID}/mark-as-read")

        assert response.status_code == 404


# ──────────────────────────────────────────────────────────────
# POST /notifications/mark-all-as-read
# ──────────────────────────────────────────────────────────────
class TestMarkAllAsRead:
    async def test_mark_all_success(self, client):
        upstream_data = {"status": "success", "message": "All notifications marked as read"}
        with patch("app.routers.notifications.httpx.AsyncClient") as MockClient:
            mock_http = AsyncMock()
            MockClient.return_value.__aenter__.return_value = mock_http
            mock_http.post.return_value = make_mock_http_response(200, json_data=upstream_data)

            response = await client.post("/notifications/mark-all-as-read")

        assert response.status_code == 200
        assert response.json()["status"] == "success"

    async def test_mark_all_requires_auth(self, client_no_auth):
        response = await client_no_auth.post("/notifications/mark-all-as-read")
        assert response.status_code == 401


# ──────────────────────────────────────────────────────────────
# DELETE /notifications/{id}
# ──────────────────────────────────────────────────────────────
class TestDeleteNotification:
    async def test_delete_success(self, client):
        upstream_data = {"status": "success", "message": "Notification deleted"}
        with patch("app.routers.notifications.httpx.AsyncClient") as MockClient:
            mock_http = AsyncMock()
            MockClient.return_value.__aenter__.return_value = mock_http
            mock_http.delete.return_value = make_mock_http_response(200, json_data=upstream_data)

            response = await client.delete(f"/notifications/{NOTIF_ID}")

        assert response.status_code == 200

    async def test_delete_not_found(self, client):
        with patch("app.routers.notifications.httpx.AsyncClient") as MockClient:
            mock_http = AsyncMock()
            MockClient.return_value.__aenter__.return_value = mock_http
            mock_http.delete.return_value = make_mock_http_response(
                404, json_data={"detail": "Not found"}
            )

            response = await client.delete(f"/notifications/{NOTIF_ID}")

        assert response.status_code == 404

    async def test_delete_requires_auth(self, client_no_auth):
        response = await client_no_auth.delete(f"/notifications/{NOTIF_ID}")
        assert response.status_code == 401
