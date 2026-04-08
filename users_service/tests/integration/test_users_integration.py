import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from shared.event_publisher import EventPublisher


# Тест регистрации
@pytest.mark.asyncio
async def test_register_user(client: AsyncClient, db_session: AsyncSession, mock_event_publisher: EventPublisher):
    response = await client.post(
        "/users/register",
        json={
            "email": "test@example.com",
            "password": "StrongPass123!",
            "first_name": "Ivan",
            "last_name": "Ivanov",
            "middle_name": "Ivanovich",
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "test@example.com"
    assert data["first_name"] == "Ivan"
    assert "id" in data

    # Проверяем, что событие было опубликовано
    mock_event_publisher.publish.assert_awaited_once()
    event_call = mock_event_publisher.publish.call_args
    event = event_call.args[0]
    assert event.event_type == "user.registered"
    assert event.payload["user_id"] == data["id"]


# Тест регистрации с уже существующим email
@pytest.mark.asyncio
async def test_register_duplicate_email(client: AsyncClient):
    # Первая регистрация
    await client.post(
        "/users/register",
        json={"email": "dup@example.com", "password": "StrongPass123!", "first_name": "Test", "last_name": "Test"},
    )
    # Попытка повторной регистрации
    response = await client.post(
        "/users/register",
        json={"email": "dup@example.com", "password": "StrongPass123!", "first_name": "Test", "last_name": "Test"},
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "Email already registered"


# Тест входа (login) и проверка токенов
@pytest.mark.asyncio
async def test_login_and_access_protected_route(client: AsyncClient):
    # 1. Регистрация
    await client.post(
        "/users/register",
        json={"email": "login@example.com", "password": "StrongPass123!", "first_name": "Login", "last_name": "Test"},
    )

    # 2. Вход
    login_response = await client.post(
        "/users/login", json={"email": "login@example.com", "password": "StrongPass123!"}
    )

    assert login_response.status_code == 200
    tokens = login_response.json()
    assert "access_token" in tokens
    assert tokens["token_type"] == "bearer"

    # Проверяем, что refresh_token установился в cookies
    cookies = login_response.cookies
    assert "refresh_token" in cookies

    access_token = tokens["access_token"]

    # 3. Доступ к защищенному роуту /me
    me_response = await client.get("/users/me", headers={"Authorization": f"Bearer {access_token}"})

    assert me_response.status_code == 200
    user_data = me_response.json()
    assert user_data["email"] == "login@example.com"


# Тест обновления профиля
@pytest.mark.asyncio
async def test_update_user_profile(client: AsyncClient, mock_event_publisher: EventPublisher):
    # Подготовка: регистрация и вход
    await client.post(
        "/users/register",
        json={"email": "update@example.com", "password": "StrongPass123!", "first_name": "Old", "last_name": "Name"},
    )

    login_resp = await client.post("/users/login", json={"email": "update@example.com", "password": "StrongPass123!"})
    token = login_resp.json()["access_token"]

    # Сбросим счетчик вызовов мока перед обновлением
    mock_event_publisher.publish.reset_mock()

    # Действие: обновление данных
    update_response = await client.put(
        "/users/me",
        json={
            "first_name": "New",
            "last_name": "Name",
            "middle_name": "Middle",  # Добавляем отчество
        },
        headers={"Authorization": f"Bearer {token}"},
    )

    assert update_response.status_code == 200
    data = update_response.json()
    assert data["first_name"] == "New"
    assert data["middle_name"] == "Middle"

    # Проверка события обновления
    mock_event_publisher.publish.assert_awaited_once()
    event = mock_event_publisher.publish.call_args.args[0]
    assert event.event_type == "user.updated"


# Тест ошибки авторизации (неверный пароль)
@pytest.mark.asyncio
async def test_login_wrong_password(client: AsyncClient):
    await client.post(
        "/users/register",
        json={
            "email": "wrongpass@example.com",
            "password": "CorrectPass123!",
            "first_name": "Test",
            "last_name": "Test",
        },
    )

    response = await client.post("/users/login", json={"email": "wrongpass@example.com", "password": "WrongPass123!"})

    assert response.status_code == 401
    assert response.json()["detail"] == "Incorrect email or password"
