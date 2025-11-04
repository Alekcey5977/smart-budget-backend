from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.schemas import UserResponse, Token, UserUpdate, UserCreate, UserLogin
from app.repository.user_repository import UserRepository
from app.database import get_db
from app.auth import create_access_token, get_password_hash, verify_password, verify_token

router = APIRouter(prefix="/users", tags=["users"])

ACCESS_TOKEN_EXPIRE_MINUTES = 20


# Получение пользовательского репозитория
async def get_user_repository(db: AsyncSession = Depends(get_db)):
    """Dependency для получения репозитория"""
    return UserRepository(db)


# Регистрация пользователя
@router.post("/register", response_model=UserResponse)
async def register(
    user_data: UserCreate,
    user_repo: UserRepository = Depends(get_user_repository)
):
    if await user_repo.exists_with_email(user_data.email):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    hashed_password = get_password_hash(user_data.password)
    db_user = await user_repo.create(user_data, hashed_password)

    return db_user


# Авторизация пользователя
@router.post("/login", response_model=Token)
async def login(
    user_data: UserLogin,
    user_repo: UserRepository = Depends(get_user_repository)
):
    
    user = await user_repo.get_by_email(user_data.email)
    
    if not user or not verify_password(user_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password"
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user"
        )

    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": str(user.id)}, expires_delta=access_token_expires
    )

    return {"access_token": access_token, "token_type": "bearer"}


# Открытие профиля
@router.get("/me", response_model=UserResponse)
async def get_current_user(
    token: str,
    user_repo: UserRepository = Depends(get_user_repository)
):
    payload = verify_token(token)
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token"
        )

    user_id = int(payload.get("sub"))
    user = await user_repo.get_by_id(user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    return user


# Редактирование профиля
@router.put("/me", response_model=UserResponse)
async def update_current_user(
    user_update: UserUpdate,
    token: str,
    user_repo: UserRepository = Depends(get_user_repository)
):
    payload = verify_token(token)
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token"
        )

    user_id = int(payload.get("sub"))
    user = await user_repo.update(user_id, user_update)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    return user
