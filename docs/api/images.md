[Документация](../README.md) / [API](index.md) / Изображения

# API: Изображения

## GET /images/avatars/default

Список предустановленных аватарок (без аутентификации). Ответ кэшируется в Redis на 6 часов.

**Ответ 200:**
```json
[
  {"id": "uuid-1", "content_type": "image/jpeg"},
  {"id": "uuid-2", "content_type": "image/png"}
]
```

---

## GET /images/avatars/me

Получить текущую аватарку пользователя.

**Заголовок:** `Authorization: Bearer {access_token}`

**Ответ 200:**
```json
{"id": "uuid-3", "content_type": "image/jpeg"}
```

**Ответ 404:** аватарка не установлена (пользователь не выбрал)

---

## PUT /images/avatars/me

Установить аватарку пользователя (выбрать из предустановленных).

**Заголовок:** `Authorization: Bearer {access_token}`

**Тело запроса:**
```json
{"image_id": "uuid-1"}
```

**Ответ 200:**
```json
{"id": "uuid-1", "content_type": "image/jpeg"}
```

**После изменения:** публикуется событие `user.avatar.updated` → history-service записывает "Аватар обновлён".

---

## GET /images/{id}

Получить бинарные данные изображения по ID (без аутентификации).

**Ответ 200:** бинарный ответ с заголовком `Content-Type: image/jpeg` (или другой)

**Cache-Control:** `public, max-age=31536000` (1 год — изображения иммутабельны)

---

## GET /images/mappings/categories

Маппинг `category_id → image_id` для иконок категорий транзакций (без аутентификации). Кэшируется в Redis на 6 часов.

**Ответ 200:**
```json
{
  "1": "uuid-10",
  "5": "uuid-11",
  "6": "uuid-12"
}
```

Используется клиентом для отображения иконки рядом с названием категории.

---

## GET /images/mappings/merchants

Маппинг `merchant_id → image_id` для логотипов мерчантов (без аутентификации). Кэшируется в Redis на 6 часов.

**Ответ 200:**
```json
{
  "42": "uuid-20",
  "55": "uuid-21"
}
```

---

## Связанные разделы

- [Images Service](../services/images-service.md)
- [API: Транзакции](transactions.md) — иконки категорий
