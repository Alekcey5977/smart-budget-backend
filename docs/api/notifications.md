[Документация](../README.md) / [API](index.md) / Уведомления

# API: Уведомления

## GET /notifications/user/me

Получить список уведомлений текущего пользователя с пагинацией.

**Заголовок:** `Authorization: Bearer {access_token}`

**Query параметры:**
- `?limit=20` — количество (default: 20)
- `?offset=0` — смещение (default: 0)

**Ответ 200:**
```json
{
  "items": [
    {
      "id": "uuid",
      "title": "Цель «Отпуск» — 80%!",
      "body": "Вы достигли 80% цели «Отпуск в Турции». Продолжайте!",
      "is_read": false,
      "created_at": "2024-01-20T15:30:00"
    }
  ],
  "total": 5,
  "limit": 20,
  "offset": 0
}
```

---

## GET /notifications/user/me/unread/count

Количество непрочитанных уведомлений (для бейджа в интерфейсе).

**Заголовок:** `Authorization: Bearer {access_token}`

**Ответ 200:**
```json
{"unread_count": 3}
```

---

## GET /notifications/{id}

Получить уведомление по ID.

**Заголовок:** `Authorization: Bearer {access_token}`

**Ответ 200:** объект уведомления

---

## POST /notifications/{id}/mark-as-read

Отметить уведомление как прочитанное.

**Заголовок:** `Authorization: Bearer {access_token}`

**Ответ 200:**
```json
{"detail": "Notification marked as read"}
```

---

## POST /notifications/mark-all-as-read

Отметить все уведомления пользователя как прочитанные.

**Заголовок:** `Authorization: Bearer {access_token}`

**Ответ 200:**
```json
{"detail": "All notifications marked as read"}
```

---

## DELETE /notifications/{id}

Удалить уведомление.

**Заголовок:** `Authorization: Bearer {access_token}`

**Ответ 200:**
```json
{"detail": "Notification deleted"}
```

---

## Связанные разделы

- [Notification Service](../services/notification-service.md)
- [API: WebSocket](websocket.md) — real-time уведомления
- [API: Финансовые цели](purposes.md)
