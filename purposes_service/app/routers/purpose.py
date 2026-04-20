from typing import List
from uuid import UUID

from app.database import get_db
from app.dependencies import get_user_id_from_header
from app.repository.purpose_repository import PurposeRepository
from app.schemas import PurposeCreate, PurposeResponse, PurposeUpdate
from fastapi import APIRouter, Depends, HTTPException
from fastapi.encoders import jsonable_encoder
from sqlalchemy.ext.asyncio import AsyncSession

from shared.cache import cache_client

router = APIRouter(prefix="/purpose", tags=["purposes"])

_PURPOSES_TTL = 30


async def get_purpose_repository(db: AsyncSession = Depends(get_db)):
    return PurposeRepository(db)


@router.post("/create", response_model=PurposeResponse)
async def create_purpose(
    purpose: PurposeCreate,
    user_id: int = Depends(get_user_id_from_header),
    repo: PurposeRepository = Depends(get_purpose_repository),
):
    """Создание цели"""
    purpose = await repo.create_purpose(user_id, purpose)
    try:
        await cache_client.delete(f"purposes:{user_id}")
    except Exception:
        pass
    return purpose


@router.get("/my", response_model=List[PurposeResponse])
async def get_purposes_by_user(
    user_id: int = Depends(get_user_id_from_header),
    repo: PurposeRepository = Depends(get_purpose_repository),
):
    """Получение целей пользователя"""
    cache_key = f"purposes:{user_id}"
    try:
        cached = await cache_client.get(cache_key)
        if cached is not None:
            return cached
    except Exception:
        pass

    purposes = await repo.get_purposes_by_user(user_id)
    result = jsonable_encoder(purposes)

    try:
        await cache_client.set(cache_key, result, ttl=_PURPOSES_TTL)
    except Exception:
        pass

    return result


@router.put("/update/{purpose_id}", response_model=PurposeResponse)
async def update_purpose(
    purpose_id: UUID,
    purpose_update: PurposeUpdate,
    user_id: int = Depends(get_user_id_from_header),
    repo: PurposeRepository = Depends(get_purpose_repository),
):
    """Обновление цели"""
    update_data = purpose_update.model_dump(exclude_none=True)

    if not update_data:
        raise HTTPException(status_code=400, detail="No fields to update")

    purpose = await repo.update_purpose(user_id, purpose_id, update_data)
    if not purpose:
        raise HTTPException(status_code=404, detail="Purpose not found")

    try:
        await cache_client.delete(f"purposes:{user_id}")
    except Exception:
        pass

    return purpose


@router.delete("/delete/{purpose_id}")
async def delete_purpose(
    purpose_id: UUID,
    user_id: int = Depends(get_user_id_from_header),
    repo: PurposeRepository = Depends(get_purpose_repository),
):
    """Удаление цели"""
    deleted_purpose = await repo.delete_purpose(user_id, purpose_id)
    if deleted_purpose is None:
        raise HTTPException(status_code=404, detail="Purpose not found or access denied")

    try:
        await cache_client.delete(f"purposes:{user_id}")
    except Exception:
        pass

    return deleted_purpose
