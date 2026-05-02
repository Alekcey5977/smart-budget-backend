[Документация](../README.md) / [Деплой](quickstart.md) / Docker Compose

# Docker Compose стек

## Обзор

SmartBudget использует два Compose-файла:

| Файл | Стек | Назначение |
|------|------|-----------|
| `docker-compose.yml` | prod/dev | Основная разработка |
| `docker-compose.test.yml` | test | Изолированное E2E тестирование |

---

## Контейнеры продакшн-стека

### Микросервисы (FastAPI + Uvicorn)

| Контейнер | Образ | Внешний порт |
|-----------|-------|-------------|
| `gateway` | Dockerfile | 8000 |
| `users-service` | Dockerfile | 8001 |
| `transactions-service` | Dockerfile | 8002 |
| `images-service` | Dockerfile | 8003 |
| `pseudo-bank-service` | Dockerfile | 8004 |
| `purposes-service` | Dockerfile | 8005 |
| `notification-service` | Dockerfile | 8006 |
| `history-service` | Dockerfile | 8007 |

### Базы данных (PostgreSQL 13)

| Контейнер | Внешний порт | Volume | Зависимость |
|-----------|-------------|--------|------------|
| `users-db` | 5433 | `users-db-data` | — |
| `transactions-db` | 5434 | `transactions-db-data` | — |
| `images-db` | 5435 | `images-db-data` | — |
| `pseudo-bank-db` | 5436 | `pseudo-bank-db-data` | — |
| `purposes-db` | 5437 | `purposes-db-data` | — |
| `notification-db` | 5438 | `notification-db-data` | — |
| `history-db` | 5439 | `history-db-data` | — |

### Инфраструктура

| Контейнер | Образ | Порт | Назначение |
|-----------|-------|------|-----------|
| `redis` | redis:7-alpine | 6379 | Кэш + шина событий |
| `redis-commander` | rediscommander | 8081 | Web-UI для Redis |
| `prometheus` | prom/prometheus | 9090 | Сбор метрик |
| `grafana` | grafana/grafana | 3000 | Дашборды |
| `loki` | grafana/loki | 3100 | Хранение логов |
| `promtail` | grafana/promtail | — | Отправка логов в Loki |

---

## Сеть

Все контейнеры подключены к сети `monitoring-net` (bridge). Это позволяет:
- Микросервисам обращаться друг к другу по имени (`users-service:8001`)
- Prometheus собирать метрики со всех сервисов
- Promtail собирать логи через Docker Socket

---

## Healthchecks

Каждая PostgreSQL база данных имеет healthcheck:
```yaml
healthcheck:
  test: ["CMD-SHELL", "pg_isready -U ${DB_USER} -d ${DB_NAME}"]
  interval: 5s
  timeout: 5s
  retries: 5
```

Redis:
```yaml
healthcheck:
  test: ["CMD", "redis-cli", "ping"]
  interval: 5s
```

Микросервисы используют `depends_on` с `condition: service_healthy` — не стартуют пока БД и Redis не готовы.

---

## Метки (labels) для Promtail

Все микросервисы имеют метку `logging: "promtail"`, по которой Promtail определяет контейнеры для сбора логов:
```yaml
labels:
  logging: "promtail"
```

---

## Volumes

| Volume | Данные |
|--------|--------|
| `users-db-data` | PostgreSQL users |
| `transactions-db-data` | PostgreSQL transactions |
| `images-db-data` | PostgreSQL images |
| `pseudo-bank-db-data` | PostgreSQL pseudo-bank |
| `purposes-db-data` | PostgreSQL purposes |
| `notification-db-data` | PostgreSQL notifications |
| `history-db-data` | PostgreSQL history |
| `grafana-data` | Grafana настройки и дашборды |
| `prometheus-data` | Метрики Prometheus |

Volumes сохраняются при `make stop` и `make down`. Удаляются только при `make clean` или `make reset-db`.

---

## Тестовый стек (docker-compose.test.yml)

Изолированная копия продакшн-стека для E2E тестирования:

- **Project name:** `smartbudget-test` (все контейнеры получают префикс `smartbudget-test-`)
- **Все порты** смещены на 10000 (8000 → 18000, 5433 → 15433, и т.д.)
- **Redis:** 17379
- **Grafana:** 13000, **Prometheus:** 19090
- **Отдельные volumes** — тестовые данные не пересекаются с dev-данными

Управление тестовым стеком:
```bash
make test-e2e-start   # Поднять (автоматически грузит тестовые данные)
make test-e2e-stop    # Остановить и удалить все volumes
```

---

## Dockerfile сервисов

Все сервисы используют единый паттерн Dockerfile:
```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "800X"]
```

---

## Связанные разделы

- [Быстрый старт](quickstart.md)
- [Конфигурация](configuration.md)
- [Справочник Makefile](makefile-reference.md)
- [Мониторинг](../monitoring/overview.md)
