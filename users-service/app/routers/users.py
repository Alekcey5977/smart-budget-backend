from datetime import timedelta
from urllib import response
from fastapi import APIRouter, Depends, HTTPException, status, Response, Request
from sqlalchemy.ext.asyncio import AsyncSession
from app.schemas import UserResponse, Token, UserUpdate, UserCreate, UserLogin
from app.repository.user_repository import UserRepository
from app.database import get_db
from app.auth import ALGORITHM, REFRESH_SECRET_KEY, create_access_token, create_refresh_token, get_password_hash, verify_password, verify_token
from jose import jwt


router = APIRouter(prefix="/users", tags=["users"])

ACCESS_TOKEN_EXPIRE_MINUTES = 20
REFRESH_TOKEN_EXPIRE_DAYS = 7

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
    response: Response,
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
    refresh_token_expires = timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    refresh_token = create_refresh_token(
        data={"sub": str(user.id)}, expires_delta=refresh_token_expires)

    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=False,  # True в продакшене
        samesite="strict",
        max_age=7 * 24 * 3600
    )


    return {"access_token": access_token, "token_type": "bearer"}


# Обновление refresh токена
@router.post("/refresh", response_model=Token)
async def refresh_token(
    response: Response,
    request: Request,
    user_repo: UserRepository = Depends(get_user_repository)
):
    refresh_token = request.cookies.get("refresh_token")
    if not refresh_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token missing"
        )

    try:
        payload = jwt.decode(
            refresh_token,
            REFRESH_SECRET_KEY,
            algorithms=[ALGORITHM],
            options={"require": ["exp", "iat", "type", "jti"]}
        )

        if payload.get("type") != "refresh":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token type"
            )

        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token claims"
            )


        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        new_access_token = create_access_token(
            data={"sub": user_id}, expires_delta=access_token_expires
        )

        new_refresh_token = create_refresh_token(
            data={"sub": user_id}, expires_delta=timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
        )

        response.set_cookie(
            key="refresh_token",
            value=new_refresh_token,
            httponly=True,
            secure=False,  # True в продакшене
            samesite="strict",
            max_age=REFRESH_TOKEN_EXPIRE_DAYS * 24 * 3600
        )

        return {"access_token": new_access_token, "token_type": "bearer"}

    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token expired"
        )
    except jwt.JWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token"
        )

# Выход из системы
@router.post("/logout")
async def logout(response: Response):
    response.delete_cookie(
        key="refresh_token",
        secure=False,  # True в продакшене
        samesite="strict"
    )
    return {"msg": "Logged out"}


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
