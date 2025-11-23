from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import and_, select
from app.models import User
from app.schemas import UserCreate, UserUpdate

class UserRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    
    async def get_by_id(self, user_id: int):
        """Получить пользователя по ID"""
        result = await self.db.execute(
            select(User).where(User.id == user_id)
        )
        return result.scalar_one_or_none()

    
    async def get_by_email(self, email: str):
        """Получить пользователя по email"""
        result = await self.db.execute(
            select(User).where(User.email == email)
        )
        return result.scalar_one_or_none()

    
    async def create(self, user_data: UserCreate, hashed_password: str):
        """Создать нового пользователя"""
        db_user = User(
            email=user_data.email,
            first_name=user_data.first_name,
            last_name=user_data.last_name,
            middle_name=user_data.middle_name,
            hashed_password=hashed_password,
        )
        self.db.add(db_user)
        await self.db.commit()
        await self.db.refresh(db_user)
        return db_user
    
    
    async def update(self, user_id: int, user_update: UserUpdate):
        """Обновить данные пользователя"""
        db_user = await self.get_by_id(user_id)

        if db_user:
            update_data = user_update.model_dump(exclude_unset=True)
            for field, value in update_data.items():
                # Пустая строка для middle_name означает удаление (NULL в БД)
                if field == "middle_name" and value == "":
                    value = None
                setattr(db_user, field, value)
            await self.db.commit()
            await self.db.refresh(db_user)
        return db_user
    
    
    async def exists_with_email(self, email: str):
        """Проверить существование пользователя с email"""
        user = await self.get_by_email(email)
        return user is not None
    
    
