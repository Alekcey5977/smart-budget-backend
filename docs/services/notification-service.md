[Документация](../README.md) / [Сервисы](gateway.md) / Notification Service

# Notification Service

**Порт:** 8006 | **БД:** PostgreSQL :5438 (notification_db)

Хранит уведомления пользователей и доставляет их в реальном времени через WebSocket. Полностью event-driven: создаёт уведомления только в ответ на доменные события.

---

## Архитектура доставки

```mermaid
sequenceDiagram
    autonumber
    participant Redis as 🧠 Redis Stream<br/>domain-events
    participant EL as 🎧 EventListener<br/>(notification-group)
    participant DB as 🗄️ notification_db
    participant WS as 🔌 Connection Manager<br/>{user_id → [WebSocket]}
    participant Client as 📱 Client

    Note over Redis,Client: 📨 NOTIFICATION HANDLING

    Redis->>EL: XREADGROUP (purpose.progress / user.registered)
    EL->>DB: INSERT INTO notifications {title, body, user_id}
    EL->>WS: get_connections(user_id)
    
    alt ✅ Active WS connection exists
        WS->>Client: send_json(notification)
        Client-->>WS: ✓ delivered
    else ❌ No connection
        Note over DB: Notification saved,<br/>available via REST API
    end
    
    EL->>Redis: XACK ✅
```

---

## Обрабатываемые события

| Событие | Заголовок уведомления | Тело |
|---------|----------------------|------|
| `user.registered` | "Добро пожаловать в SmartBudget!" | "Привет, {first_name}! Ваш аккаунт успешно создан." |
| `purpose.progress` | "Цель «{name}» — {threshold}%!" | "Вы достигли {threshold}% цели «{name}». Продолжайте!" |

---

## WebSocket

**Подключение:**
```
ws://localhost:8000/ws/notification?token={access_token}
```

Gateway проксирует соединение к `ws://notification-service:8006/ws/notification?token=...`

**active_connections** — словарь `dict[user_id: int, list[WebSocket]]`. Один пользователь может иметь несколько активных соединений (например, мобильное + веб). Уведомление рассылается по всем.

**Формат сообщения через WS:**
```json
{
  "id": "uuid",
  "title": "Цель «Отпуск» — 80%!",
  "body": "Вы достигли 80% цели «Отпуск в Турции». Продолжайте!",
  "is_read": false,
  "created_at": "2024-01-20T15:30:00"
}
```

---

## Эндпоинты

| Метод | Путь | Описание | Auth |
|-------|------|----------|------|
| `GET` | `/notifications/user/me` | Список уведомлений (пагинация) | X-User-ID |
| `GET` | `/notifications/user/me/unread/count` | Количество непрочитанных | X-User-ID |
| `GET` | `/notifications/{id}` | Уведомление по ID | — |
| `POST` | `/notifications/{id}/mark-as-read` | Отметить как прочитанное | X-User-ID |
| `POST` | `/notifications/mark-all-as-read` | Отметить все прочитанными | X-User-ID |
| `DELETE` | `/notifications/{id}` | Удалить уведомление | X-User-ID |
| `WS` | `/ws/notification?token=` | Real-time поток уведомлений | JWT |

---

## Аутентификация в сервисе

Сервис выполняет собственную JWT-проверку для WebSocket (не зависит от Gateway):
- Декодирует `token` из query параметра с `ACCESS_SECRET_KEY`
- Закрывает соединение с кодом `4001` при невалидном токене

Для REST эндпоинтов — проверяет `X-User-ID` заголовок от Gateway.

---

## Переменные окружения

| Переменная | Описание |
|-----------|----------|
| `NOTIFICATION_DATABASE_URL` | postgresql+asyncpg://notification_user:pass@notification-db:5432/notification_db |
| `ACCESS_SECRET_KEY` | Ключ для проверки JWT в WS |
| `REDIS_URL` | Redis Stream для получения событий |

---

## Связанные разделы

- [API: Уведомления](../api/notifications.md)
- [API: WebSocket](../api/websocket.md)
- [Система событий](../architecture/event-system.md)
- [History Service](history-service.md)
