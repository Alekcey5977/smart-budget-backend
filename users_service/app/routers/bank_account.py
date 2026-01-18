from typing import List
from fastapi import Depends, HTTPException, status, Request, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.schemas import oauth2_scheme, Bank_accountResponse, Bank_AccountCreate
from app.auth import verify_token
from app.repository.bank_account_repository import Bank_AccountRepository
from app.repository.user_repository import UserRepository
from app.routers.users import router, get_bank_account_repository, get_user_repository


# Получение репозитория банковских счетов
async def get_bank_account_repository(db: AsyncSession = Depends(get_db)):
    """Dependency для получения репозитория"""
    return Bank_AccountRepository(db)



# Добавление банковского счета
@router.post("/me/bank_account", response_model=Bank_accountResponse)
async def add_bank_account(
    request: Request,
    bank_account: Bank_AccountCreate,
    background_tasks: BackgroundTasks,
    token: str = Depends(oauth2_scheme),
    bank_account_repo: Bank_AccountRepository = Depends(
        get_bank_account_repository),
    user_repo: UserRepository = Depends(get_user_repository)
):
    """Добавление счёта в личном кабинете"""

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

    new_account, account_hash = await bank_account_repo.create(user_id, bank_account)

    # Запускаем синхронизацию транзакций в фоне
    background_tasks.add_task(bank_account_repo.trigger_transaction_sync, account_hash, user_id)

    # Преобразуем в response с названием банка
    return {
        "bank_account_id": new_account.bank_account_id,
        "bank_account_name": new_account.bank_account_name,
        "currency": new_account.currency,
        "bank": new_account.bank.name,
        "balance": new_account.balance
    }


# Получение всех банковских счетов пользователя
@router.get("/me/bank_accounts", response_model=List[Bank_accountResponse])
async def get_user_bank_accounts(
    request: Request,
    token: str = Depends(oauth2_scheme),
    bank_account_repo: Bank_AccountRepository = Depends(get_bank_account_repository),
    user_repo: UserRepository = Depends(get_user_repository)
):
    """Получить все банковские счета текущего пользователя"""

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

    accounts = await bank_account_repo.get_all_by_user_id(user_id)

    # Преобразуем в response с названиями банков
    return [
        {
            "bank_account_id": acc.bank_account_id,
            "bank_account_name": acc.bank_account_name,
            "currency": acc.currency,
            "bank": acc.bank.name,
            "balance": acc.balance
        }
        for acc in accounts
    ]


# Удаление банковского счета
@router.delete("/me/bank_account/{bank_account_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_bank_account(
    bank_account_id: int,
    request: Request,
    token: str = Depends(oauth2_scheme),
    bank_account_repo: Bank_AccountRepository = Depends(get_bank_account_repository),
    user_repo: UserRepository = Depends(get_user_repository)
):
    """Удалить банковский счет"""

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

    account = await bank_account_repo.delete(bank_account_id, user_id)
    if account is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Bank account not found"
        )

    return None
