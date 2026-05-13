[Документация](../README.md) / [Мониторинг](overview.md) / Логирование

# Логирование

## Стек

```
Сервис (FastAPI)
    ↓ stdout (JSON)
Docker (container logs)
    ↓ Docker Socket
Promtail (Docker Service Discovery)
    ↓ HTTP push
Loki (:3100)
    ↓ datasource
Grafana (:3000) → Explore / Logs Dashboard
```

---

## Конфигурация Promtail

**Файл:** `promtail-config.yml`

Promtail использует Docker Service Discovery — автоматически находит контейнеры с меткой `logging: "promtail"`:

```yaml
scrape_configs:
  - job_name: docker
    docker_sd_configs:
      - host: unix:///var/run/docker.sock
        refresh_interval: 5s
        filters:
          - name: label
            values: ["logging=promtail"]
    relabel_configs:
      - source_labels: [__meta_docker_container_name]
        target_label: container_name
      - source_labels: [__meta_docker_compose_service]
        target_label: compose_service
```

**Дополнительные labels** в каждой лог-строке:
- `container_name` — имя контейнера
- `compose_service` — имя сервиса в docker-compose
- `log_stream` — stdout/stderr
- `level` — INFO/WARNING/ERROR/DEBUG (извлекается regex из JSON-лога)

---

## Формат логов сервисов

Все сервисы используют JSON-логирование через `shared/logging/`:

```json
{
  "timestamp": "2024-01-15T10:30:00.123Z",
  "level": "INFO",
  "service": "users-service",
  "message": "📤 Событие опубликовано: user.registered (ID: uuid)",
  "request_id": "abc123"
}
```

**Компоненты:**
- `shared/logging/config.py` — настройка JSON форматтера и уровней
- `shared/logging/middleware.py` — логирование каждого HTTP запроса (метод, путь, статус, время)
- `shared/logging/filters.py` — фильтрация технических логов (healthcheck и т.п.)

---

## Уровни логирования

| Уровень | Когда используется |
|---------|-------------------|
| `INFO` | Нормальные операции: sync завершён, событие обработано, запрос выполнен |
| `WARNING` | Нестандартные, но не критичные ситуации: WS disconnect, незнакомый тип события |
| `ERROR` | Сбои: Redis недоступен, ошибка обработки события, sync провалился |
| `DEBUG` | Детали для отладки (отключено в продакшне) |

---

## Просмотр логов

### Через make
```bash
make logs                                # Все сервисы (streaming)
docker compose logs -f users-service    # Конкретный сервис
docker compose logs --tail=100 transactions-service  # Последние 100 строк
```

### Через Grafana Loki (Explore)
```
URL: http://localhost:3000/explore

# Все ошибки
{job="docker"} |= "ERROR"

# Логи конкретного сервиса
{compose_service="transactions-service"}

# События синхронизации
{compose_service="transactions-service"} |= "sync"

# Ошибки Redis
{job="docker"} |= "Redis" |= "ERROR"

# HTTP запросы к gateway
{compose_service="gateway"} | json | status >= 400
```

---

## Связанные разделы

- [Обзор мониторинга](overview.md)
- [Grafana дашборды](grafana.md)
- [Docker Compose стек](../deployment/docker-compose.md)
