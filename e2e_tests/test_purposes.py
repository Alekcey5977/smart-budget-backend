"""
E2E tests for /purposes/* — полный CRUD жизненный цикл.
"""

import uuid

PURPOSE = {
    "title": "E2E Test Purpose",
    "deadline": "2027-12-31T00:00:00",
    "amount": 0.0,
    "total_amount": 10000.0,
}


class TestCreatePurpose:
    def test_create_purpose_success(self, http_client, auth_headers):
        _, headers = auth_headers
        resp = http_client.post("/purposes/create", json=PURPOSE, headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["title"] == PURPOSE["title"]
        assert float(data["total_amount"]) == 10000.0
        assert "id" in data
        assert "user_id" in data

    def test_create_without_token_returns_401(self, http_client):
        resp = http_client.post("/purposes/create", json=PURPOSE)
        assert resp.status_code == 401

    def test_create_missing_title_returns_422(self, http_client, auth_headers):
        _, headers = auth_headers
        resp = http_client.post(
            "/purposes/create",
            json={"deadline": "2027-12-31T00:00:00", "amount": 0.0, "total_amount": 1000.0},
            headers=headers,
        )
        assert resp.status_code == 422


class TestGetPurposes:
    def test_empty_list_for_new_user(self, http_client, auth_headers):
        _, headers = auth_headers
        resp = http_client.get("/purposes/my", headers=headers)
        assert resp.status_code == 200
        assert resp.json() == []

    def test_created_purpose_appears_in_list(self, http_client, auth_headers):
        _, headers = auth_headers
        http_client.post("/purposes/create", json=PURPOSE, headers=headers)
        resp = http_client.get("/purposes/my", headers=headers)
        assert resp.status_code == 200
        purposes = resp.json()
        assert len(purposes) == 1
        assert purposes[0]["title"] == PURPOSE["title"]

    def test_get_purposes_without_token_returns_401(self, http_client):
        resp = http_client.get("/purposes/my")
        assert resp.status_code == 401


class TestUpdatePurpose:
    def test_update_title(self, http_client, auth_headers):
        _, headers = auth_headers
        create_resp = http_client.post("/purposes/create", json=PURPOSE, headers=headers)
        purpose_id = create_resp.json()["id"]

        resp = http_client.put(
            f"/purposes/update/{purpose_id}",
            json={"title": "Updated Title"},
            headers=headers,
        )
        assert resp.status_code == 200
        assert resp.json()["title"] == "Updated Title"

    def test_update_nonexistent_purpose_returns_404(self, http_client, auth_headers):
        _, headers = auth_headers
        fake_id = "00000000-0000-0000-0000-000000000000"
        resp = http_client.put(
            f"/purposes/update/{fake_id}",
            json={"title": "Ghost"},
            headers=headers,
        )
        assert resp.status_code == 404

    def test_update_other_users_purpose_returns_404(self, http_client, auth_headers):
        # Пользователь A создаёт purpose
        _, headers_a = auth_headers
        create_resp = http_client.post("/purposes/create", json=PURPOSE, headers=headers_a)
        purpose_id = create_resp.json()["id"]

        # Пользователь B пытается изменить
        uid = uuid.uuid4().hex[:8]
        user_b = {
            "email": f"userb_{uid}@example.com",
            "password": "StrongPass1!",
            "first_name": "Bob",
            "last_name": "Other",
        }
        http_client.post("/auth/register", json=user_b)
        login_b = http_client.post(
            "/auth/login",
            json={"email": user_b["email"], "password": user_b["password"]},
        )
        headers_b = {"Authorization": f"Bearer {login_b.json()['access_token']}"}

        resp = http_client.put(
            f"/purposes/update/{purpose_id}",
            json={"title": "Stolen"},
            headers=headers_b,
        )
        assert resp.status_code == 404

    def test_update_without_token_returns_401(self, http_client):
        resp = http_client.put(
            "/purposes/update/00000000-0000-0000-0000-000000000000",
            json={"title": "X"},
        )
        assert resp.status_code == 401


class TestDeletePurpose:
    def test_delete_purpose_success(self, http_client, auth_headers):
        _, headers = auth_headers
        create_resp = http_client.post("/purposes/create", json=PURPOSE, headers=headers)
        purpose_id = create_resp.json()["id"]

        resp = http_client.delete(f"/purposes/delete/{purpose_id}", headers=headers)
        assert resp.status_code == 200

        # Проверяем что удалено
        list_resp = http_client.get("/purposes/my", headers=headers)
        assert list_resp.json() == []

    def test_delete_nonexistent_purpose_returns_404(self, http_client, auth_headers):
        _, headers = auth_headers
        fake_id = "00000000-0000-0000-0000-000000000000"
        resp = http_client.delete(f"/purposes/delete/{fake_id}", headers=headers)
        assert resp.status_code == 404

    def test_delete_without_token_returns_401(self, http_client):
        resp = http_client.delete("/purposes/delete/00000000-0000-0000-0000-000000000000")
        assert resp.status_code == 401
