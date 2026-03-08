from typing import List
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.repository.history_repository import HistoryRepository
from app.schemas import HistoryEntryResponse, DeleteResponse
from app.dependencies import get_user_id_from_header
from uuid import UUID


router = APIRouter(prefix="/history", tags=["history"])


async def get_history_repository(db: AsyncSession = Depends(get_db)):
    return HistoryRepository(db)


@router.get(
    "/user/me",
    response_model=List[HistoryEntryResponse],
    summary="Получить историю действий пользователя",
    description="""
Получить список записей истории текущего пользователя с поддержкой пагинации.

**Аутентификация:** X-User-ID заголовок (передаётся gateway автоматически из JWT токена).

Записи возвращаются отсортированными от новых к старым (по дате создания).

## Параметры пагинации
- `skip`: Пропустить N первых записей (по умолчанию 0)
- `limit`: Максимальное количество возвращаемых записей (по умолчанию 100, макс 100)

## Источник записей
Записи создаются автоматически при наступлении доменных событий:
- Создание / изменение / удаление цели
- Добавление / удаление банковского счёта
- Изменение профиля или аватара пользователя
""",
    responses={
        200: {
            "description": "Список записей истории",
            "content": {
                "application/json": {
                    "example": [
                        {
                            "id": "550e8400-e29b-41d4-a716-446655440000",
                            "user_id": 1,
                            "title": "Цель создана",
                            "body": "Цель «Отпуск в Турции» на сумму 150000 руб. создана",
                            "created_at": "2026-01-21T10:30:00"
                        },
                        {
                            "id": "660f9511-f30c-52e5-b827-55766541b001",
                            "user_id": 1,
                            "title": "Банковский счёт добавлен",
                            "body": "Добавлен счёт «Сбербанк» с балансом 50000 руб.",
                            "created_at": "2026-01-20T15:20:00"
                        }
                    ]
                }
            }
        },
        422: {"description": "X-User-ID заголовок отсутствует или невалиден"}
    }
)
async def get_history_by_user(
    user_id: int = Depends(get_user_id_from_header),
    skip: int = Query(0, ge=0, description="Пропустить N записей (для пагинации)"),
    limit: int = Query(100, ge=1, le=100, description="Максимум записей на страницу"),
    repo: HistoryRepository = Depends(get_history_repository)
):
    """Получение истории действий пользователя"""
    entries = await repo.get_entries_by_user(user_id, skip, limit)
    return entries


@router.get(
    "/{entry_id}",
    response_model=HistoryEntryResponse,
    summary="Получить запись истории по ID",
    description="""
Получить конкретную запись истории по её UUID.

**Аутентификация:** Не требует X-User-ID — запись доступна по прямому UUID.

Если запись с указанным ID не найдена, возвращается ошибка 404.
""",
    responses={
        200: {
            "description": "Данные записи истории",
            "content": {
                "application/json": {
                    "example": {
                        "id": "550e8400-e29b-41d4-a716-446655440000",
                        "user_id": 1,
                        "title": "Цель создана",
                        "body": "Цель «Отпуск в Турции» на сумму 150000 руб. создана",
                        "created_at": "2026-01-21T10:30:00"
                    }
                }
            }
        },
        404: {"description": "Запись истории не найдена"}
    }
)
async def get_history_entry(
    entry_id: UUID,
    repo: HistoryRepository = Depends(get_history_repository)
):
    """Получение записи истории по ID"""
    entry = await repo.get_entry_by_id(entry_id)

    if not entry:
        raise HTTPException(status_code=404, detail="History entry not found")

    return entry


@router.delete(
    "/{entry_id}",
    response_model=DeleteResponse,
    summary="Удалить запись истории",
    description="""
Удалить конкретную запись истории.

**Аутентификация:** X-User-ID заголовок (передаётся gateway автоматически из JWT токена).

**Безопасность:** Можно удалить только собственную запись.
Если запись не найдена или принадлежит другому пользователю — возвращается ошибка 404.
""",
    responses={
        200: {
            "description": "Запись успешно удалена",
            "content": {
                "application/json": {
                    "example": {
                        "status": "success",
                        "message": "History entry deleted"
                    }
                }
            }
        },
        404: {"description": "Запись не найдена или доступ запрещён"},
        422: {"description": "X-User-ID заголовок отсутствует или невалиден"}
    }
)
async def delete_history_entry(
    entry_id: UUID,
    user_id: int = Depends(get_user_id_from_header),
    repo: HistoryRepository = Depends(get_history_repository)
):
    """Удаление записи истории"""
    rowcount = await repo.delete_entry(entry_id, user_id)

    if rowcount == 0:
        raise HTTPException(status_code=404, detail="History entry not found or access denied")

    return {"status": "success", "message": "History entry deleted"}
