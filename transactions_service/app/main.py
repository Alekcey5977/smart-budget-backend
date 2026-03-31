# Настройка логирования должна быть ПЕРЕД всеми остальными импортами
from contextlib import asynccontextmanager

import uvicorn
from app.database import AsyncSessionLocal, create_tables
from app.models import *  # noqa: F403
from app.repository.sync_repository import SyncRepository
from app.routers import sync, transactions
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from prometheus_fastapi_instrumentator import Instrumentator

from shared.logging import LoggingMiddleware, setup_logging

setup_logging(service_name="transactions-service")

scheduler = AsyncIOScheduler()


#  Периодическая задача
async def periodic_sync():
    async with AsyncSessionLocal() as db:
        repo = SyncRepository(db)
        try:
            result = await repo.sync_incremental()
            print(f"[SCHEDULER] Incremental sync: {result['synced']}")
        except Exception as e:
            print(f"[SCHEDULER] Error: {e}")


@asynccontextmanager
async def life_span(app: FastAPI):
    print("[LIFESPAN] Starting up...")

    await create_tables()

    try:
        async with AsyncSessionLocal() as db:
            repo = SyncRepository(db)
            result = await repo.sync_incremental()
            print(f"[LIFESPAN] Initial sync: {result['synced']}")
    except Exception as e:
        print(f"[LIFESPAN] Initial sync failed: {e}")

    scheduler.add_job(periodic_sync, IntervalTrigger(minutes=10))
    scheduler.start()
    print("[LIFESPAN] Scheduler started (sync every 10 minutes)")

    yield

    print("[LIFESPAN] Shutting down...")
    scheduler.shutdown(wait=False)
    print("[LIFESPAN] Scheduler stopped")


app = FastAPI(title="Transactions", lifespan=life_span)

app.add_middleware(LoggingMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(transactions.router)
app.include_router(sync.router)

Instrumentator().instrument(app).expose(app, endpoint="/metrics")


@app.get("/health")
async def health():
    return {"status": "healthy", "service": "transactions"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8002)
