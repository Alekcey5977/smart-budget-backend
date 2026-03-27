import asyncio
import logging
from contextlib import asynccontextmanager

import uvicorn
from app.database import create_tables, shutdown
from app.event_listener import EventListener
from app.routers import notification, websocket
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from prometheus_fastapi_instrumentator import Instrumentator

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)


@asynccontextmanager
async def life_span(app: FastAPI):
    await create_tables()

    # Запускаем прослушиватель событий в фоновом режиме
    event_listener = EventListener()
    listener_task = asyncio.create_task(event_listener.listen())

    # Сохраняем ссылку на задачу, чтобы она не была удалена GC
    app.state.listener_task = listener_task

    yield

    # Отменяем задачу при остановке сервиса
    if not listener_task.done():
        listener_task.cancel()
        try:
            await listener_task
        except asyncio.CancelledError:
            pass

    await shutdown()


app = FastAPI(title="Notification-service", lifespan=life_span)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(notification.router)
app.include_router(websocket.router)

Instrumentator().instrument(app).expose(app, endpoint="/metrics")


@app.get("/health")
async def health():
    return {"status": "healthy", "service": "notification-service"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8006)
