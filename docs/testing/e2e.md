[Документация](../README.md) / [Тестирование](overview.md) / E2E тесты

# E2E тесты

Сквозные тесты проверяют полные пользовательские сценарии через реальный Gateway на изолированном Docker-стеке с отдельными базами данных.

## Подготовка и запуск

```bash
# Шаг 1: Поднять изолированный тестовый стек
make test-e2e-start
# Стек готов на http://localhost:18000
# Автоматически грузит тестовые данные

# Шаг 2: Запустить тесты
make test-e2e

# Шаг 3: Остановить стек (удаляет все тестовые данные)
make test-e2e-stop
```

---

## Тестовый стек

| Ресурс | URL |
|--------|-----|
| Gateway | http://localhost:18000 |
| Grafana | http://localhost:13000 |
| Prometheus | http://localhost:19090 |

Стек запускается командой `docker compose -f docker-compose.test.yml -p smartbudget-test up -d`.

---

## Fixtures (e2e_tests/conftest.py)

```python
@pytest.fixture(scope="session")
async def check_gateway_reachable():
    """Проверить, что Gateway доступен перед тестами."""
    # GET http://localhost:18000/health

@pytest.fixture(scope="session")
async def http_client():
    """AsyncClient для запросов через Gateway."""
    async with httpx.AsyncClient(base_url="http://localhost:18000") as client:
        yield client

@pytest.fixture
async def registered_user(http_client):
    """Зарегистрировать нового пользователя (уникальный email)."""
    email = f"test_{uuid4()}@example.com"
    await http_client.post("/auth/register", json={...})
    return {"email": email, "password": "StrongPass1!"}

@pytest.fixture
async def auth_headers(http_client, registered_user):
    """Залогиниться и вернуть заголовок Authorization."""
    response = await http_client.post("/auth/login", json=registered_user)
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}

@pytest.fixture
async def bank_account(http_client, auth_headers):
    """Добавить банковский счёт для пользователя."""
    # Перебирает тестовые счета пока не найдёт свободный
    for number in BANK_ACCOUNT_NUMBERS:
        response = await http_client.post("/users/me/bank_account",
            headers=auth_headers,
            json={"bank_account_number": number, ...})
        if response.status_code == 200:
            return response.json()
    pytest.skip("Все тестовые счета заняты — выполните make reset-db")
```

---

## Тест-файлы

### test_auth.py
- Регистрация с валидными и невалидными данными
- Логин, получение access token и refresh cookie
- Обновление токена через /auth/refresh
- Получение профиля через /auth/me
- Обновление профиля через PUT /auth/me
- Выход и инвалидация сессии

### test_bank_accounts.py
- Добавление счёта (happy path)
- Получение списка счетов
- Переименование счёта
- Удаление счёта
- Попытка добавить несуществующий счёт

### test_sync.py
- Ручная синхронизация через POST /sync
- Проверка появления транзакций после sync
- Проверка обновления баланса счёта

### test_transactions.py
- Получение списка транзакций с фильтрацией
- Фильтрация по типу (income/expense)
- Фильтрация по дате, сумме, категории
- Пагинация (limit/offset)
- Смена категории транзакции
- Сводка по категориям (POST /transactions/categories/summary)

### test_purposes.py
- Создание финансовой цели
- Получение списка целей
- Обновление суммы (проверка порогов уведомлений)
- Удаление цели

### test_notifications.py
- Получение уведомления после регистрации (welcome)
- Отметка как прочитанное
- Отметка всех как прочитанных
- Удаление уведомления
- Проверка счётчика непрочитанных

### test_history.py
- Проверка создания записей истории при действиях
- Получение списка истории
- Удаление записи

### test_images.py
- Получение списка предустановленных аватарок
- Установка аватарки пользователю
- Получение аватарки пользователя
- Маппинги категорий и мерчантов

---

## Тестовые счета

E2E тесты используют 10 предзагруженных тестовых счетов (см. [Pseudo Bank Service](../services/pseudo-bank-service.md)). Каждый счёт может быть привязан только к одному пользователю одновременно.

**При параллельном запуске тестов** или после нагрузочных тестов все слоты могут быть заняты. Освободить:
```bash
make test-e2e-stop && make test-e2e-start
# или для dev-стека:
make reset-db && make load-test-data
```

---

## Связанные разделы

- [Обзор тестирования](overview.md)
- [Нагрузочные тесты](load-testing.md)
- [Pseudo Bank Service](../services/pseudo-bank-service.md)
- [Makefile: test-e2e команды](../deployment/makefile-reference.md)
