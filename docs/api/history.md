[Документация](../README.md) / [API](index.md) / История действий

# API: История действий

## GET /history/user/me

Получить историю действий пользователя с пагинацией. Записи создаются автоматически при системных событиях.

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
      "title": "Синхронизация завершена",
      "body": "Загружено новых транзакций: 47",
      "created_at": "2024-01-20T15:30:00"
    },
    {
      "id": "uuid",
      "title": "Счёт добавлен",
      "body": "Банковский счёт «Сбербанк» успешно привязан",
      "created_at": "2024-01-19T10:00:00"
    }
  ],
  "total": 12,
  "limit": 20,
  "offset": 0
}
```

---

## GET /history/{id}

Получить запись истории по ID.

**Заголовок:** `Authorization: Bearer {access_token}`

**Ответ 200:** объект записи истории

---

## DELETE /history/{id}

Удалить запись из истории.

**Заголовок:** `Authorization: Bearer {access_token}`

**Ответ 200:**
```json
{"detail": "History entry deleted"}
```

---

## Типы записей истории

| Заголовок | Когда создаётся |
|-----------|-----------------|
| Профиль обновлён | PUT /auth/me |
| Аватар обновлён | PUT /images/avatars/me |
| Счёт добавлен | POST /users/me/bank_account |
| Счёт удалён | DELETE /users/me/bank_account/{id} |
| Счёт переименован | PATCH /users/me/bank_account/{id} |
| Цель создана | POST /purposes/create |
| Цель обновлена | PUT /purposes/update/{id} |
| Цель удалена | DELETE /purposes/delete/{id} |
| Категория изменена | PATCH /transactions/{id}/category |
| Синхронизация завершена | Авто каждые 10 мин |

---

## Связанные разделы

- [History Service](../services/history-service.md)
- [API: WebSocket](websocket.md) — real-time история
- [Система событий](../architecture/event-system.md)
