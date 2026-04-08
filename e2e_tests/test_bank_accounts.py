from conftest import BANK_ACCOUNT_NUMBERS

NONEXISTENT_ACCOUNT = {
    "bank_account_number": "9999999999999999",
    "bank_account_name": "Ghost",
    "bank": "NoBank",
}


class TestAddBankAccount:
    def test_add_valid_account_returns_balance(self, http_client, auth_headers, bank_account):
        data = bank_account
        assert "bank_account_id" in data
        assert float(data["balance"]) > 0
        assert data["currency"] == "RUB"
        assert "bank_account_name" in data

    def test_add_same_account_twice_returns_400(self, http_client, auth_headers, bank_account):
        _, headers = auth_headers
        number = bank_account["_account_number"]
        resp = http_client.post(
            "/users/me/bank_account",
            json={
                "bank_account_number": number,
                "bank_account_name": "Duplicate",
                "bank": "TestBank",
            },
            headers=headers,
        )
        assert resp.status_code == 400

    def test_add_nonexistent_account_returns_400(self, http_client, auth_headers):
        _, headers = auth_headers
        resp = http_client.post("/users/me/bank_account", json=NONEXISTENT_ACCOUNT, headers=headers)
        assert resp.status_code == 400

    def test_add_without_token_returns_401(self, http_client):
        resp = http_client.post(
            "/users/me/bank_account",
            json={
                "bank_account_number": BANK_ACCOUNT_NUMBERS[0],
                "bank_account_name": "Card",
                "bank": "TestBank",
            },
        )
        assert resp.status_code == 401


class TestGetBankAccounts:
    def test_empty_list_for_new_user(self, http_client, auth_headers):
        _, headers = auth_headers
        resp = http_client.get("/users/me/bank_accounts", headers=headers)
        assert resp.status_code == 200
        assert resp.json() == []

    def test_list_contains_added_account(self, http_client, auth_headers, bank_account):
        _, headers = auth_headers
        resp = http_client.get("/users/me/bank_accounts", headers=headers)
        assert resp.status_code == 200
        accounts = resp.json()
        assert len(accounts) == 1
        assert accounts[0]["bank_account_id"] == bank_account["bank_account_id"]
        assert accounts[0]["currency"] == "RUB"

    def test_get_accounts_without_token_returns_401(self, http_client):
        resp = http_client.get("/users/me/bank_accounts")
        assert resp.status_code == 401


class TestDeleteBankAccount:
    def test_delete_existing_account_returns_204(self, http_client, auth_headers, bank_account):
        _, headers = auth_headers
        account_id = bank_account["bank_account_id"]

        resp = http_client.delete(f"/users/me/bank_account/{account_id}", headers=headers)
        assert resp.status_code == 204

        # Проверяем что счёт исчез
        resp = http_client.get("/users/me/bank_accounts", headers=headers)
        assert resp.status_code == 200
        assert resp.json() == []

    def test_delete_nonexistent_account_returns_404(self, http_client, auth_headers):
        _, headers = auth_headers
        resp = http_client.delete("/users/me/bank_account/999999", headers=headers)
        assert resp.status_code == 404

    def test_delete_without_token_returns_401(self, http_client, bank_account):
        account_id = bank_account["bank_account_id"]
        resp = http_client.delete(f"/users/me/bank_account/{account_id}")
        assert resp.status_code == 401
