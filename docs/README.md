# SmartBudget Backend — Документация

SmartBudget — бэкенд-система для управления личными финансами. Построена на микросервисной архитектуре: 8 независимых FastAPI-сервисов, каждый со своей базой данных, объединённых через API Gateway и асинхронную шину событий на Redis Streams.

---

## Навигация

| Раздел | Описание | Точка входа |
|--------|----------|-------------|
| **Архитектура** | Общее устройство системы, схемы данных, события | [architecture/overview.md](architecture/overview.md) |
| **Сервисы** | Детальное описание каждого микросервиса | [services/gateway.md](services/gateway.md) |
| **API** | Полный справочник эндпоинтов с примерами | [api/index.md](api/index.md) |
| **Деплой** | Быстрый старт, конфигурация, Docker | [deployment/quickstart.md](deployment/quickstart.md) |
| **Тестирование** | Unit, интеграционные, E2E и нагрузочные тесты | [testing/overview.md](testing/overview.md) |
| **Мониторинг** | Prometheus, Grafana, Loki | [monitoring/overview.md](monitoring/overview.md) |

---

## Карта микросервисов

| Сервис | Порт | База данных | Назначение |
|--------|------|-------------|------------|
| **gateway** | 8000 | — | Единая точка входа, JWT-аутентификация, маршрутизация |
| **users-service** | 8001 | PostgreSQL :5433 | Регистрация, логин, профиль, банковские счета |
| **transactions-service** | 8002 | PostgreSQL :5434 | Транзакции, синхронизация с банком, категоризация |
| **images-service** | 8003 | PostgreSQL :5435 | Аватарки пользователей, иконки категорий и мерчантов |
| **pseudo-bank-service** | 8004 | PostgreSQL :5436 | Мок-банк для разработки и тестирования |
| **purposes-service** | 8005 | PostgreSQL :5437 | Финансовые цели и сберегательные планы |
| **notification-service** | 8006 | PostgreSQL :5438 | Уведомления в реальном времени через WebSocket |
| **history-service** | 8007 | PostgreSQL :5439 | Аудит-трейл действий пользователя |

---

## Быстрые ссылки

- **Запустить за 5 минут** → [deployment/quickstart.md](deployment/quickstart.md)
- **Справочник всех API эндпоинтов** → [api/index.md](api/index.md)
- **Как работает синхронизация транзакций** → [services/transactions-service.md](services/transactions-service.md)
- **Как работает система событий** → [architecture/event-system.md](architecture/event-system.md)
- **Запустить тесты** → [testing/overview.md](testing/overview.md)
- **Нагрузочное тестирование k6** → [testing/load-testing.md](testing/load-testing.md)

---

## Адреса после `make start`

| Сервис | URL |
|--------|-----|
| API Gateway (Swagger UI) | http://localhost:8000/docs |
| Grafana | http://localhost:3000 (admin / admin) |
| Prometheus | http://localhost:9090 |
| Redis Commander | http://localhost:8081 |

---

## Технологический стек

**Язык и фреймворки:** Python 3.11, FastAPI 0.115, SQLAlchemy 2.0, Pydantic 2.8

**Инфраструктура:** Docker Compose, PostgreSQL 13 (×8), Redis 7 Alpine

**Аутентификация:** JWT (python-jose), argon2 (пароли)

**Асинхронность:** asyncpg, httpx (async), APScheduler, Redis Streams

**Мониторинг:** Prometheus, Grafana, Loki, Promtail

**Тестирование:** pytest, pytest-asyncio, k6

---

## Структура репозитория

```
smart-budget-backend/
├── gateway/                   # API Gateway
├── users_service/             # Сервис пользователей
├── transactions_service/      # Сервис транзакций
├── images_service/            # Сервис изображений
├── pseudo_bank_service/       # Мок-банк
├── purposes_service/          # Сервис финансовых целей
├── notification_service/      # Сервис уведомлений
├── history_service/           # Сервис истории
├── shared/                    # Общие библиотеки (cache, event_publisher, logging)
├── e2e_tests/                 # Сквозные тесты
├── k6/                        # Нагрузочные тесты
├── monitoring/                # Конфигурации Grafana, Prometheus
├── testData/                  # Генераторы и загрузчики тестовых данных
├── docs/                      # Документация (этот раздел)
├── docker-compose.yml         # Продакшн-стек
├── docker-compose.test.yml    # Изолированный тестовый стек
├── Makefile                   # Автоматизация задач
└── .env.example               # Шаблон переменных окружения
```

---

## Команда

- **Алексей Килин** — Team Lead, Backend Developer
- **Дмитрий Лыков** — Backend Developer
- **Александр Оскин** — Frontend Developer
- **Вадим Попов** — Frontend Developer
