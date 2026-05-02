[Документация](../README.md) / [Тестирование](overview.md) / Нагрузочные тесты

# Нагрузочное тестирование (k6)

## Требования

- **k6** установлен: https://grafana.com/docs/k6/latest/set-up/install-k6/
- Тестовый стек запущен: `make test-e2e-start`

---

## Запуск

```bash
# Один тест
make k6-smoke
make k6-load
make k6-stress

# Последовательно: smoke → load → stress (~10 мин)
make k6

# Против dev-стека (без тестового окружения)
make k6-smoke K6_BASE_URL=http://localhost:8000
```

---

## Профили нагрузки

| Команда | VUs | Длительность | Пороги (fail-fast) | Цель |
|---------|-----|-------------|-------------------|------|
| `k6-smoke` | 1 | 30 сек | p95 < 1с, errors < 1% | Sanity check |
| `k6-load` | 0→50→0 | ~4 мин | p95 < 2с, errors < 2% | Реалистичная нагрузка |
| `k6-stress` | 0→50→100→150→0 | ~5 мин | p95 < 5с, errors < 10% | Поиск предела |
| `k6-spike` | 20→1000→20 | ~1 мин | p99 < 10с, errors < 20% | Устойчивость к всплеску |
| `k6-max` | 0→3000 | ~1 мин | только наблюдение | Абсолютный предел |
| `k6-high` | 0→5000 | 75 сек | только наблюдение | За пределом |
| `k6-extreme` | 0→10000 | 90 сек | только наблюдение | Разрушительная нагрузка |

`fail-fast` = при нарушении порога тест прерывается (только для smoke).

---

## Сценарий теста (что делает каждый VU)

Все профили кроме smoke используют **10 seed-пользователей**, созданных в `setup()`:

```javascript
export function setup() {
    // Создаёт 10 пользователей, один на каждый тестовый счёт
    for (let i = 0; i < BANK_ACCOUNT_NUMBERS.length; i++) {
        register(email, password, ...);
        const token = login(email, password);
        addBankAccount(token, BANK_ACCOUNT_NUMBERS[i], ...);
        users.push({email, password});
    }
    return users;
}
```

VU выбирает слот по формуле `(__VU - 1) % 10` и кэширует токен между итерациями.

**Итерация каждого VU:**
1. Логин (один раз, токен кэшируется)
2. `GET /auth/me`
3. `GET /users/me/bank_accounts`
4. `GET /transactions/categories` (кэшируется Redis 12 ч — практически без нагрузки на БД)
5. `POST /transactions/categories/summary`
6. `POST /transactions/` (limit=10)
7. `GET /images/avatars/default` (кэш Redis 6 ч)
8. `GET /images/mappings/categories` (кэш Redis 6 ч)
9. `GET /notifications/user/me`
10. `GET /history/user/me`
11. Каждые 5 итераций: `POST /purposes/create` + `DELETE /purposes/delete/{id}`

---

## Метрики

| Метрика | Описание |
|---------|----------|
| `http_req_duration` | Время ответа (p50, p95, p99) |
| `http_req_failed` | Доля неуспешных запросов |
| `errors` (custom Rate) | Ошибочные статусы по бизнес-логике |
| `vus` | Активные виртуальные пользователи |
| `http_reqs` | Общее число запросов |

---

## Интеграция с Grafana

k6 экспортирует метрики в Prometheus через remote write, которые визуализируются в Grafana:

```bash
# Тест с экспортом в тестовый Prometheus
make k6-load K6_PROMETHEUS_RW=http://localhost:19090/api/v1/write
```

После запуска откройте дашборд **k6 Load Test** в Grafana: http://localhost:13000

Дашборд показывает в реальном времени:
- Количество активных VU
- RPS (requests per second)
- p95, p99 латентность
- Процент ошибок

---

## Файлы k6

```
k6/
├── smoke.js      — 1 VU, 30 сек
├── load.js       — 50 VU, ~4 мин
├── stress.js     — до 150 VU, ~5 мин
├── spike.js      — до 1000 VU, ~1 мин
├── max.js        — до 3000 VU, ~1 мин
├── high.js       — до 5000 VU, 75 сек
├── extreme.js    — до 10000 VU, 90 сек
└── lib/
    ├── auth.js   — register(), login(), addBankAccount(), BANK_ACCOUNT_NUMBERS
    └── helpers.js — checkStatus(), authHeaders(), SMOKE_THRESHOLDS, LOAD_THRESHOLDS, ...
```

---

## Связанные разделы

- [Обзор тестирования](overview.md)
- [E2E тесты](e2e.md)
- [Мониторинг: Grafana дашборды](../monitoring/grafana.md)
- [Makefile: k6 команды](../deployment/makefile-reference.md)
