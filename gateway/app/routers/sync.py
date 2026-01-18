import os
from fastapi import APIRouter, Depends, HTTPException, Request
import httpx
from app.dependencies import get_current_user
from typing import Dict

router = APIRouter(prefix="/sync", tags=["sync"])

TRANSACTIONS_SERVICE_URL = os.getenv("TRANSACTIONS_SERVICE_URL", "http://transactions-service:8002")
USERS_SERVICE_URL = os.getenv("USERS_SERVICE_URL", "http://users-service:8001")


@router.post(
    "",
    summary="Синхронизировать все счета пользователя",
    description="""
    Синхронизирует все банковские счета текущего пользователя с псевдо банком.

    **Кто вызывает:**
    - Фронтенд - кнопка "Обновить данные" / "Синхронизировать"
    - Автоматически при первом входе пользователя
    - Автоматический планировщик (каждые 10 минут - уже работает внутри transactions-service)

    **Что происходит:**
    1. Получаем список всех счетов пользователя из users-service
    2. Для каждого счета вызываем синхронизацию в transactions-service
    3. Transactions-service копирует новые транзакции из псевдо банка
    """,
    responses={
        200: {
            "description": "Синхронизация выполнена",
            "content": {
                "application/json": {
                    "example": {
                        "synced_accounts": 3,
                        "total_transactions": 45,
                        "details": [
                            {
                                "account_name": "Основная карта",
                                "new_transactions": 15
                            },
                            {
                                "account_name": "Накопительная",
                                "new_transactions": 10
                            },
                            {
                                "account_name": "Зарплатная",
                                "new_transactions": 20
                            }
                        ]
                    }
                }
            }
        },
        401: {"description": "Не авторизован"},
        504: {"description": "Таймаут синхронизации"}
    }
)
async def sync_all_user_accounts(
    request: Request,
    current_user: dict = Depends(get_current_user)
):
    """
    Синхронизировать все банковские счета пользователя.

    ## Назначение

    Это основная ручка синхронизации, которую должен вызывать фронтенд.

    ## Автоматическая синхронизация

    **Важно:** Внутри transactions-service уже работает автоматический планировщик,
    который синхронизирует все счета каждые 10 минут. Эта ручка нужна для:
    - Ручной синхронизации по требованию пользователя
    - Первичной синхронизации при добавлении нового счета

    ## Процесс синхронизации

    1. Gateway получает список всех счетов пользователя из users-service
    2. Для каждого счета вызывается transactions-service
    3. Transactions-service получает новые транзакции из псевдо банка
    4. Транзакции сохраняются с правильным user_id

    ## Примечания

    - Синхронизация инкрементальная (только новые транзакции)
    - user_id из псевдо банка (999) заменяется на реальный ID пользователя
    - Дубликаты не создаются благодаря проверкам в БД
    """
    user_id = current_user["user_id"]

    try:
        # 1. Получаем все счета пользователя
        cookies = dict(request.cookies)
        async with httpx.AsyncClient(timeout=10.0) as client:
            accounts_response = await client.get(
                f"{USERS_SERVICE_URL}/users/me/bank_accounts",
                headers={"Authorization": f"Bearer {current_user.get('token')}"},
                cookies=cookies
            )
            accounts_response.raise_for_status()
            accounts = accounts_response.json()

        if not accounts:
            return {
                "synced_accounts": 0,
                "total_transactions": 0,
                "details": [],
                "message": "У вас нет добавленных банковских счетов"
            }

        # 2. Синхронизируем все счета пользователя одним запросом
        results = []

        async with httpx.AsyncClient(timeout=60.0) as client:
            try:
                sync_response = await client.post(
                    f"{TRANSACTIONS_SERVICE_URL}/transactions/sync_user_accounts",
                    json={"user_id": user_id}
                )

                if sync_response.status_code == 200:
                    # Синхронизация прошла успешно для всех счетов
                    for account in accounts:
                        results.append({
                            "account_name": account.get("bank_account_name"),
                            "status": "success"
                        })
                else:
                    # Ошибка синхронизации
                    for account in accounts:
                        results.append({
                            "account_name": account.get("bank_account_name"),
                            "status": "failed",
                            "error": f"HTTP {sync_response.status_code}"
                        })

            except Exception as e:
                # Если произошла ошибка, отмечаем все счета как failed
                for account in accounts:
                    results.append({
                        "account_name": account.get("bank_account_name"),
                        "status": "failed",
                        "error": str(e)
                    })

        return {
            "synced_accounts": len([r for r in results if r["status"] == "success"]),
            "total_accounts": len(accounts),
            "details": results
        }

    except httpx.TimeoutException:
        raise HTTPException(
            status_code=504,
            detail="Таймаут при синхронизации счетов"
        )
    except httpx.HTTPStatusError as e:
        raise HTTPException(
            status_code=e.response.status_code,
            detail=f"Ошибка при получении счетов: {e.response.text}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Внутренняя ошибка: {str(e)}"
        )


