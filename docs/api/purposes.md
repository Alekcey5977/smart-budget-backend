[Документация](../README.md) / [API](index.md) / Финансовые цели

# API: Финансовые цели

## POST /purposes/create

Создать новую сберегательную цель.

**Заголовок:** `Authorization: Bearer {access_token}`

**Тело запроса:**
```json
{
  "title": "Отпуск в Турции",
  "deadline": "2024-07-01T00:00:00",
  "total_amount": 150000.00,
  "amount": 25000.00
}
```

| Поле | Тип | Обязательно | Описание |
|------|-----|-------------|----------|
| `title` | string | да | Название цели |
| `deadline` | datetime | да | Дата, к которой нужно накопить |
| `total_amount` | decimal | да | Целевая сумма |
| `amount` | decimal | нет | Уже накоплено (default: 0) |

**Ответ 200:**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "title": "Отпуск в Турции",
  "deadline": "2024-07-01T00:00:00",
  "total_amount": 150000.00,
  "amount": 25000.00,
  "created_at": "2024-01-15T10:00:00",
  "updated_at": null
}
```

---

## GET /purposes/my

Получить список всех целей пользователя. Ответ кэшируется в Redis на 30 секунд.

**Заголовок:** `Authorization: Bearer {access_token}`

**Ответ 200:** массив объектов целей

---

## PUT /purposes/update/{id}

Обновить цель. При пересечении порогов прогресса (25%, 50%, 80%, 100%) создаётся уведомление.

**Заголовок:** `Authorization: Bearer {access_token}`

**Тело запроса** (все поля опциональны):
```json
{
  "title": "Отпуск в Греции",
  "deadline": "2024-08-01T00:00:00",
  "total_amount": 200000.00,
  "amount": 160000.00
}
```

**Ответ 200:** обновлённый объект цели

**Пример:** если `amount` меняется с `60 000` до `120 000` при `total_amount=150 000`:
- Старый прогресс: 40%
- Новый прогресс: 80%
- Пересечён порог **50%** и **80%** → два уведомления

---

## DELETE /purposes/delete/{id}

Удалить цель.

**Заголовок:** `Authorization: Bearer {access_token}`

**Ответ 200:**
```json
{"detail": "Purpose deleted"}
```

**После удаления:** публикуется событие `purpose.deleted` → history-service записывает "Цель «{name}» удалена".

---

## Связанные разделы

- [Purposes Service](../services/purposes-service.md)
- [API: Уведомления](notifications.md)
