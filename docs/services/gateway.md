[Документация](../README.md) / [Сервисы](users-service.md) / Gateway

# Gateway Service

**Порт:** 8000 | **Swagger UI:** http://localhost:8000/docs

Gateway — единственная точка входа для клиентских запросов. Выполняет JWT-аутентификацию, маршрутизирует HTTP-запросы к микросервисам и проксирует WebSocket-соединения.

---

## Роли и ответственность

| Роль | Реализация |
|------|-----------|
| Reverse proxy | `httpx.AsyncClient` с keepalive-пулом (200 соединений, 20 keepalive) |
| JWT-аутентификация | Локальная проверка подписи (`ACCESS_SECRET_KEY`), без вызова users-service |
| WebSocket прокси | Двунаправленное проксирование к notification-service и history-service |
| Метрики | `prometheus-fastapi-instrumentator` — экспозиция на `/metrics` |

---

## Маршруты

| Router | Prefix | Целевой сервис | Защита |
|--------|--------|----------------|--------|
| `auth.py` | `/auth` | users-service | частично (см. ниже) |
| `bank_accounts.py` | `/users/me` | users-service | JWT |
| `transactions.py` | `/transactions` | transactions-service | JWT |
| `sync.py` | `/sync` | transactions-service | JWT |
| `images.py` | `/images` | images-service | частично |
| `purposes.py` | `/purposes` | purposes-service | JWT |
| `notifications.py` | `/notifications` | notification-service | JWT |
| `history.py` | `/history` | history-service | JWT |
| `websocket.py` | `/ws` | notification/history | JWT (query param) |

---

## Аутентификация

### Лёгкая (`get_current_user`)
Применяется на большинстве защищённых эндпоинтов. Декодирует JWT локально, HTTP-вызова нет.

```
Входящий запрос: Authorization: Bearer <token>
                 или ?token=<token>
↓
Декодирование JWT: jose.decode(token, ACCESS_SECRET_KEY, algorithms=["HS256"])
↓
Возвращает: {token, user_id, user: None}
↓
Проксирование: добавляет заголовок X-User-ID: {user_id}
```

### Полная (`get_current_user_with_profile`)
Только для `GET /auth/me` и `PUT /auth/me`. Включает получение профиля.

```
1. JWT → user_id (локально)
2. Redis CACHE: GET user:profile:{user_id}  (TTL 300 сек)
   ✓ HIT  → вернуть {token, user_id, user: {...}}
   ✗ MISS → GET /users/me к users-service → кэшировать → вернуть
```

---

## Проксирование HTTP

Gateway пересылает тело запроса «as is», добавляя заголовки:

```http
X-User-ID: 42
Authorization: Bearer eyJ...   (только для /users/me — users-service)
```

Таймауты: `15–30 секунд` в зависимости от операции.

При недоступности downstream-сервиса: `503 Service Unavailable`.

---

## WebSocket прокси

```
ws://gateway:8000/ws/notification?token={jwt_access_token}
ws://gateway:8000/ws/history?token={jwt_access_token}
```

Схема работы:
1. Клиент открывает WS-соединение с Gateway
2. Gateway проверяет JWT из `?token=`
3. При невалидном токене: закрывает с кодом `4001`
4. При успехе: открывает WS-соединение к целевому сервису
5. Двунаправленное проксирование через `asyncio.wait(FIRST_COMPLETED)`
6. При разрыве любой стороны — закрывает обе

---

## Переменные окружения

| Переменная | Пример | Описание |
|-----------|--------|----------|
| `ACCESS_SECRET_KEY` | `your-secret` | Ключ подписи JWT |
| `USERS_SERVICE_URL` | `http://users-service:8001` | URL users-service |
| `TRANSACTIONS_SERVICE_URL` | `http://transactions-service:8002` | URL transactions-service |
| `IMAGES_SERVICE_URL` | `http://images-service:8003` | URL images-service |
| `PURPOSES_SERVICE_URL` | `http://purposes-service:8005` | URL purposes-service |
| `NOTIFICATION_SERVICE_URL` | `http://notification-service:8006` | URL notification-service |
| `HISTORY_SERVICE_URL` | `http://history-service:8007` | URL history-service |
| `REDIS_URL` | `redis://redis:6379` | Redis для кэша профиля |

---

## Связанные разделы

- [Карта сервисов и маршрутизация](../architecture/services-map.md)
- [API: Обзор](../api/index.md)
- [API: Аутентификация](../api/auth.md)
- [API: WebSocket](../api/websocket.md)
