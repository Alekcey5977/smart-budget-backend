# Настройка логирования должна быть ПЕРЕД всеми остальными импортами
import os
import sys

import uvicorn
from app.routers import (
    auth,
    bank_accounts,
    history,
    images,
    notifications,
    purposes,
    sync,
    transactions,
    websocket,
)
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from prometheus_fastapi_instrumentator import Instrumentator

from shared.logging import LoggingMiddleware, setup_logging

setup_logging(service_name="gateway")


sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


app = FastAPI(title="Gateway Service",
              description="Точка входа", version="1.0.0")

app.add_middleware(LoggingMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(transactions.router)
app.include_router(images.router)
app.include_router(sync.router)
app.include_router(bank_accounts.router)
app.include_router(purposes.router)
app.include_router(notifications.router)
app.include_router(history.router)
app.include_router(websocket.router)


Instrumentator().instrument(app).expose(app, endpoint="/metrics")


@app.get("/health")
async def health():
    return {"status": "healthy", "service": "gateway", "version": "1.0.0"}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
