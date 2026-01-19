from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


class PurposeRepository:
    def __init__(self, db: AsyncSession):
        self.db = db
    