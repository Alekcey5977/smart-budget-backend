<div align="center">

# 💰 SmartBudget Backend

**Microservice backend for personal finance management**

[![CI](https://github.com/Alekcey5977/smart-budget-backend/actions/workflows/ci.yml/badge.svg)](https://github.com/Alekcey5977/smart-budget-backend/actions/workflows/ci.yml)
[![Deploy Docs](https://github.com/Alekcey5977/smart-budget-backend/actions/workflows/docs.yml/badge.svg)](https://github.com/Alekcey5977/smart-budget-backend/actions/workflows/docs.yml)
[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)

[📚 Documentation](https://alekcey5977.github.io/smart-budget-backend/) · [🔍 API Reference](https://alekcey5977.github.io/smart-budget-backend/api/index/)

</div>

---

## Overview

SmartBudget Backend is an 8-service microservice system built with FastAPI. It handles authentication, bank account synchronization, transaction categorization, financial goals, real-time notifications, and audit history — all connected via Redis Streams event bus.

## Features

- **JWT Authentication** — access token (15 min) + refresh cookie (7 days)
- **Bank Sync** — automatic transaction sync every 10 min via APScheduler
- **Transaction Filtering** — by date, amount, category, type with pagination
- **Financial Goals** — progress tracking with threshold notifications at 25/50/80/100%
- **Real-time Updates** — WebSocket push for notifications and history
- **Event-Driven** — Redis Streams as internal event bus between services
- **Full Observability** — Prometheus + Grafana + Loki stack included

## Tech Stack

![Python](https://img.shields.io/badge/Python-3776AB?logo=python&logoColor=white&style=flat-square)
![FastAPI](https://img.shields.io/badge/FastAPI-009688?logo=fastapi&logoColor=white&style=flat-square)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-4169E1?logo=postgresql&logoColor=white&style=flat-square)
![Redis](https://img.shields.io/badge/Redis-DC382D?logo=redis&logoColor=white&style=flat-square)
![Docker](https://img.shields.io/badge/Docker-2496ED?logo=docker&logoColor=white&style=flat-square)
![Prometheus](https://img.shields.io/badge/Prometheus-E6522C?logo=prometheus&logoColor=white&style=flat-square)
![Grafana](https://img.shields.io/badge/Grafana-F46800?logo=grafana&logoColor=white&style=flat-square)
![k6](https://img.shields.io/badge/k6-7D64FF?logo=k6&logoColor=white&style=flat-square)

## Architecture

```
Client → Gateway (8000) → 7 backend services
                        ↕
                   Redis Streams
                   (event bus)
```

| Service | Port | Responsibility |
|---|---|---|
| gateway | 8000 | Auth, routing, WebSocket proxy |
| users-service | 8001 | Registration, JWT, bank accounts |
| transactions-service | 8002 | Sync, categorization, filtering |
| images-service | 8003 | Avatars, category/merchant icons |
| pseudo-bank-service | 8004 | Mock bank API |
| purposes-service | 8005 | Financial goals |
| notification-service | 8006 | Event-driven notifications |
| history-service | 8007 | Audit trail |

## Quick Start

```bash
# 1. Clone and configure
git clone https://github.com/Alekcey5977/smart-budget-backend.git
cd smart-budget-backend
cp .env.example .env

# 2. Start all services
make start

# 3. Load test data (optional)
make load-test-data    # bank accounts + transactions
make load-test-images  # avatars + category icons
```

API is available at `http://localhost:8000` · Swagger UI at `http://localhost:8000/docs`

## Testing

```bash
make install        # create .venv for all 8 services
make test           # unit + integration tests
make test-e2e-start # start isolated test stack
make test-e2e       # run E2E tests
make k6             # load tests (smoke → load → stress)
```

## Team

| Name | Role |
|---|---|
| **Alexey Kilin** | Team Lead & Backend Developer |
| **Dmitry Lykov** | Backend Developer |
| **Alexander Oskin** | Frontend Developer |
| **Vadim Popov** | Frontend Developer |
