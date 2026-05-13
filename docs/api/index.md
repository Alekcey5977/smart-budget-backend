[Документация](../README.md) / API / Обзор

# API Reference — Обзор

## Base URLs

| Окружение | URL |
|-----------|-----|
| Разработка (prod stack) | `http://localhost:8000` |
| Тестовый стек | `http://localhost:18000` |
| Swagger UI (интерактивная документация) | `http://localhost:8000/docs` |
| ReDoc | `http://localhost:8000/redoc` |

---

## Аутентификация

### Для клиентов (HTTP)

```http
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

### Для Swagger UI
Передайте токен как query-параметр `?token=`:
```
GET /auth/me?token=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

### Refresh token
Хранится в HTTP-only cookie `refresh_token`. Устанавливается автоматически при логине, удаляется при логауте.

---

## Передача user_id

Клиент **никогда** не передаёт `user_id` напрямую — он извлекается из JWT в Gateway:
```
Клиент → Gateway:  Authorization: Bearer <JWT>
Gateway → Сервис:  X-User-ID: 42         (извлечено из токена)
```

---

## Форматы данных

| Поле | Формат | Пример |
|------|--------|--------|
| Дата/время | ISO 8601 UTC | `"2024-01-15T10:30:00"` |
| UUID | строка | `"550e8400-e29b-41d4-a716-446655440000"` |
| Сумма | число с плавающей точкой | `1500.75` |
| ID | целое число | `42` |

---

## Коды ошибок

| Код | Значение |
|-----|---------|
| `400 Bad Request` | Ошибка бизнес-логики (дублирующий email, неверные данные) |
| `401 Unauthorized` | Невалидный или просроченный токен |
| `403 Forbidden` | Доступ запрещён (не владелец ресурса) |
| `404 Not Found` | Ресурс не найден |
| `422 Unprocessable Entity` | Ошибка валидации Pydantic (неверный формат данных) |
| `503 Service Unavailable` | Downstream-сервис недоступен |
| `504 Gateway Timeout` | Таймаут downstream-сервиса |

**Формат тела ошибки:**
```json
{"detail": "Email уже зарегистрирован"}
```

---

## Сводная таблица всех эндпоинтов

### Аутентификация
| Метод | Путь | Защита | Описание |
|-------|------|--------|----------|
| POST | `/auth/register` | — | Регистрация |
| POST | `/auth/login` | — | Логин, получить токены |
| POST | `/auth/refresh` | cookie | Обновить access token |
| POST | `/auth/logout` | — | Выход |
| GET | `/auth/me` | JWT | Профиль пользователя |
| PUT | `/auth/me` | JWT | Обновить профиль |

### Банковские счета
| Метод | Путь | Защита | Описание |
|-------|------|--------|----------|
| POST | `/users/me/bank_account` | JWT | Добавить счёт |
| GET | `/users/me/bank_accounts` | JWT | Список счетов |
| PATCH | `/users/me/bank_account/{id}` | JWT | Переименовать |
| DELETE | `/users/me/bank_account/{id}` | JWT | Удалить |

### Транзакции
| Метод | Путь | Защита | Описание |
|-------|------|--------|----------|
| POST | `/transactions/` | JWT | Список с фильтрацией |
| GET | `/transactions/{id}` | JWT | Транзакция по ID |
| PATCH | `/transactions/{id}/category` | JWT | Изменить категорию |
| GET | `/transactions/categories` | JWT | Справочник категорий |
| GET | `/transactions/categories/{id}` | JWT | Категория по ID |
| POST | `/transactions/categories/summary` | JWT | Сводка по категориям |

### Синхронизация
| Метод | Путь | Защита | Описание |
|-------|------|--------|----------|
| POST | `/sync` | JWT | Синхронизировать все счета |
| POST | `/sync/{account_id}` | JWT | Синхронизировать один счёт |

### Изображения
| Метод | Путь | Защита | Описание |
|-------|------|--------|----------|
| GET | `/images/avatars/default` | — | Предустановленные аватарки |
| GET | `/images/avatars/me` | JWT | Аватарка пользователя |
| PUT | `/images/avatars/me` | JWT | Установить аватарку |
| GET | `/images/{id}` | — | Бинарные данные изображения |
| GET | `/images/mappings/categories` | — | Маппинг category → image |
| GET | `/images/mappings/merchants` | — | Маппинг merchant → image |

### Финансовые цели
| Метод | Путь | Защита | Описание |
|-------|------|--------|----------|
| POST | `/purposes/create` | JWT | Создать цель |
| GET | `/purposes/my` | JWT | Список целей |
| PUT | `/purposes/update/{id}` | JWT | Обновить цель |
| DELETE | `/purposes/delete/{id}` | JWT | Удалить цель |

### Уведомления
| Метод | Путь | Защита | Описание |
|-------|------|--------|----------|
| GET | `/notifications/user/me` | JWT | Список уведомлений |
| GET | `/notifications/user/me/unread/count` | JWT | Количество непрочитанных |
| GET | `/notifications/{id}` | JWT | Уведомление по ID |
| POST | `/notifications/{id}/mark-as-read` | JWT | Отметить прочитанным |
| POST | `/notifications/mark-all-as-read` | JWT | Все прочитаны |
| DELETE | `/notifications/{id}` | JWT | Удалить |

### История
| Метод | Путь | Защита | Описание |
|-------|------|--------|----------|
| GET | `/history/user/me` | JWT | Список записей |
| GET | `/history/{id}` | JWT | Запись по ID |
| DELETE | `/history/{id}` | JWT | Удалить запись |

### WebSocket
| Протокол | Путь | Auth | Описание |
|---------|------|------|----------|
| WS | `/ws/notification?token=` | JWT | Real-time уведомления |
| WS | `/ws/history?token=` | JWT | Real-time история |

---

## Связанные разделы

- [API: Аутентификация](auth.md)
- [API: Банковские счета](bank-accounts.md)
- [API: Транзакции](transactions.md)
- [API: WebSocket](websocket.md)
- [Архитектура: Карта сервисов](../architecture/services-map.md)
