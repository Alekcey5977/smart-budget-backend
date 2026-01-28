from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.database import create_tables, shutdown
from app.models import *
from contextlib import asynccontextmanager
from app.routers import notification
import uvicorn
from app.event_listener import EventListener
import asyncio


@asynccontextmanager
async def life_span(app: FastAPI):
    await create_tables()
    
    # Запускаем прослушиватель событий в фоновом режиме
    event_listener = EventListener()
    asyncio.create_task(event_listener.listen())
    
    yield
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


@app.get("/health")
async def health():
    return {"status": "healthy", "service": "notification-service"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8006)
