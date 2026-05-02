[Документация](../README.md) / [Сервисы](gateway.md) / History Service

# History Service

**Порт:** 8007 | **БД:** PostgreSQL :5439 (history_db)

Ведёт аудит-трейл всех значимых действий пользователя. Полностью event-driven: не содержит бизнес-логики, только записывает и отдаёт историю. Поддерживает real-time доставку через WebSocket.

---

## Принцип работы

История создаётся **исключительно** через события Redis Streams. Сервис:
1. Слушает стрим `domain-events` (consumer group: `history-group`)
2. Для каждого события создаёт читаемую запись на русском языке
3. Сохраняет в `history_db`
4. Рассылает по активным WebSocket-соединениям

---

## Обрабатываемые события

| Событие | Заголовок | Тело |
|---------|-----------|------|
| `user.updated` | "Профиль обновлён" | "Данные профиля были изменены" |
| `user.avatar.updated` | "Аватар обновлён" | "Фотография профиля была изменена" |
| `bank_account.added` | "Счёт добавлен" | "Банковский счёт «{bank_name}» успешно привязан" |
| `bank_account.deleted` | "Счёт удалён" | "Банковский счёт «{bank_name}» был отвязан" |
| `bank_account.renamed` | "Счёт переименован" | "Банковский счёт переименован" |
| `purpose.created` | "Цель создана" | "Создана финансовая цель «{name}» на {target_amount} ₽" |
| `purpose.updated` | "Цель обновлена" | "Финансовая цель «{name}» изменена" |
| `purpose.deleted` | "Цель удалена" | "Финансовая цель «{name}» удалена" |
| `transaction.category.updated` | "Категория изменена" | "Категория транзакции изменена: {old} → {new}" |
| `sync.completed` | "Синхронизация завершена" | "Загружено новых транзакций: {count}" |

---

## WebSocket

**Подключение:**
```
ws://localhost:8000/ws/history?token={access_token}
```

Gateway проксирует к `ws://history-service:8007/ws/history?token=...`

Архитектура аналогична notification-service: `active_connections: dict[user_id, list[WebSocket]]`.

**Формат сообщения через WS:**
```json
{
  "id": "uuid",
  "title": "Синхронизация завершена",
  "body": "Загружено новых транзакций: 47",
  "created_at": "2024-01-20T15:30:00"
}
```

---

## Эндпоинты

| Метод | Путь | Описание | Auth |
|-------|------|----------|------|
| `GET` | `/history/user/me` | Список записей истории (пагинация) | X-User-ID |
| `GET` | `/history/{id}` | Запись по ID | — |
| `DELETE` | `/history/{id}` | Удалить запись | X-User-ID |
| `WS` | `/ws/history?token=` | Real-time поток истории | JWT |

---

## Аутентификация в сервисе

Аналогично notification-service:
- REST: `X-User-ID` заголовок от Gateway
- WebSocket: декодирование JWT из `?token=` с `ACCESS_SECRET_KEY`

---

## Переменные окружения

| Переменная | Описание |
|-----------|----------|
| `HISTORY_DATABASE_URL` | postgresql+asyncpg://history_user:pass@history-db:5432/history_db |
| `ACCESS_SECRET_KEY` | Ключ для проверки JWT в WS |
| `REDIS_URL` | Redis Stream для получения событий |

---

## Связанные разделы

- [API: История](../api/history.md)
- [API: WebSocket](../api/websocket.md)
- [Система событий](../architecture/event-system.md)
- [Notification Service](notification-service.md)
