# Настройка логирования должна быть ПЕРЕД всеми остальными импортами
from contextlib import asynccontextmanager

import uvicorn
from app.database import create_tables, shutdown
from app.models import *  # noqa: F403
from app.routers import pseudo_bank
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from prometheus_fastapi_instrumentator import Instrumentator

from shared.logging import LoggingMiddleware, setup_logging

setup_logging(service_name="pseudo-bank-service")


@asynccontextmanager
async def life_span(app: FastAPI):
    await create_tables()
    yield
    await shutdown()


app = FastAPI(title="Pseudo_Bank", lifespan=life_span)

app.add_middleware(LoggingMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(pseudo_bank.router)

Instrumentator().instrument(app).expose(app, endpoint="/metrics")


@app.get("/health")
async def health():
    return {"status": "healthy", "service": "pseudo_bank"}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8004)
