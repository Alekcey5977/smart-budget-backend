from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.schemas import oauth2_scheme, Bank_accountResponse, Bank_AccountCreate
from users_service.app.auth import verify_token
from users_service.app.repository.bank_account_repository import Bank_AccountRepository
from users_service.app.repository.user_repository import UserRepository
from users_service.app.routers.users import router, get_bank_account_repository, get_user_repository
from users_service.app.schemas import Bank_AccountCreate


# Получение репозитория банковских счетов
async def get_bank_account_repository(db: AsyncSession = Depends(get_db)):
    """Dependency для получения репозитория"""
    return Bank_AccountRepository(db)



# Добавление банковского счета
@router.post("/me/bank_account", response_model=Bank_accountResponse)
async def add_bank_account(
    request: Request,
    bank_account: Bank_AccountCreate,
    token: str = Depends(oauth2_scheme),
    bank_account_repo: Bank_AccountRepository = Depends(
        get_bank_account_repository),
    user_repo: UserRepository = Depends(get_user_repository)
):

    refresh_token = request.cookies.get("refresh_token")
    payload = verify_token(token, refresh_token_from_cookie=refresh_token)
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

    account_number = bank_account.bank_account_number
    if not account_number or len(account_number.strip()) < 16:
        raise HTTPException(
            status_code=400,
            detail="Bank account number must be at least 16 digits"
        )

    return await bank_account_repo.create(user_id, bank_account)
