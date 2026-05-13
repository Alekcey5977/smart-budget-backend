[Документация](../README.md) / [Тестирование](overview.md) / Unit и интеграционные тесты

# Unit и интеграционные тесты

## Настройка окружения

Для запуска тестов нужны локальные виртуальные окружения:

```bash
make install   # Создать .venv и установить зависимости для всех 8 сервисов
               # Требуется Python 3.11–3.13
```

---

## Запуск тестов

```bash
# Все тесты (unit + integration) для всех сервисов
make test

# Только unit тесты
make test-unit

# Тесты конкретного сервиса
cd users_service && .venv/bin/pytest tests/ -v --tb=short

# Только unit тесты одного сервиса
cd users_service && .venv/bin/pytest tests/unit/ -v

# С показом stdout (print)
cd gateway && .venv/bin/pytest tests/ -v -s
```

---

## Конфигурация pytest

Каждый сервис имеет `pytest.ini`:
```ini
[pytest]
asyncio_mode = auto
```

`asyncio_mode = auto` — все async-тесты запускаются автоматически без декоратора `@pytest.mark.asyncio`.

---

## Unit тесты — структура и паттерны

### Fixtures (conftest.py)

Unit тесты мокируют все зависимости. Пример из `users_service/tests/unit/conftest.py`:

```python
@pytest.fixture
def mock_cache_client():
    mock = AsyncMock()
    mock.get.return_value = None  # cache miss по умолчанию
    mock.set.return_value = True
    return mock

@pytest.fixture
def mock_bank_account_repo():
    return AsyncMock(spec=BankAccountRepository)

@pytest.fixture
def mock_http_client():
    return AsyncMock()
```

### Пример unit теста роутера

```python
async def test_register_success(mock_user_repo, mock_cache_client):
    # Arrange
    mock_user_repo.get_by_email.return_value = None
    mock_user_repo.create.return_value = UserModel(id=1, email="test@example.com", ...)

    # Act
    response = await client.post("/users/register", json={
        "email": "test@example.com",
        "password": "StrongPass1!",
        "first_name": "Иван",
        "last_name": "Иванов"
    })

    # Assert
    assert response.status_code == 200
    assert response.json()["email"] == "test@example.com"
```

---

## Интеграционные тесты — SQLite in-memory

### Fixtures (conftest.py)

Интеграционные тесты используют реальную SQLite БД:

```python
@pytest.fixture
async def db_session():
    # SQLite in-memory с aiosqlite
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with AsyncSession(engine) as session:
        yield session

@pytest.fixture
def mock_pseudo_bank_client():
    # Внешние HTTP-сервисы всё равно мокируются
    return AsyncMock()
```

### Ограничения SQLite

- Нет `UUID` типа — используется `String` в тестах
- Нет некоторых PostgreSQL функций (`func.now()` работает)
- Отличается поведение `DECIMAL` — используйте `float` в assert

---

## Тестируемые компоненты по сервисам

### gateway
- Роутеры с мокированным HTTP-клиентом
- JWT-декодирование и зависимости аутентификации
- Кэширование профиля (mock Redis)

### users_service
- Регистрация и логин (mock argon2, mock JWT)
- CRUD банковских счетов (mock pseudo-bank HTTP)
- JWT генерация и верификация

### transactions_service
- Фильтрация транзакций (SQLite)
- Логика синхронизации (mock pseudo-bank)
- Смена категории транзакции

### purposes_service
- CRUD целей (SQLite)
- Логика пересечения порогов прогресса
- Публикация событий (mock EventPublisher)

### notification_service / history_service
- Сохранение и чтение уведомлений/истории (SQLite)
- Обработка событий (mock EventListener)

---

## Связанные разделы

- [Обзор стратегии тестирования](overview.md)
- [E2E тесты](e2e.md)
- [Нагрузочные тесты](load-testing.md)
