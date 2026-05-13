[Документация](../README.md) / [Деплой](quickstart.md) / Конфигурация

# Конфигурация (переменные окружения)

## Файлы конфигурации

| Файл | Назначение |
|------|-----------|
| `.env` | Основное окружение (dev/prod) |
| `.env.test` | Изолированный тестовый стек (порты 18000+) |
| `.env.example` | Шаблон — не содержит секретов, безопасно коммитить |

Файл `.env` не коммитится в git (в `.gitignore`). При первом запуске: `cp .env.example .env`.

---

## Обязательные секреты (изменить перед продакшном)

| Переменная | Описание | Генерация |
|-----------|----------|-----------|
| `ACCESS_SECRET_KEY` | Подпись JWT access token | `openssl rand -hex 32` |
| `REFRESH_SECRET_KEY` | Подпись JWT refresh token | `openssl rand -hex 32` |
| `BANK_SECRET_KEY` | HMAC-ключ для хэширования номеров счетов | Произвольная строка |

**Важно:** `BANK_SECRET_KEY` нельзя менять после загрузки тестовых данных — хэши счетов в pseudo_bank_db будут несовпадать.

---

## Базы данных

```env
# users-service
USERS_DATABASE_URL=postgresql+asyncpg://users_user:users_password@users-db:5432/users_db
USERS_DB_USER=users_user
USERS_DB_PASSWORD=users_password
USERS_DB_NAME=users_db

# transactions-service
TRANSACTIONS_DATABASE_URL=postgresql+asyncpg://tr_user:tr_password@transactions-db:5432/transactions_db
TRANSACTIONS_DB_USER=tr_user
TRANSACTIONS_DB_PASSWORD=tr_password
TRANSACTIONS_DB_NAME=transactions_db

# images-service
IMAGES_DATABASE_URL=postgresql+asyncpg://img_user:img_password@images-db:5432/images_db
IMAGES_DB_USER=img_user
IMAGES_DB_PASSWORD=img_password
IMAGES_DB_NAME=images_db

# pseudo-bank-service
PSEUDO_BANK_DATABASE_URL=postgresql+asyncpg://pseudo_user:pseudo_password@pseudo-bank-db:5432/pseudo_bank_db
PSEUDO_BANK_DB_USER=pseudo_user
PSEUDO_BANK_DB_PASSWORD=pseudo_password
PSEUDO_BANK_DB_NAME=pseudo_bank_db

# purposes-service
PURPOSES_DATABASE_URL=postgresql+asyncpg://purposes_user:purposes_password@purposes-db:5432/purposes_db
PURPOSES_DB_USER=purposes_user
PURPOSES_DB_PASSWORD=purposes_password
PURPOSES_DB_NAME=purposes_db

# notification-service
NOTIFICATION_DATABASE_URL=postgresql+asyncpg://notification_user:notification_pass@notification-db:5432/notification_db
NOTIFICATION_DB_USER=notification_user
NOTIFICATION_DB_PASSWORD=notification_pass
NOTIFICATION_DB_NAME=notification_db

# history-service
HISTORY_DATABASE_URL=postgresql+asyncpg://history_user:history_password@history-db:5432/history_db
HISTORY_DB_USER=history_user
HISTORY_DB_PASSWORD=history_password
HISTORY_DB_NAME=history_db
```

---

## Порты сервисов

```env
GATEWAY_PORT=8000
USERS_SERVICE_PORT=8001
TRANSACTIONS_SERVICE_PORT=8002
IMAGES_SERVICE_PORT=8003
PSEUDO_BANK_SERVICE_PORT=8004
PURPOSES_SERVICE_PORT=8005
NOTIFICATION_SERVICE_PORT=8006
HISTORY_SERVICE_PORT=8007
```

---

## URL сервисов (внутри Docker-сети)

```env
USERS_SERVICE_URL=http://users-service:8001
TRANSACTIONS_SERVICE_URL=http://transactions-service:8002
IMAGES_SERVICE_URL=http://images-service:8003
PSEUDO_BANK_SERVICE_URL=http://pseudo-bank-service:8004
PURPOSES_SERVICE_URL=http://purposes-service:8005
NOTIFICATION_SERVICE_URL=http://notification-service:8006
HISTORY_SERVICE_URL=http://history-service:8007
```

Имена хостов (`users-service`, `transactions-service` и т.д.) — это имена сервисов в `docker-compose.yml`. Используются только внутри Docker-сети.

---

## Redis

```env
REDIS_URL=redis://redis:6379
```

---

## Тестовое окружение (.env.test)

Тестовый стек использует изолированные порты, чтобы не конфликтовать с продакшн-стеком:

| Ресурс | Prod порт | Test порт |
|--------|-----------|-----------|
| Gateway | 8000 | 18000 |
| users-service | 8001 | 18001 |
| transactions-service | 8002 | 18002 |
| images-service | 8003 | 18003 |
| pseudo-bank-service | 8004 | 18004 |
| purposes-service | 8005 | 18005 |
| notification-service | 8006 | 18006 |
| history-service | 8007 | 18007 |
| users-db | 5433 | 15433 |
| transactions-db | 5434 | 15434 |
| images-db | 5435 | 15435 |
| pseudo-bank-db | 5436 | 15436 |
| purposes-db | 5437 | 15437 |
| notification-db | 5438 | 15438 |
| history-db | 5439 | 15439 |
| Redis | 6379 | 17379 |
| Grafana | 3000 | 13000 |
| Prometheus | 9090 | 19090 |

Docker Compose проект тестового стека: `smartbudget-test` (чтобы не пересекаться с продакшном).

---

## Связанные разделы

- [Быстрый старт](quickstart.md)
- [Docker Compose стек](docker-compose.md)
- [Справочник Makefile](makefile-reference.md)
