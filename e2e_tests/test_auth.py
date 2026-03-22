import uuid


PASSWORD = "StrongPass1!"


class TestRegister:
    def test_register_success(self, http_client):
        uid = uuid.uuid4().hex[:8]
        payload = {
            "email": f"reg_{uid}@example.com",
            "password": PASSWORD,
            "first_name": "Reg",
            "last_name": "Test",
        }
        resp = http_client.post("/auth/register", json=payload)
        assert resp.status_code == 200
        data = resp.json()
        assert data["email"] == payload["email"]
        assert data["first_name"] == "Reg"
        assert "password" not in data
        assert "hashed_password" not in data

    def test_register_duplicate_email_returns_400(self, http_client, registered_user):
        resp = http_client.post(
            "/auth/register",
            json={
                "email": registered_user["email"],
                "password": PASSWORD,
                "first_name": "Dup",
                "last_name": "User",
            },
        )
        assert resp.status_code == 400

    def test_register_weak_password_returns_422(self, http_client):
        resp = http_client.post(
            "/auth/register",
            json={
                "email": f"weak_{uuid.uuid4().hex[:8]}@example.com",
                "password": "weak",
                "first_name": "Bad",
                "last_name": "Pass",
            },
        )
        assert resp.status_code == 422

    def test_register_missing_fields_returns_422(self, http_client):
        resp = http_client.post("/auth/register", json={"email": "x@x.com"})
        assert resp.status_code == 422


class TestLogin:
    def test_login_success_returns_token(self, http_client, registered_user):
        resp = http_client.post(
            "/auth/login",
            json={
                "email": registered_user["email"],
                "password": registered_user["password"],
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert len(data["access_token"]) > 20

    def test_login_wrong_password_returns_401(self, http_client, registered_user):
        resp = http_client.post(
            "/auth/login",
            json={
                "email": registered_user["email"],
                "password": "WrongPass1!",
            },
        )
        assert resp.status_code == 401

    def test_login_nonexistent_user_returns_401(self, http_client):
        resp = http_client.post(
            "/auth/login",
            json={"email": "nonexistent_xyz99@example.com", "password": PASSWORD},
        )
        assert resp.status_code == 401


class TestGetMe:
    def test_get_me_with_valid_token(self, http_client, auth_headers, registered_user):
        _, headers = auth_headers
        resp = http_client.get("/auth/me", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["user"]["email"] == registered_user["email"]
        assert "user_id" in data

    def test_get_me_without_token_returns_401(self, http_client):
        resp = http_client.get("/auth/me")
        assert resp.status_code == 401

    def test_get_me_invalid_token_returns_401(self, http_client):
        resp = http_client.get(
            "/auth/me",
            headers={"Authorization": "Bearer totally.invalid.token"},
        )
        assert resp.status_code == 401


class TestUpdateMe:
    def test_update_first_name(self, http_client, auth_headers):
        _, headers = auth_headers
        resp = http_client.put(
            "/auth/me",
            json={"first_name": "Updated"},
            headers=headers,
        )
        assert resp.status_code == 200
        assert resp.json()["first_name"] == "Updated"

    def test_update_without_token_returns_401(self, http_client):
        resp = http_client.put("/auth/me", json={"first_name": "X"})
        assert resp.status_code == 401


class TestFullLifecycle:
    def test_register_login_refresh_logout(self, http_client):
        uid = uuid.uuid4().hex[:8]
        user = {
            "email": f"lifecycle_{uid}@example.com",
            "password": PASSWORD,
            "first_name": "Life",
            "last_name": "Cycle",
        }

        # 1. Register
        resp = http_client.post("/auth/register", json=user)
        assert resp.status_code == 200

        # 2. Login
        resp = http_client.post(
            "/auth/login",
            json={"email": user["email"], "password": user["password"]},
        )
        assert resp.status_code == 200
        assert resp.json()["access_token"]

        # 3. Refresh (использует refresh_token cookie из предыдущего ответа)
        resp = http_client.post("/auth/refresh")
        assert resp.status_code == 200
        new_token = resp.json()["access_token"]
        assert new_token

        # 4. Logout
        resp = http_client.post(
            "/auth/logout",
            headers={"Authorization": f"Bearer {new_token}"},
        )
        assert resp.status_code == 200
        assert resp.json()["msg"] == "Logged out"