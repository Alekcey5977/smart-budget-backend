"""
E2E tests for /notifications/* endpoints.
Уведомления создаются через Redis pub/sub (async pipeline).
Добавление банковского счёта генерирует уведомление.
Используем polling вместо фиксированного sleep.
"""
import asyncio

import pytest


async def _poll_notifications(http_client, headers, min_count=1, retries=10, delay=0.5):
    """Ждём появления уведомлений с polling (максимум retries * delay секунд)."""
    for _ in range(retries):
        resp = http_client.get("/notifications/user/me", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        if len(data) >= min_count:
            return data
        await asyncio.sleep(delay)
    resp = http_client.get("/notifications/user/me", headers=headers)
    return resp.json()


class TestGetNotifications:
    async def test_notifications_appear_after_bank_account_add(
        self, http_client, auth_headers, bank_account
    ):
        _, headers = auth_headers
        notifications = await _poll_notifications(http_client, headers)
        assert len(notifications) > 0, (
            "Expected at least one notification after adding a bank account"
        )

    async def test_notification_has_required_fields(
        self, http_client, auth_headers, bank_account
    ):
        _, headers = auth_headers
        notifications = await _poll_notifications(http_client, headers)
        if not notifications:
            pytest.skip("No notifications arrived in time")

        notif = notifications[0]
        assert "id" in notif
        assert "title" in notif
        assert "body" in notif
        assert "is_read" in notif
        assert "created_at" in notif

    def test_get_notifications_without_token_returns_401(self, http_client):
        resp = http_client.get("/notifications/user/me")
        assert resp.status_code == 401


class TestUnreadCount:
    async def test_unread_count_returns_valid_response(
        self, http_client, auth_headers, bank_account
    ):
        _, headers = auth_headers
        await asyncio.sleep(1)  # ждём propagation

        resp = http_client.get(
            "/notifications/user/me/unread/count", headers=headers
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "count" in data
        assert isinstance(data["count"], int)
        assert data["count"] >= 0

    def test_unread_count_without_token_returns_401(self, http_client):
        resp = http_client.get("/notifications/user/me/unread/count")
        assert resp.status_code == 401


class TestMarkAsRead:
    async def test_mark_notification_as_read(
        self, http_client, auth_headers, bank_account
    ):
        _, headers = auth_headers
        notifications = await _poll_notifications(http_client, headers)

        if not notifications:
            pytest.skip("No notifications available to mark as read")

        notif_id = notifications[0]["id"]
        resp = http_client.post(
            f"/notifications/{notif_id}/mark-as-read",
            headers=headers,
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "success"

    async def test_mark_all_as_read_sets_count_to_zero(
        self, http_client, auth_headers, bank_account
    ):
        _, headers = auth_headers
        await asyncio.sleep(1)

        resp = http_client.post(
            "/notifications/mark-all-as-read", headers=headers
        )
        assert resp.status_code == 200

        count_resp = http_client.get(
            "/notifications/user/me/unread/count", headers=headers
        )
        assert count_resp.status_code == 200
        assert count_resp.json()["count"] == 0

    def test_mark_as_read_without_token_returns_401(self, http_client):
        resp = http_client.post(
            "/notifications/00000000-0000-0000-0000-000000000000/mark-as-read"
        )
        assert resp.status_code == 401


class TestDeleteNotification:
    async def test_delete_own_notification(
        self, http_client, auth_headers, bank_account
    ):
        _, headers = auth_headers
        notifications = await _poll_notifications(http_client, headers)

        if not notifications:
            pytest.skip("No notifications to delete")

        notif_id = notifications[0]["id"]
        resp = http_client.delete(
            f"/notifications/{notif_id}", headers=headers
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "success"

    def test_delete_without_token_returns_401(self, http_client):
        resp = http_client.delete(
            "/notifications/00000000-0000-0000-0000-000000000000"
        )
        assert resp.status_code == 401