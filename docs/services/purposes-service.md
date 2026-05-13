[Документация](../README.md) / [Сервисы](gateway.md) / Purposes Service

# Purposes Service (Финансовые цели)

**Порт:** 8005 | **БД:** PostgreSQL :5437 (purposes_db)

Управляет сберегательными целями пользователей. Отслеживает прогресс накопления и публикует уведомления при достижении ключевых порогов.

---

## Модель цели (Purpose)

```
id            UUID PK           — уникальный идентификатор
user_id       INT               — ID пользователя
title         VARCHAR           — название цели ("Отпуск в Турции")
deadline      DATETIME          — дата достижения цели
total_amount  DECIMAL(12,2)     — целевая сумма накопления
amount        DECIMAL(12,2)     — накоплено на данный момент (default: 0)
created_at    DATETIME
updated_at    DATETIME
```

**Прогресс:** `progress_percent = (amount / total_amount) * 100`

---

## Логика уведомлений о прогрессе

При каждом обновлении цели (`PUT /purpose/update/{id}`) сервис вычисляет, были ли пересечены пороговые значения:

```python
THRESHOLDS = [25, 50, 80, 100]

def get_crossed_thresholds(old_amount, new_amount, total_amount):
    old_pct = (old_amount / total_amount) * 100
    new_pct = (new_amount / total_amount) * 100
    return [t for t in THRESHOLDS if old_pct < t <= new_pct]
```

При пересечении порога публикуется событие `purpose.progress`:
```json
{
  "user_id": 42,
  "purpose_name": "Отпуск в Турции",
  "progress_percent": 80,
  "threshold": 80
}
```

notification-service создаёт уведомление: *"Цель «Отпуск в Турции» достигла 80%!"*

---

## Эндпоинты

| Метод | Путь | Описание | Auth |
|-------|------|----------|------|
| `POST` | `/purpose/create` | Создать цель | X-User-ID |
| `GET` | `/purpose/my` | Список целей пользователя | X-User-ID |
| `PUT` | `/purpose/update/{id}` | Обновить цель | X-User-ID |
| `DELETE` | `/purpose/delete/{id}` | Удалить цель | X-User-ID |

### Создание цели (POST /purpose/create)

```json
{
  "title": "Отпуск в Турции",
  "deadline": "2024-07-01T00:00:00",
  "total_amount": 150000.00,
  "amount": 25000.00
}
```

### Ответ (GET /purpose/my)

```json
[
  {
    "id": "uuid",
    "title": "Отпуск в Турции",
    "deadline": "2024-07-01T00:00:00",
    "total_amount": 150000.00,
    "amount": 25000.00,
    "created_at": "2024-01-15T10:00:00",
    "updated_at": null
  }
]
```

---

## Кэш Redis

| Ключ | TTL | Описание |
|------|-----|----------|
| `purposes:{user_id}` | 30 сек | Список целей пользователя |

Кэш инвалидируется при любой операции create/update/delete.

---

## Публикуемые события

| Событие | Триггер | Payload |
|---------|---------|---------|
| `purpose.created` | POST /purpose/create | `{user_id, name, target_amount, deadline}` |
| `purpose.updated` | PUT /purpose/update/{id} | `{user_id, name}` |
| `purpose.deleted` | DELETE /purpose/delete/{id} | `{user_id, name, target_amount}` |
| `purpose.progress` | PUT (при пересечении порога) | `{user_id, purpose_name, progress_percent, threshold}` |

---

## Переменные окружения

| Переменная | Описание |
|-----------|----------|
| `PURPOSES_DATABASE_URL` | postgresql+asyncpg://purposes_user:pass@purposes-db:5432/purposes_db |
| `REDIS_URL` | Redis для кэша и событий |

---

## Связанные разделы

- [API: Финансовые цели](../api/purposes.md)
- [Notification Service](notification-service.md)
- [Система событий](../architecture/event-system.md)
