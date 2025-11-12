from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.routers import auth, transactions

app = FastAPI(title="Gateway Service", description="Точка входа", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(transactions.router)

@app.get("/health")
async def health():
    return {
        "status": "healthy", 
        "service": "gateway",
        "version": "1.0.0"
    }

if __name__ == "__main__":
    uvicorn.run(
        app, 
        host="0.0.0.0",
        port=8000
    )