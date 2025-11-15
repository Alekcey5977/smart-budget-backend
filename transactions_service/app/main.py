from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.database import create_tables, shutdown
from app.models import *
from contextlib import asynccontextmanager
import uvicorn


@asynccontextmanager
async def life_span(app: FastAPI):
    await create_tables()
    yield
    await shutdown()


app = FastAPI(title="Transactions", lifespan=life_span)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)



@app.get("/health")
async def health():
    return {"status": "healthy", "service": "transactions"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8002)
