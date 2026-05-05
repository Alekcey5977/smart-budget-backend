[Документация](../README.md) / [Сервисы](gateway.md) / Users Service

# Users Service

**Порт:** 8001 | **БД:** PostgreSQL :5433 (users_db)

Управляет пользователями: регистрация, аутентификация, профиль, банковские счета. Единственный сервис, выдающий JWT-токены.

---

## Компоненты

| Компонент | Библиотека | Детали |
|-----------|-----------|--------|
| JWT | python-jose | HS256, access: 15 мин, refresh: 7 дней |
| Пароли | passlib + argon2-cffi | argon2 hash |
| Хэширование счетов | hmac (stdlib) | HMAC-SHA256(account_number, BANK_SECRET_KEY) |
| Кэш | Redis Cache-Aside | ключ `bank_accounts:{user_id}`, TTL 300 сек |

---

## Эндпоинты

| Метод | Путь | Описание | Аутентификация |
|-------|------|----------|----------------|
| `POST` | `/users/register` | Регистрация нового пользователя | — |
| `POST` | `/users/login` | Логин, выдача токенов | — |
| `POST` | `/users/refresh` | Обновление access token | refresh_token cookie |
| `POST` | `/users/logout` | Выход, удаление refresh токена | — |
| `GET` | `/users/me` | Получить профиль | JWT |
| `PUT` | `/users/me` | Обновить профиль | JWT + refresh cookie |
| `POST` | `/me/bank_account` | Добавить банковский счёт | JWT |
| `GET` | `/me/bank_accounts` | Список счетов пользователя | JWT |
| `PATCH` | `/me/bank_account/{id}` | Переименовать счёт | JWT |
| `DELETE` | `/me/bank_account/{id}` | Удалить счёт | JWT |

*Примечание: Gateway обращается к этим эндпоинтам с `Bearer` токеном, клиент работает только через Gateway.*

---

## JWT Flow

```mermaid
sequenceDiagram
    autonumber
    participant C as 📱 Client
    participant G as 🚪 Gateway
    participant U as 👤 users-service

    Note over C,U: 🔐 LOGIN
    C->>G: POST /auth/login (email, password)
    G->>U: POST /users/login
    U->>U: verify password
    U->>U: generate tokens
    U-->>G: access_token + refresh_token (cookie)
    G-->>C: access_token + refresh_token (cookie)

    Note over C,U: 🔄 REFRESH
    C->>G: POST /auth/refresh (cookie)
    G->>U: POST /users/refresh
    U->>U: decode + rotate
    U-->>G: new tokens
    G-->>C: new tokens
```

**JTI-binding:** каждый access token хранит `refresh_jti` — ID соответствующего refresh token. Это позволяет инвалидировать access token при замене refresh токена.

---

## Добавление банковского счёта

```mermaid
sequenceDiagram
    autonumber
    participant GW as 🚪 Gateway
    participant US as 👤 users-service
    participant PBS as 🏦 pseudo-bank-service
    participant Redis as 🧠 Redis

    Note over GW,Redis: ➕ ADD BANK ACCOUNT
    GW->>US: POST /me/bank_account {number, name, bank}
    US->>US: HMAC-SHA256(number) → hash
    US->>PBS: POST /validate_account {hash}
    PBS-->>US: {currency, balance} или 404
    US->>US: INSERT INTO bank_accounts
    US->>Redis: DEL bank_accounts:{user_id}
    US->>Redis: XADD domain-events {bank_account.added}
    US-->>GW: {id, name, currency, bank, balance}

    Note over Redis: 📢 AFTER EVENT:
    Note over Redis: → transactions-service: sync
    Note over Redis: → history-service: "Account {bank} added"
```

---

## Публикуемые события

| Событие | Триггер |
|---------|---------|
| `user.registered` | POST /users/register |
| `user.updated` | PUT /users/me |
| `bank_account.added` | POST /me/bank_account |
| `bank_account.renamed` | PATCH /me/bank_account/{id} |
| `bank_account.deleted` | DELETE /me/bank_account/{id} |

---

## Переменные окружения

| Переменная | Описание |
|-----------|----------|
| `USERS_DATABASE_URL` | postgresql+asyncpg://users_user:pass@users-db:5432/users_db |
| `ACCESS_SECRET_KEY` | Ключ подписи access JWT |
| `REFRESH_SECRET_KEY` | Ключ подписи refresh JWT |
| `BANK_SECRET_KEY` | HMAC-ключ для хэширования номеров счетов |
| `PSEUDO_BANK_SERVICE_URL` | URL для валидации счетов |
| `REDIS_URL` | Redis для кэша и публикации событий |

---

## Связанные разделы

- [API: Аутентификация](../api/auth.md)
- [API: Банковские счета](../api/bank-accounts.md)
- [Модели данных: users_db](../architecture/data-model.md)
- [Pseudo Bank Service](pseudo-bank-service.md)
