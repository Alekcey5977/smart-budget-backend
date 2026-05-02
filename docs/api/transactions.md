[Документация](../README.md) / [API](index.md) / Транзакции

# API: Транзакции

## POST /transactions/

Получить список транзакций с фильтрацией и пагинацией.

**Заголовок:** `Authorization: Bearer {access_token}`

**Тело запроса** (все поля опциональны):
```json
{
  "transaction_type": "expense",
  "category_ids": [1, 5, 10],
  "bank_account_ids": [3, 7],
  "start_date": "2024-01-01T00:00:00",
  "end_date": "2024-12-31T23:59:59",
  "min_amount": 100.0,
  "max_amount": 50000.0,
  "merchant_ids": [42, 55],
  "limit": 20,
  "offset": 0
}
```

| Поле | Тип | Описание |
|------|-----|----------|
| `transaction_type` | string | `"income"` или `"expense"`, null = все |
| `category_ids` | int[] | Фильтр по категориям |
| `bank_account_ids` | int[] | Фильтр по счетам |
| `start_date` | datetime | Транзакции с этой даты |
| `end_date` | datetime | Транзакции до этой даты |
| `min_amount` | decimal | Минимальная сумма |
| `max_amount` | decimal | Максимальная сумма |
| `merchant_ids` | int[] | Фильтр по мерчантам |
| `limit` | int | 1–100, default=20 |
| `offset` | int | Для пагинации, default=0 |

**Ответ 200:**
```json
{
  "items": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "amount": 1500.00,
      "type": "expense",
      "description": "Пятёрочка",
      "created_at": "2024-01-15T14:30:00",
      "category": {
        "id": 5,
        "name": "Продукты",
        "type": "expense"
      },
      "merchant": {
        "id": 42,
        "name": "Пятёрочка",
        "inn": "7728539850"
      },
      "bank_account": {
        "id": 1,
        "bank_account_name": "Моя карта",
        "currency": "RUB"
      }
    }
  ],
  "total": 250,
  "limit": 20,
  "offset": 0
}
```

---

## GET /transactions/{id}

Получить транзакцию по UUID.

**Заголовок:** `Authorization: Bearer {access_token}`

**Ответ 200:** объект транзакции (аналогично элементу из списка)

**Ошибки:** `403` — транзакция принадлежит другому пользователю, `404` — не найдена

---

## PATCH /transactions/{id}/category

Изменить категорию транзакции.

**Заголовок:** `Authorization: Bearer {access_token}`

**Тело запроса:**
```json
{
  "category_id": 7
}
```

**Ответ 200:** обновлённый объект транзакции

**После изменения:** публикуется событие `transaction.category.updated` → history-service записывает "Категория изменена: {старая} → {новая}".

---

## GET /transactions/categories

Справочник всех категорий. Кэшируется в Redis на 12 часов.

**Query параметры:**
- `?type=income` — только категории доходов
- `?type=expense` — только категории расходов
- (без параметра) — все категории

**Ответ 200:**
```json
[
  {"id": 1, "name": "Зарплата", "type": "income"},
  {"id": 5, "name": "Продукты", "type": "expense"},
  {"id": 6, "name": "Транспорт", "type": "expense"}
]
```

---

## GET /transactions/categories/{id}

Получить категорию по ID.

**Ответ 200:**
```json
{"id": 5, "name": "Продукты", "type": "expense"}
```

---

## POST /transactions/categories/summary

Сводка расходов/доходов по категориям за период.

**Заголовок:** `Authorization: Bearer {access_token}`

**Тело запроса:**
```json
{
  "transaction_type": "expense",
  "start_date": "2024-01-01T00:00:00",
  "end_date": "2024-01-31T23:59:59",
  "bank_account_ids": [1]
}
```

**Ответ 200** (отсортировано по убыванию суммы):
```json
[
  {
    "category_id": 5,
    "category_name": "Продукты",
    "total_amount": 15420.50,
    "transaction_count": 23
  },
  {
    "category_id": 6,
    "category_name": "Транспорт",
    "total_amount": 8750.00,
    "transaction_count": 45
  }
]
```

---

## Связанные разделы

- [Transactions Service](../services/transactions-service.md)
- [API: Синхронизация](sync.md)
- [API: Изображения](images.md) — иконки категорий
