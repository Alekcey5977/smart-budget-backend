import asyncio
import logging
from contextlib import asynccontextmanager

import uvicorn
from app.database import create_tables, shutdown
from app.event_listener import EventListener
from app.routers import history, websocket
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)


@asynccontextmanager
async def life_span(app: FastAPI):
    await create_tables()

    event_listener = EventListener()
    listener_task = asyncio.create_task(event_listener.listen())

    app.state.listener_task = listener_task

    yield

    if not listener_task.done():
        listener_task.cancel()
        try:
            await listener_task
        except asyncio.CancelledError:
            pass

    await shutdown()


app = FastAPI(
    title="History Service",
    description="Сервис истории действий пользователя. Записи создаются автоматически через Redis events при изменении целей, банковских счётов и профиля.",
    version="1.0.0",
    lifespan=life_span
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(history.router)
app.include_router(websocket.router)


@app.get("/health")
async def health():
    return {"status": "healthy", "service": "history-service"}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8007)
