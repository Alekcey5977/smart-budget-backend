[Документация](../README.md) / [Деплой](configuration.md) / Быстрый старт

# Быстрый старт

Запустить SmartBudget backend локально за 5 минут.

## Предварительные требования

- **Docker** и **Docker Compose** (v2+)
- **make**
- **git**
- **Python 3.11–3.13** (только для запуска тестов, не нужен для `make start`)
- **k6** (только для нагрузочных тестов) — https://grafana.com/docs/k6/latest/set-up/install-k6/

---

## Шаг 1: Клонировать и настроить окружение

```bash
git clone <repository-url>
cd smart-budget-backend

# Создать файл с переменными окружения
cp .env.example .env
```

Отредактируйте `.env` — обязательно замените секретные ключи:
```env
ACCESS_SECRET_KEY=your-strong-random-secret-here
REFRESH_SECRET_KEY=another-strong-random-secret
BANK_SECRET_KEY=bank-account-secure-key-2026
```

Для разработки можно использовать любые строки, но в продакшне — обязательно случайные значения достаточной длины.

---

## Шаг 2: Запустить сервисы

```bash
make start
```

Поднимает 16 Docker-контейнеров: 8 микросервисов, 8 PostgreSQL БД, Redis, Prometheus, Grafana, Loki, Promtail, Redis Commander.

Дождитесь сообщения `Services started!`

---

## Шаг 3: Загрузить тестовые данные

```bash
# Генерация JSON-файлов с тестовыми транзакциями и изображениями
make generate-test-data

# Загрузка тестовых банковских счетов и транзакций в pseudo-bank-service
make load-test-data

# Загрузка аватарок и иконок категорий/мерчантов в images-service
make load-test-images
```

После этого доступны 10 тестовых банковских счетов (номера в разделе [тестовые счета](../services/pseudo-bank-service.md)).

---

## Шаг 4: Проверить работу

Откройте Swagger UI: **http://localhost:8000/docs**

Пример первого запроса (curl):
```bash
# Регистрация
curl -X POST http://localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"StrongPass1!","first_name":"Иван","last_name":"Иванов"}'

# Логин
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"StrongPass1!"}' \
  -c cookies.txt

# Добавить банковский счёт
TOKEN="<access_token из ответа выше>"
curl -X POST http://localhost:8000/users/me/bank_account \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"bank_account_number":"40817810099910004312","bank_account_name":"Моя карта","bank":"Сбербанк"}'

# Транзакции появятся через несколько секунд (автосинхронизация)
curl -X POST http://localhost:8000/transactions/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"limit": 5}'
```

---

## Адреса всех сервисов

| Сервис | URL |
|--------|-----|
| **API Gateway (Swagger)** | http://localhost:8000/docs |
| Users Service (Swagger) | http://localhost:8001/docs |
| Transactions Service | http://localhost:8002/docs |
| Images Service | http://localhost:8003/docs |
| Pseudo Bank Service | http://localhost:8004/docs |
| Purposes Service | http://localhost:8005/docs |
| Notification Service | http://localhost:8006/docs |
| History Service | http://localhost:8007/docs |
| **Grafana** | http://localhost:3000 (admin/admin) |
| **Prometheus** | http://localhost:9090 |
| **Redis Commander** | http://localhost:8081 |

---

## Управление сервисами

```bash
make start       # Запустить
make stop        # Остановить (данные сохраняются)
make restart     # Перезапустить
make down        # Остановить и удалить контейнеры (данные сохраняются в volumes)
make clean       # Остановить и удалить всё включая данные (с подтверждением)
make reset-db    # Полный сброс БД — удалить и пересоздать (с подтверждением)
make logs        # Показать логи всех сервисов (streaming)
make status      # Показать статус контейнеров
make build       # Пересобрать Docker образы
```

---

## Частые проблемы

**Порт уже занят:**
```
Error: port 8000 is already allocated
```
Измените `GATEWAY_PORT=8000` в `.env` на свободный порт.

**База данных не поднялась:**
```bash
make logs  # Найти ошибки в логах
# или для конкретного сервиса:
docker compose logs users-db
```

**Нет транзакций после добавления счёта:**
- Убедитесь, что `make load-test-data` был выполнен
- Транзакции синхронизируются немедленно при добавлении счёта
- Проверьте логи: `docker compose logs transactions-service`

**Ошибка 503 при API запросах:**
- Один из сервисов не запустился
- Проверьте `make status` и `make logs`

---

## Связанные разделы

- [Конфигурация (переменные окружения)](configuration.md)
- [Docker Compose стек](docker-compose.md)
- [Справочник Makefile](makefile-reference.md)
- [E2E тестирование](../testing/e2e.md)
