[Документация](../README.md) / Тестирование / Обзор

# Стратегия тестирования

## Уровни тестирования

SmartBudget использует четыре уровня тестирования, каждый со своей средой и целью:

| Уровень | Среда | Скорость | Покрытие |
|---------|-------|---------|----------|
| Unit | Моки, без БД | Секунды | Бизнес-логика, роутеры |
| Integration | SQLite in-memory | Секунды | Роутер + репозиторий + БД |
| E2E | Docker Compose (изолированный стек) | Минуты | Сквозные сценарии через Gateway |
| Load (k6) | Docker Compose (тестовый стек) | Минуты | Производительность, стабильность |

---

## Unit тесты

**Что тестируют:** роутеры с замоканными зависимостями, репозитории, Pydantic-схемы.

**Инструменты:** `pytest`, `pytest-asyncio`, `unittest.mock`

**Изоляция:** все внешние зависимости (БД, Redis, HTTP-клиент) замоканы через pytest fixtures в `conftest.py`.

**Структура:**
```
{service}/tests/unit/
├── conftest.py          — моки (cache_client, db, http)
├── routers/             — тесты роутеров
│   └── test_*.py
└── repository/          — тесты репозиториев
    └── test_*.py
```

**Запуск:**
```bash
make test-unit                              # все сервисы
cd users_service && .venv/bin/pytest tests/unit/ -v  # один сервис
```

---

## Интеграционные тесты

**Что тестируют:** взаимодействие роутера, репозитория и базы данных как единого целого.

**Инструменты:** `pytest`, `pytest-asyncio`, SQLite in-memory (`aiosqlite`)

**Особенность:** SQLite вместо PostgreSQL — быстро, без Docker, но с ограничениями (нет UUID-типа, нет некоторых PostgreSQL функций).

**Структура:**
```
{service}/tests/integration/
├── conftest.py          — SQLite in-memory БД, замоканные внешние сервисы
└── test_*.py
```

**Запуск:**
```bash
make test                                   # unit + integration все сервисы
cd users_service && .venv/bin/pytest tests/ -v
```

---

## E2E тесты

**Что тестируют:** полные пользовательские сценарии через реальный Gateway на изолированном Docker-стеке.

**Среда:** `docker-compose.test.yml` — отдельные БД, порты 18000+, project `smartbudget-test`.

**Структура:** `e2e_tests/` в корне репозитория:
```
e2e_tests/
├── conftest.py          — shared fixtures
├── pytest.ini           — маркер e2e
├── test_auth.py
├── test_bank_accounts.py
├── test_transactions.py
├── test_sync.py
├── test_purposes.py
├── test_notifications.py
├── test_history.py
└── test_images.py
```

**Запуск:**
```bash
make test-e2e-start   # Поднять стек + загрузить тестовые данные
make test-e2e         # Запустить тесты
make test-e2e-stop    # Остановить и удалить стек
```

Подробности: [E2E тесты](e2e.md)

---

## Нагрузочные тесты (k6)

**Что тестируют:** производительность под нагрузкой, устойчивость к спайкам, поиск предела.

**Среда:** тот же тестовый стек (порт 18000).

**7 профилей:** smoke (1 VU) → load (50 VU) → stress (150 VU) → spike (1000 VU) → max (3000 VU) → high (5000 VU) → extreme (10000 VU).

**Запуск:**
```bash
make test-e2e-start   # Поднять стек
make k6               # smoke → load → stress последовательно
make k6-smoke         # Только smoke test
```

Подробности: [Нагрузочные тесты](load-testing.md)

---

## CI/CD

| Workflow | Триггер | Что делает |
|---------|---------|-----------|
| `ci.yml` | push, pull_request | Ruff lint + unit/integration тесты |
| `e2e.yml` | PR на main + ручной запуск | Docker стек + E2E тесты |

Конфигурация: `.github/workflows/`

---

## Структура тестов по сервисам

| Сервис | Unit | Integration | E2E |
|--------|------|-------------|-----|
| gateway | да | — | через все тесты |
| users_service | да | да | test_auth.py, test_bank_accounts.py |
| transactions_service | да | да | test_transactions.py, test_sync.py |
| images_service | да | да | test_images.py |
| pseudo_bank_service | да | — | используется косвенно |
| purposes_service | да | да | test_purposes.py |
| notification_service | да | да | test_notifications.py |
| history_service | да | да | test_history.py |

---

## Связанные разделы

- [Unit и интеграционные тесты](unit-integration.md)
- [E2E тесты](e2e.md)
- [Нагрузочные тесты k6](load-testing.md)
- [Справочник Makefile](../deployment/makefile-reference.md)
