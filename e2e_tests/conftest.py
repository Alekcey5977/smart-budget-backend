import os
import uuid

import httpx
import pytest

GATEWAY_URL = os.environ.get("GATEWAY_URL", "http://localhost:28000")
PASSWORD = "StrongPass1!"
# All account numbers loaded by `make load-test-data`.
# The constraint is global (not per-user), so the fixture tries each until one is free.
BANK_ACCOUNT_NUMBERS = [
    "40817810099910004312",
    "40817810099910004313",
    "40817810099910004314",
    "40817810099910004315",
    "40817810099910004316",
    "40817810099910004317",
    "40817810099910004318",
    "40817810099910004319",
    "40817810099910004320",
    "40817810099910004321",
]


# ---------------------------------------------------------------------------
# Auto-mark all tests in e2e_tests/ with @pytest.mark.e2e
# ---------------------------------------------------------------------------
def pytest_collection_modifyitems(items):
    e2e_mark = pytest.mark.e2e
    for item in items:
        if "e2e_tests" in str(item.fspath):
            item.add_marker(e2e_mark)


# ---------------------------------------------------------------------------
# Connectivity guard — пропустить все тесты если gateway не запущен
# ---------------------------------------------------------------------------
@pytest.fixture(scope="session", autouse=True)
def check_gateway_reachable():
    try:
        with httpx.Client(timeout=5.0) as c:
            c.get(f"{GATEWAY_URL}/health").raise_for_status()
    except Exception as exc:
        pytest.skip(f"Gateway not reachable: {exc}. Run: make start")


# ---------------------------------------------------------------------------
# Shared HTTP client — session scope, синхронный (нет проблем с event loop)
# ---------------------------------------------------------------------------
@pytest.fixture(scope="session")
def http_client():
    with httpx.Client(
        base_url=GATEWAY_URL,
        timeout=30.0,
        follow_redirects=True,
    ) as client:
        yield client


# ---------------------------------------------------------------------------
# registered_user — новый уникальный пользователь для каждого теста
# ---------------------------------------------------------------------------
@pytest.fixture
def registered_user(http_client):
    uid = uuid.uuid4().hex[:12]
    user = {
        "email": f"e2e_{uid}@example.com",
        "password": PASSWORD,
        "first_name": "E2E",
        "last_name": "Test",
    }
    resp = http_client.post("/auth/register", json=user)
    assert resp.status_code == 200, f"Register failed: {resp.text}"
    yield user
    # Best-effort cleanup: logout инвалидирует refresh token
    try:
        r = http_client.post(
            "/auth/login",
            json={"email": user["email"], "password": PASSWORD},
        )
        if r.status_code == 200:
            token = r.json()["access_token"]
            http_client.post(
                "/auth/logout",
                headers={"Authorization": f"Bearer {token}"},
            )
    except Exception:
        pass


# ---------------------------------------------------------------------------
# auth_headers — (token, headers_dict) для текущего registered_user
# ---------------------------------------------------------------------------
@pytest.fixture
def auth_headers(http_client, registered_user):
    resp = http_client.post(
        "/auth/login",
        json={
            "email": registered_user["email"],
            "password": registered_user["password"],
        },
    )
    assert resp.status_code == 200, f"Login failed: {resp.text}"
    token = resp.json()["access_token"]
    return token, {"Authorization": f"Bearer {token}"}


# ---------------------------------------------------------------------------
# bank_account — добавляет счёт, возвращает данные, удаляет после теста
# ---------------------------------------------------------------------------
@pytest.fixture
def bank_account(http_client, auth_headers):
    _, headers = auth_headers
    data = None
    used_number = None
    for number in BANK_ACCOUNT_NUMBERS:
        resp = http_client.post(
            "/users/me/bank_account",
            json={
                "bank_account_number": number,
                "bank_account_name": "E2E Account",
                "bank": "TestBank",
            },
            headers=headers,
        )
        if resp.status_code == 200:
            data = resp.json()
            used_number = number
            break
    if data is None:
        pytest.skip("All bank account numbers taken — run: make reset-db")
    data["_account_number"] = used_number
    yield data
    try:
        http_client.delete(
            f"/users/me/bank_account/{data['bank_account_id']}",
            headers=headers,
        )
    except Exception:
        pass
