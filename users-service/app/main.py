from fastapi import FastAPI
from app.database import create_tables, shutdown

from .models import *
from contextlib import asynccontextmanager
import uvicorn



@asynccontextmanager
async def life_span(app: FastAPI):
    await create_tables()
    yield
    await shutdown()


app = FastAPI(lifespan=life_span)

@app.get("/health")
async def health():
    return {"status": "healthy", "service": "users-service"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8001)