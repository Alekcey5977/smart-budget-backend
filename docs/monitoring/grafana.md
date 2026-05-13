[Документация](../README.md) / [Мониторинг](overview.md) / Grafana

# Grafana дашборды

**URL:** http://localhost:3000 (dev стек) / http://localhost:13000 (test стек)
**Логин:** admin / admin

---

## Дашборд: Service Metrics

**Файл:** `monitoring/service_metrics.json`

Показывает производительность всех 8 микросервисов в реальном времени.

**Панели:**
- **RPS по сервисам** — количество запросов в секунду (разбивка по сервисам)
- **Латентность p50/p95/p99** — перцентили времени ответа
- **Процент ошибок (4xx/5xx)** — доля неуспешных ответов
- **Активные соединения** — количество одновременных запросов

**Полезные фильтры:** выбор конкретного сервиса и временного диапазона через переменные Grafana.

---

## Дашборд: k6 Load Test

**Файл:** `monitoring/k6_dashboard.json`

Показывает результаты нагрузочных тестов в реальном времени.

**Панели:**
- **Virtual Users** — количество активных VU
- **RPS** — запросы в секунду
- **http_req_duration p95/p99** — латентность под нагрузкой
- **Error Rate** — процент ошибок
- **HTTP Status distribution** — разбивка по кодам ответа

**Запуск с экспортом метрик:**
```bash
make test-e2e-start
# Открыть http://localhost:13000
make k6-load K6_PROMETHEUS_RW=http://localhost:19090/api/v1/write
# Наблюдать в реальном времени
```

---

## Дашборд: Logs

**Файл:** `monitoring/logs-dashboard.json`

Агрегированные логи из всех контейнеров через Loki.

**Панели:**
- **Log stream** — поток логов с фильтрацией по сервису и уровню
- **Error rate** — частота ERROR логов по сервисам
- **Log volume** — объём логов по времени

**Типичные запросы в Explore:**
```
# Ошибки всех сервисов
{job="docker"} |= "ERROR"

# Логи конкретного сервиса
{compose_service="transactions-service"}

# Только WARNING и выше
{compose_service="purposes-service"} | json | level =~ "WARNING|ERROR"

# Поиск по тексту
{job="docker"} |= "sync.completed"
```

---

## Провизионирование

Grafana автоматически загружает дашборды и datasources при старте контейнера через папку `/etc/grafana/provisioning/`.

Изменения в JSON-файлах применяются при перезапуске контейнера:
```bash
docker compose restart grafana
```

---

## Связанные разделы

- [Обзор мониторинга](overview.md)
- [Логирование](logs.md)
- [Нагрузочные тесты k6](../testing/load-testing.md)
