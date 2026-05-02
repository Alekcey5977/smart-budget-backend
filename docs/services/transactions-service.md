[Документация](../README.md) / [Сервисы](gateway.md) / Transactions Service

# Transactions Service

**Порт:** 8002 | **БД:** PostgreSQL :5434 (transactions_db)

Хранит транзакции, синхронизирует их с pseudo-bank-service, управляет категориями. Центральный сервис для финансовой аналитики.

---

## Жизненный цикл сервиса (lifespan)

При старте выполняется в порядке:
1. Подключение к Redis (кэш + EventPublisher)
2. `initial_sync()` — инкрементальная синхронизация всех активных счетов
3. APScheduler запускает `periodic_sync()` каждые **10 минут**
4. EventListener подписывается на события `bank_account.added` и `bank_account.renamed`

При остановке: APScheduler и EventPublisher корректно завершают работу.

---

## Синхронизация транзакций

### Инкрементальная синхронизация (основной режим)

```mermaid
sequenceDiagram
    participant APSched as APScheduler (10 мин)
    participant TR as transactions-service
    participant PBS as pseudo-bank-service
    participant DB as transactions_db
    participant Redis

    APSched->>TR: periodic_sync()
    TR->>DB: SELECT активные bank_accounts
    loop Для каждого счёта
        TR->>PBS: GET /pseudo_bank/account/{hash}/export?since={last_synced_at}
        PBS-->>TR: {bank_account, transactions[], merchants[], categories[]}
        TR->>DB: UPSERT categories, merchants
        TR->>DB: INSERT новые транзакции (дедупликация по ID)
        TR->>DB: UPDATE bank_account (balance, last_synced_at)
        TR->>Redis: XADD domain-events {sync.completed, user_id, count}
    end
```

При первом добавлении счёта: `since=None` → экспортируются все транзакции.

### Ручная синхронизация

```
POST /transactions/sync_user_accounts   — все счета одного пользователя
POST /transactions/trigger_sync         — один конкретный счёт
POST /transactions/sync_all             — все активные счета всех пользователей
```

### Реакция на события

При получении `bank_account.added`:
- Запуск `trigger_sync(bank_account_hash, user_id)` — немедленная синхронизация нового счёта

При получении `bank_account.renamed`:
- Обновление `bank_account_name` в локальной копии `bank_accounts`

---

## Категоризация транзакций

Приоритет при импорте транзакции:

```
1. Мерчант известен → category = merchant.category
2. MCC-код известен → category = mcc_categories[mcc].category
3. Иначе            → category = "Без категории" (default)
```

Пользователь может переопределить категорию через `PATCH /transactions/{id}/category`.

---

## Эндпоинты

| Метод | Путь | Описание | Auth |
|-------|------|----------|------|
| `POST` | `/transactions/` | Список транзакций с фильтрацией | X-User-ID |
| `GET` | `/transactions/{id}` | Получить транзакцию по ID | X-User-ID |
| `PATCH` | `/transactions/{id}/category` | Изменить категорию | X-User-ID |
| `GET` | `/transactions/categories` | Справочник категорий | — |
| `GET` | `/transactions/categories/{id}` | Категория по ID | — |
| `POST` | `/transactions/categories/summary` | Сводка по категориям | X-User-ID |
| `POST` | `/transactions/trigger_sync` | Синхронизация одного счёта | — |
| `POST` | `/transactions/sync_user_accounts` | Синхронизация всех счетов пользователя | — |
| `POST` | `/transactions/sync_all` | Инкрементальная синхронизация всех | — |

### Параметры фильтрации транзакций (`POST /transactions/`)

```json
{
  "transaction_type": "expense",     // "income" | "expense" | null
  "category_ids": [1, 5, 10],        // список ID категорий
  "bank_account_ids": [3, 7],        // фильтр по счетам
  "start_date": "2024-01-01T00:00:00",
  "end_date": "2024-12-31T23:59:59",
  "min_amount": 100.0,
  "max_amount": 50000.0,
  "merchant_ids": [42],
  "limit": 20,                       // 1–100, default=20
  "offset": 0
}
```

---

## Кэш Redis

| Ключ | TTL | Описание |
|------|-----|----------|
| `transactions:categories` | 12 часов | Полный справочник категорий |

---

## Публикуемые события

| Событие | Триггер | Payload |
|---------|---------|---------|
| `sync.completed` | Завершение sync для счёта | `{user_id, new_transactions_count, synced_at}` |
| `transaction.category.updated` | PATCH /{id}/category | `{user_id, old_category_name, new_category_name}` |

---

## Переменные окружения

| Переменная | Описание |
|-----------|----------|
| `TRANSACTIONS_DATABASE_URL` | postgresql+asyncpg://tr_user:pass@transactions-db:5432/transactions_db |
| `PSEUDO_BANK_SERVICE_URL` | URL pseudo-bank-service для экспорта данных |
| `REDIS_URL` | Redis для кэша и событий |

---

## Связанные разделы

- [API: Транзакции](../api/transactions.md)
- [API: Синхронизация](../api/sync.md)
- [Система событий](../architecture/event-system.md)
- [Pseudo Bank Service](pseudo-bank-service.md)
