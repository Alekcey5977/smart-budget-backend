from contextlib import asynccontextmanager

import uvicorn
from app.database import create_tables, shutdown
from app.models import *  # noqa: F403
from app.routers import bank_account, users
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware


@asynccontextmanager
async def life_span(app: FastAPI):
    await create_tables()
    yield
    await shutdown()


app = FastAPI(title="Users-service", lifespan=life_span)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(users.router)
app.include_router(bank_account.router, prefix="/users")


@app.get("/health")
async def health():
    return {"status": "healthy", "service": "users-service"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8001)