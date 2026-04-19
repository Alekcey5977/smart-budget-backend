from typing import List

from app.auth import verify_token
from app.cache import (
    BANK_ACCOUNTS_TTL,
    bank_accounts_key,
    cache_client,
)
from app.repository.bank_account_repository import Bank_AccountRepository
from app.repository.user_repository import UserRepository
from app.routers.users import get_bank_account_repository, get_user_repository
from app.schemas import Bank_AccountCreate, Bank_accountResponse, oauth2_scheme
from fastapi import APIRouter, Depends, HTTPException, Request, status

router = APIRouter(prefix="/me", tags=["bank_account"])


# --- ЗАВИСИМОСТЬ АВТОРИЗАЦИИ ---
async def get_current_user(
    request: Request, token: str = Depends(oauth2_scheme), user_repo: UserRepository = Depends(get_user_repository)
):
    """Извлекает и валидирует пользователя из токена"""
    refresh_token = request.cookies.get("refresh_token")

    # Вызываем проверку токена
    payload = verify_token(token, refresh_token_from_cookie=refresh_token)

    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    user_id = int(payload.get("sub"))
    user = await user_repo.get_by_id(user_id)

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    return user


@router.post("/bank_account", response_model=Bank_accountResponse)
async def add_bank_account(
    request: Request,
    bank_account: Bank_AccountCreate,
    user=Depends(get_current_user),
    bank_account_repo: Bank_AccountRepository = Depends(
        get_bank_account_repository),
):
    """Добавление счёта в личном кабинете"""
    user_id = user.id

    account_number = bank_account.bank_account_number
    if not account_number or len(account_number.strip()) < 16:
        raise HTTPException(
            status_code=400, detail="Bank account number must be at least 16 digits")

    new_account, _ = await bank_account_repo.create(user_id, bank_account)

    # Инвалидация кэша банковских счетов
    await cache_client.delete(bank_accounts_key(user_id))

    return {
        "bank_account_id": new_account.bank_account_id,
        "bank_account_name": new_account.bank_account_name,
        "currency": new_account.currency,
        "bank": new_account.bank.name,
        "balance": new_account.balance,
    }


@router.get("/bank_accounts", response_model=List[Bank_accountResponse])
async def get_user_bank_accounts(
    user=Depends(get_current_user), bank_account_repo: Bank_AccountRepository = Depends(get_bank_account_repository)
):
    """Получить все банковские счета текущего пользователя"""
    user_id = user.id

    # Cache-Aside: пробуем получить из кэша
    cache_key = bank_accounts_key(user_id)
    cached = await cache_client.get(cache_key)
    if cached is not None:
        return cached

    accounts = await bank_account_repo.get_all_by_user_id(user_id)

    result = [
        {
            "bank_account_id": acc.bank_account_id,
            "bank_account_name": acc.bank_account_name,
            "currency": acc.currency,
            "bank": acc.bank.name,
            "balance": acc.balance,
        }
        for acc in accounts
    ]

    # Сохраняем в кэш
    await cache_client.set(cache_key, result, ttl=BANK_ACCOUNTS_TTL)

    return result


@router.delete("/bank_account/{bank_account_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_bank_account(
    bank_account_id: int,
    user=Depends(get_current_user),
    bank_account_repo: Bank_AccountRepository = Depends(
        get_bank_account_repository),
):
    """Удалить банковский счет"""
    user_id = user.id

    account = await bank_account_repo.delete(bank_account_id, user_id)
    if account is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="Bank account not found")

    # Инвалидация кэша банковских счетов
    await cache_client.delete(bank_accounts_key(user_id))

    return None
