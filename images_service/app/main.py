# Настройка логирования должна быть ПЕРЕД всеми остальными импортами
from contextlib import asynccontextmanager

from app.database import engine
from app.models import Base
from app.routers import images
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from prometheus_fastapi_instrumentator import Instrumentator

from shared.logging import LoggingMiddleware, setup_logging

setup_logging(service_name="images-service")


@asynccontextmanager
async def lifespan(_app: FastAPI):
    """
    Lifecycle events для приложения.

    Создает таблицы при старте и закрывает соединения при остановке.
    """
    # Startup: Создание таблиц
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield

    # Shutdown: Закрытие соединений
    await engine.dispose()


app = FastAPI(
    title="Images Service",
    description="""
# Images Service API

Сервис для управления изображениями в Smart Budget приложении.

## Функциональность:

### Аватарки пользователей
- Получение списка предустановленных аватарок
- Получение текущей аватарки пользователя
- Обновление аватарки пользователя (выбор из предустановленных)

### Изображения категорий и мерчантов
- Получение маппинга категорий к изображениям для кэширования
- Получение маппинга мерчантов к изображениям для кэширования
- Получение бинарных данных изображения по ID

## Архитектура:

Фронтенд загружает маппинги при инициализации и кэширует их.
При отображении транзакции:
1. Проверяет наличие изображения мерчанта в кэше
2. Если нет - использует изображение категории
3. Загружает изображение по ID через GET /images/{id}

## Безопасность:

Защищенные эндпоинты (аватарки пользователя) требуют заголовок X-User-ID,
который прокидывается Gateway после проверки JWT токена.
""",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(LoggingMiddleware)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # В production указать конкретные домены
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Подключение роутеров
app.include_router(images.router)

Instrumentator().instrument(app).expose(app, endpoint="/metrics")


@app.get("/", tags=["health"])
async def root():
    """Health check эндпоинт"""
    return {"service": "images-service", "status": "running", "version": "1.0.0"}


@app.get("/health", tags=["health"])
async def health_check():
    """
    Проверка здоровья сервиса.

    Используется для мониторинга и load balancer health checks.
    """
    return {"status": "healthy"}
