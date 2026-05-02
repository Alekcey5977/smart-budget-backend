import pytest
from app.models import Bank, Bank_Accounts, User
from httpx import AsyncClient
from passlib.context import CryptContext

pytestmark = pytest.mark.asyncio


async def test_add_bank_account_success(
    client: AsyncClient, test_user: User, auth_headers: dict, mock_bank_service, mock_event_publisher
):
    """✅ Успешное добавление счета через API"""
    payload = {
        # 20 цифр (корректный формат)
        "bank_account_number": "40817810099910004312",
        "bank_account_name": "Мой основной счет",
        "bank": "Тинькофф",
    }

    response = await client.post("/me/bank_account", json=payload, headers=auth_headers)

    assert response.status_code == 200, response.text
    data = response.json()
    assert data["bank_account_name"] == "Мой основной счет"
    mock_event_publisher.publish.assert_awaited_once()


async def test_add_bank_account_unauthorized(client: AsyncClient):
    """❌ Попытка добавления без токена"""
    payload = {
        "bank_account_number": "1234567890123456",  # Исправил на 16 цифр
        "bank_account_name": "T",
        "bank": "T",
    }
    response = await client.post("/me/bank_account", json=payload)
    assert response.status_code == 401


async def test_get_user_bank_accounts(client: AsyncClient, auth_headers: dict, mock_bank_service, mock_event_publisher):
    """✅ Получение списка счетов пользователя"""
    # Создаем через API
    # ИСПРАВЛЕНО: номер счета должен быть >= 16 цифр
    payload = {"bank_account_number": "40817810099910004313", "bank_account_name": "List", "bank": "Sber"}

    # Добавляем проверку создания, чтобы сразу видеть ошибку, если она есть
    create_resp = await client.post("/me/bank_account", json=payload, headers=auth_headers)
    assert create_resp.status_code == 200, f"Не удалось создать счет: {create_resp.text}"

    response = await client.get("/me/bank_accounts", headers=auth_headers)

    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 1


async def test_delete_bank_account(client: AsyncClient, auth_headers: dict, mock_bank_service, mock_event_publisher):
    """✅ Удаление счета"""
    # Создаем
    # ИСПРАВЛЕНО: номер счета должен быть >= 16 цифр
    payload = {"bank_account_number": "40817810099910004314", "bank_account_name": "ToDel", "bank": "Alpha"}

    create_resp = await client.post("/me/bank_account", json=payload, headers=auth_headers)
    assert create_resp.status_code == 200, create_resp.text
    account_id = create_resp.json()["bank_account_id"]

    # Удаляем
    del_resp = await client.delete(f"/me/bank_account/{account_id}", headers=auth_headers)
    assert del_resp.status_code == 204


async def test_rename_bank_account_success(
    client: AsyncClient, auth_headers: dict, mock_bank_service, mock_event_publisher
):
    """✅ Успешное переименование счёта"""
    create_resp = await client.post(
        "/me/bank_account",
        json={"bank_account_number": "40817810099910004315", "bank_account_name": "Старое имя", "bank": "Сбер"},
        headers=auth_headers,
    )
    assert create_resp.status_code == 200, create_resp.text
    account_id = create_resp.json()["bank_account_id"]

    rename_resp = await client.patch(
        f"/me/bank_account/{account_id}",
        json={"bank_account_name": "Новое имя"},
        headers=auth_headers,
    )
    assert rename_resp.status_code == 200
    data = rename_resp.json()
    assert data["bank_account_name"] == "Новое имя"
    assert data["bank_account_id"] == account_id


async def test_rename_bank_account_not_found(client: AsyncClient, auth_headers: dict):
    """❌ Переименование несуществующего счёта"""
    rename_resp = await client.patch(
        "/me/bank_account/99999",
        json={"bank_account_name": "Новое имя"},
        headers=auth_headers,
    )
    assert rename_resp.status_code == 404


async def test_rename_bank_account_unauthorized(client: AsyncClient):
    """❌ Попытка переименования без токена"""
    rename_resp = await client.patch(
        "/me/bank_account/1",
        json={"bank_account_name": "Новое имя"},
    )
    assert rename_resp.status_code == 401


async def test_rename_bank_account_empty_name(client: AsyncClient, auth_headers: dict):
    """❌ Пустое название — 422"""
    rename_resp = await client.patch(
        "/me/bank_account/1",
        json={"bank_account_name": "   "},
        headers=auth_headers,
    )
    assert rename_resp.status_code == 422


async def test_rename_not_my_account(
    client: AsyncClient,
    auth_headers: dict,
    db_session,
):
    """❌ Попытка переименовать чужой счёт"""
    from app.models import Bank, Bank_Accounts, User
    from passlib.context import CryptContext

    pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")
    other_user = User(
        email="rename_other@test.com",
        hashed_password=pwd_context.hash("pass"),
        first_name="Other",
        last_name="User",
        is_active=True,
    )
    db_session.add(other_user)
    bank = Bank(name="RenameBankOther")
    db_session.add(bank)
    await db_session.commit()
    await db_session.refresh(other_user)
    await db_session.refresh(bank)

    other_account = Bank_Accounts(
        user_id=other_user.id,
        bank_id=bank.id,
        bank_account_hash="rename_hash_other",
        bank_account_name="Чужой счёт",
        currency="RUB",
        balance=0,
    )
    db_session.add(other_account)
    await db_session.commit()
    await db_session.refresh(other_account)

    rename_resp = await client.patch(
        f"/me/bank_account/{other_account.bank_account_id}",
        json={"bank_account_name": "Попытка взлома"},
        headers=auth_headers,
    )
    assert rename_resp.status_code == 404


async def test_delete_not_my_account(
    client: AsyncClient,
    test_user: User,
    auth_headers: dict,
    db_session,  # Сессия из conftest
):
    """❌ Попытка удалить чужой счет"""

    pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")

    other_user = User(
        email="other_user_integ@test.com",
        hashed_password=pwd_context.hash("pass"),
        first_name="Other",
        last_name="User",
        is_active=True,
    )
    db_session.add(other_user)

    bank = Bank(name="UniqueBankForOtherUser")
    db_session.add(bank)

    await db_session.commit()

    await db_session.refresh(other_user)
    await db_session.refresh(bank)

    other_account = Bank_Accounts(
        user_id=other_user.id,
        bank_id=bank.id,
        bank_account_hash="unique_hash_other",
        bank_account_name="Чужой счет",
        currency="USD",
        balance=100,
    )
    db_session.add(other_account)
    await db_session.commit()
    await db_session.refresh(other_account)

    delete_resp = await client.delete(f"/me/bank_account/{other_account.bank_account_id}", headers=auth_headers)

    # Ожидаем 404, так как у текущего пользователя нет такого счета
    assert delete_resp.status_code == 404