@router.post(
    "/{bank_account_id}",
    summary="Синхронизировать один конкретный счет",
    description="""
    Синхронизирует один конкретный банковский счет по его ID.

    **Использование:**
    - Фронтенд - кнопка "Обновить" возле конкретного счета
    - После добавления нового счета (автоматически в background)
    """,
    responses={
        200: {
            "description": "Счет успешно синхронизирован",
            "content": {
                "application/json": {
                    "example": {
                        "account_name": "Основная карта",
                        "new_transactions": 5,
                        "last_sync": "2024-01-15T14:30:00"
                    }
                }
            }
        },
        401: {"description": "Не авторизован"},
        404: {"description": "Счет не найден или не принадлежит пользователю"},
        504: {"description": "Таймаут синхронизации"}
    }
)
async def sync_single_account(
    bank_account_id: int,
    request: Request,
    current_user: dict = Depends(get_current_user)
):
    """
    Синхронизировать один конкретный банковский счет.

    ## Параметры

    | Параметр | Тип | Расположение | Описание |
    |----------|-----|--------------|----------|
    | `bank_account_id` | integer | Path | ID счета из GET /users/me/bank_accounts |

    ## Пример использования

    1. Получите список счетов: `GET /users/me/bank_accounts`
    2. Выберите `bank_account_id` нужного счета
    3. Вызовите `POST /sync/{bank_account_id}`

    ## Процесс

    1. Gateway получает информацию о счете из users-service
    2. Проверяет, что счет принадлежит текущему пользователю
    3. Получает хеш счета
    4. Вызывает синхронизацию в transactions-service
    """
    user_id = current_user["user_id"]

    try:
        # 1. Получаем информацию о счете
        cookies = dict(request.cookies)
        async with httpx.AsyncClient(timeout=10.0) as client:
            accounts_response = await client.get(
                f"{USERS_SERVICE_URL}/users/me/bank_accounts",
                headers={"Authorization": f"Bearer {current_user.get('token')}"},
                cookies=cookies
            )
            accounts_response.raise_for_status()
            accounts = accounts_response.json()

        # 2. Ищем нужный счет
        target_account = next((acc for acc in accounts if acc.get("bank_account_id") == bank_account_id), None)

        if not target_account:
            raise HTTPException(
                status_code=404,
                detail="Счет не найден или не принадлежит вам"
            )

        # 3. Синхронизируем через transactions-service
        async with httpx.AsyncClient(timeout=30.0) as client:
            sync_response = await client.post(
                f"{TRANSACTIONS_SERVICE_URL}/transactions/sync_user_accounts",
                json={"user_id": user_id}
            )
            sync_response.raise_for_status()

            return {
                "account_name": target_account.get("bank_account_name"),
                "status": "success",
                "message": "Синхронизация завершена"
            }

    except HTTPException:
        raise
    except httpx.TimeoutException:
        raise HTTPException(
            status_code=504,
            detail="Таймаут синхронизации"
        )
    except httpx.HTTPStatusError as e:
        raise HTTPException(
            status_code=e.response.status_code,
            detail=f"Ошибка синхронизации: {e.response.text}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Внутренняя ошибка: {str(e)}"
        )