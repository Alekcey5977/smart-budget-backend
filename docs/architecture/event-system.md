[Документация](../README.md) / [Архитектура](overview.md) / Система событий

# Система событий (Redis Streams)

## Назначение

Асинхронная шина событий развязывает сервисы при побочных эффектах. Когда бизнес-операция производит событие (добавление счёта, синхронизация, обновление цели), публикующий сервис не знает и не ждёт, кто его обработает.

**Паттерн:** один publisher → Redis Stream `domain-events` → несколько consumer groups.

---

## Схема потока

```mermaid
flowchart LR
    subgraph "1. Публикация"
        A[Любой сервис] -->|XADD| B[(Redis Stream<br/>domain-events)]
    end

    subgraph "2. Consumer Groups"
        B -->|XREADGROUP| C[notification-group]
        B -->|XREADGROUP| D[history-group]
        B -->|XREADGROUP| E[transactions-group]
    end

    subgraph "3. Обработка"
        C -->|сохранить + WS| F[(БД)]
        D -->|сохранить + WS| G[(БД)]
        E -->|sync с банком| H[(БД)]
    end

    subgraph "4. Подтверждение"
        F -.->|XACK| B
        G -.->|XACK| B
        H -.->|XACK| B
    end

    style A fill:#e3f2fd,stroke:#1565c0,stroke-width:2px,color:#000
    style B fill:#f5f5f5,stroke:#9e9e9e,stroke-width:2px,color:#000
    style C fill:#e8f5e9,stroke:#2e7d32,stroke-width:2px,color:#000
    style D fill:#e8f5e9,stroke:#2e7d32,stroke-width:2px,color:#000
    style E fill:#e8f5e9,stroke:#2e7d32,stroke-width:2px,color:#000
    style F fill:#fce4ec,stroke:#c62828,stroke-width:2px,color:#000
    style G fill:#fce4ec,stroke:#c62828,stroke-width:2px,color:#000
    style H fill:#fce4ec,stroke:#c62828,stroke-width:2px,color:#000
```

---

## Схема DomainEvent

```python
class DomainEvent(BaseModel):
    event_id:   UUID      # Уникальный ID события (uuid4)
    event_type: str       # Тип: "user.registered", "sync.completed", и т.д.
    source:     str       # Сервис-источник: "users-service", "purposes-service"
    timestamp:  datetime  # Время создания события (UTC)
    payload:    dict      # Произвольные данные события
```

Событие сериализуется в JSON и записывается в Redis Stream как одно поле `payload`.

---

## Каталог событий

| event_type | Источник | Слушатели | Payload |
|-----------|----------|-----------|---------|
| `user.registered` | users-service | notification-service | `{user_id, first_name}` |
| `user.updated` | users-service | history-service | `{user_id}` |
| `user.avatar.updated` | images-service | history-service | `{user_id}` |
| `bank_account.added` | users-service | transactions-service, history-service | `{user_id, bank_account_hash, bank_name}` |
| `bank_account.deleted` | users-service | history-service | `{user_id, bank_name}` |
| `bank_account.renamed` | users-service | transactions-service, history-service | `{bank_account_hash, new_name}` |
| `purpose.created` | purposes-service | history-service | `{user_id, name, target_amount, deadline}` |
| `purpose.updated` | purposes-service | history-service | `{user_id, name}` |
| `purpose.deleted` | purposes-service | history-service | `{user_id, name, target_amount}` |
| `purpose.progress` | purposes-service | notification-service | `{user_id, purpose_name, progress_percent, threshold}` |
| `transaction.category.updated` | transactions-service | history-service | `{user_id, old_category_name, new_category_name}` |
| `sync.completed` | transactions-service | history-service | `{user_id, new_transactions_count, synced_at}` |

---

## Consumer Groups

| Группа | Сервис | Имя консьюмера |
|--------|--------|----------------|
| `notification-group` | notification-service | `notification-service-consumer` |
| `history-group` | history-service | `history-service-consumer` |
| `transactions-group` | transactions-service | `transactions-service-consumer` |

Каждая группа независимо читает все события из стрима. Одно событие обрабатывается каждой группой ровно один раз (at-least-once delivery).

---

## EventPublisher

Класс `EventPublisher` из `shared/event_publisher.py` используется всеми сервисами-источниками.

**Инициализация** (один раз в `lifespan` сервиса):
```python
await EventPublisher.connect()  # создаёт общий пул соединений
# ...
await EventPublisher.close()    # при остановке
```

**Публикация события:**
```python
publisher = EventPublisher()
await publisher.publish(DomainEvent(
    event_id=uuid4(),
    event_type="bank_account.added",
    source="users-service",
    timestamp=datetime.utcnow(),
    payload={"user_id": 42, "bank_account_hash": "0eb1e1...", "bank_name": "Сбербанк"},
))
```

Если `connect()` не вызывался (например, в тестах), создаётся временное соединение автоматически (fallback).

---

## Механизм надёжности

**At-least-once delivery:**
- Консьюмер читает сообщения через `XREADGROUP` с `>` (только новые)
- После успешной обработки отправляет `XACK` — сообщение считается доставленным
- При ошибке обработки `XACK` не отправляется → сообщение остаётся в PEL (Pending Entry List)
- При переподключении консьюмер продолжит с того места, где остановился

**Reconnect loop:**
- При разрыве соединения: задержка 2 секунды, повторная попытка
- При повторной ошибке: задержка 5 секунд
- `mkstream=True` при создании группы — стрим создаётся автоматически если не существует

**Параллельность:**
- `block=5000` — блокирующее чтение с таймаутом 5 секунд
- Максимум 10 сообщений за одну итерацию (`count=10`)

---

## Доставка через WebSocket

После сохранения уведомления/записи истории в БД, сервис рассылает событие по активным WebSocket-соединениям:

```mermaid
sequenceDiagram
    autonumber
    participant Redis as 📦 Redis Stream
    participant EL as ⚙️ EventListener
    participant DB as 💾 notification_db
    participant WS as 🔌 Connection Manager
    participant Client as 🖥️ Клиент

    Note over Redis,EL: 1. Получение
    Redis->>EL: XREADGROUP purpose.progress
    
    Note over EL,DB: 2. Сохранение
    EL->>DB: INSERT INTO notifications
    DB-->>EL: notification_id
    
    Note over EL,WS: 3. Поиск соединений
    EL->>WS: get_connections(user_id)
    WS-->>EL: [websocket1, websocket2]
    
    Note over WS,Client: 4. Отправка
    WS->>Client: send_json({id, title, body, is_read, created_at})
    
    Note over EL,Redis: 5. Подтверждение
    EL->>Redis: XACK
```

Если пользователь не подключён по WS — уведомление сохраняется в БД и будет доступно при следующем открытии приложения через `GET /notifications/user/me`.

---

## Связанные разделы

- [Обзор архитектуры](overview.md)
- [Notification Service](../services/notification-service.md)
- [History Service](../services/history-service.md)
- [Transactions Service](../services/transactions-service.md)
