from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from app.database import AsyncSessionLocal, create_tables, shutdown
from app.models import *
from contextlib import asynccontextmanager
from app.routers import transactions, sync
import uvicorn

from transactions_service.app.repository.sync_repository import SyncRepository


@asynccontextmanager
async def life_span(app: FastAPI):
    await create_tables()
    yield
    await shutdown()


scheduler = AsyncIOScheduler()


# 2. Периодическая задача
async def periodic_sync():
    async with AsyncSessionLocal() as db:
        repo = SyncRepository(db)
        try:
            result = await repo.sync_incremental()
            print(f"[SCHEDULER] Incremental sync: {result['synced']}")
        except Exception as e:
            print(f"[SCHEDULER] Error: {e}")


# 3. Lifespan-менеджер — заменяет @on_event
@asynccontextmanager
async def lifespan(app: FastAPI):
    # --- STARTUP ---
    print("[LIFESPAN] Starting up...")

    # Создаём таблицы
    await create_tables()

    # Первый запуск: начальная синхронизация
    try:
        async with AsyncSessionLocal() as db:
            repo = SyncRepository(db)
            result = await repo.sync_incremental()
            print(f"[LIFESPAN] Initial sync: {result['synced']}")
    except Exception as e:
        print(f"[LIFESPAN] Initial sync failed: {e}")

    # Запускаем планировщик
    scheduler.add_job(periodic_sync, IntervalTrigger(minutes=5))
    scheduler.start()
    print("[LIFESPAN] Scheduler started")

    yield  # ← приложение запущено

    # --- SHUTDOWN ---
    print("[LIFESPAN] Shutting down...")
    scheduler.shutdown(wait=False)
    print("[LIFESPAN] Scheduler stopped")



app = FastAPI(title="Transactions", lifespan=life_span)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(transactions.router)
app.include_router(sync.router)

@app.get("/health")
async def health():
    return {"status": "healthy", "service": "transactions"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8002)
