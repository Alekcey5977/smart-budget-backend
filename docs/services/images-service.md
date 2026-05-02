[Документация](../README.md) / [Сервисы](gateway.md) / Images Service

# Images Service

**Порт:** 8003 | **БД:** PostgreSQL :5435 (images_db)

Хранит бинарные данные изображений: аватарки пользователей, иконки категорий транзакций и мерчантов.

---

## Модель хранения

Единая таблица `images` для всех типов изображений. Поле `entity_type` определяет роль записи:

| entity_type | entity_id | is_default | Описание |
|-------------|-----------|------------|----------|
| `user_avatar` | — | `True` | Предустановленная аватарка (общая для всех) |
| `user_avatar` | user_id | `False` | Выбранная аватарка конкретного пользователя |
| `category` | category_id | — | Иконка категории транзакции |
| `merchant` | merchant_id | — | Иконка мерчанта |

Бинарные данные (`image_data: BYTEA`) хранятся прямо в PostgreSQL. При запросе `GET /images/{id}` возвращается бинарный ответ с правильным `Content-Type`.

---

## Эндпоинты

### Публичные (без аутентификации)

| Метод | Путь | Кэш | Описание |
|-------|------|-----|----------|
| `GET` | `/images/avatars/default` | Redis 6 ч | Список предустановленных аватарок |
| `GET` | `/images/{id}` | Cache-Control 1 год | Бинарные данные изображения |
| `GET` | `/images/mappings/categories` | Redis 6 ч | Маппинг category_id → image_id |
| `GET` | `/images/mappings/merchants` | Redis 6 ч | Маппинг merchant_id → image_id |

### Защищённые (X-User-ID)

| Метод | Путь | Описание |
|-------|------|----------|
| `GET` | `/images/avatars/me` | Аватарка текущего пользователя |
| `PUT` | `/images/avatars/me` | Выбрать аватарку (из предустановленных) |

---

## Стратегия кэширования

**Списки и маппинги (Redis Cache-Aside):**
- `images:default_avatars` — список ID и метаданных предустановленных аватарок (TTL 6 ч)
- `images:categories_map` — `{category_id: image_id, ...}` (TTL 6 ч)
- `images:merchants_map` — `{merchant_id: image_id, ...}` (TTL 6 ч)

**Бинарные данные (`/images/{id}`):**
- `Cache-Control: public, max-age=31536000` (1 год)
- ID изображений иммутабельны — содержимое не меняется при том же ID

---

## Загрузка тестовых данных

Тестовые изображения (аватарки и иконки) загружаются через:
```bash
make load-test-images
```

Скрипт `testData/load_test_images.py` заливает изображения через `POST /images/bulk` (внутренний эндпоинт псевдобанка).

---

## Публикуемые события

| Событие | Триггер | Payload |
|---------|---------|---------|
| `user.avatar.updated` | `PUT /images/avatars/me` | `{user_id}` |

---

## Переменные окружения

| Переменная | Описание |
|-----------|----------|
| `IMAGES_DATABASE_URL` | postgresql+asyncpg://img_user:pass@images-db:5432/images_db |
| `REDIS_URL` | Redis для кэша |

---

## Связанные разделы

- [API: Изображения](../api/images.md)
- [Модели данных: images_db](../architecture/data-model.md)
- [Тестовые данные](../deployment/quickstart.md)
