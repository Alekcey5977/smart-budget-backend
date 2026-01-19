from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db


router = APIRouter(prefix="/purpose", tags=["purposes"])


async def get_purpose_repository(db: AsyncSession = Depends(get_db)):
    """Dependency для получения репозитория"""
    return PurposeRepository(db)


@router.post("/create", response_model=PurposeResponse):
