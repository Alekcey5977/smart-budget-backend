from fastapi import APIRouter, Depends, HTTPException, Request
import httpx
import os
from typing import List
from app.dependencies import get_current_user

router = APIRouter(
    prefix="/users/me",
    tags=["bank_accounts"]
)

USERS_SERVICE_URL = os.getenv("USERS_SERVICE_URL")


@router.post(
    "/bank_account",
    summary="Добавить банковский счет",
    description="""
    Добавляет новый банковский счет к профилю пользователя. Номер счета проверяется в псевдо банке, затем автоматически синхронизируются все транзакции.

    **Требует авторизации:** JWT токен в заголовке Authorization.

    ## Процесс добавления счета

    1. Система проверяет, не добавлен ли уже этот счет
    2. Номер счета валидируется в псевдо банке
    3. Счет привязывается к вашему профилю
    4. Автоматически запускается синхронизация транзакций

    ## Параметры запроса

    | Поле | Тип | Обязательно | Описание |
    |------|-----|-------------|----------|
    | `bank_account_number` | string | Да | Номер банковского счета (мин. 16 цифр) |
    | `bank_account_name` | string | Да | Произвольное название для счета |
    | `bank` | string | Да | Название банка |

    ## Пример запроса

    ```json
    {
        "bank_account_number": "40817810099910004312",
        "bank_account_name": "Моя основная карта",
        "bank": "Сбербанк"
    }
    ```

    ## Тестовые номера счетов

    | Номер счета | Название | Баланс |
    |-------------|----------|--------|
    | `40817810099910004312` | Основная карта | 125,450.75 ₽ |
    | `40817810099910004313` | Накопительная | 50,000.00 ₽ |
    | `40817810099910004314` | Зарплатная | 78,230.50 ₽ |
    | `40817810099910004315` | Повседневная | 23,100.00 ₽ |

    ## Пример успешного ответа

    ```json
    {
        "bank_account_id": 1,
        "bank_account_name": "Основная карта",
        "currency": "RUB",
        "bank": "Сбербанк",
        "balance": "125450.75"
    }
    ```

    ## Возможные ошибки

    - **400 Bad Request:**
        - Счет уже добавлен к вашему профилю
        - Счет не существует в банковской системе
        - Номер счета слишком короткий (менее 16 символов)
    - **401 Unauthorized:** Невалидный или отсутствующий токен
    - **404 Not Found:** Пользователь не найден
    - **504 Gateway Timeout:** Псевдо банк не отвечает
    """,
    responses={
        200: {
            "description": "Счет успешно добавлен",
            "content": {
                "application/json": {
                    "example": {
                        "bank_account_id": 1,
                        "bank_account_name": "Основная карта",
                        "currency": "RUB",
                        "bank": "Сбербанк",
                        "balance": "125450.75"
                    }
                }
            }
        },
        400: {
            "description": "Некорректные данные",
            "content": {
                "application/json": {
                    "examples": {
                        "duplicate": {
                            "summary": "Счет уже добавлен",
                            "value": {"detail": "Bank account with this number already exists"}
                        },
                        "not_found_in_bank": {
                            "summary": "Счет не найден в банке",
                            "value": {"detail": "Bank account does not exist in the bank system"}
                        },
                        "short_number": {
                            "summary": "Слишком короткий номер",
                            "value": {"detail": "Bank account number must be at least 16 digits"}
                        }
                    }
                }
            }
        },
        401: {"description": "Не авторизован"},
        404: {"description": "Пользователь не найден"},
        504: {"description": "Таймаут при добавлении счета"}
    }
)
async def add_bank_account(
    request: Request,
    bank_account: dict,
    current_user: dict = Depends(get_current_user)
):
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            # Передаем cookies из оригинального запроса (refresh_token)
            cookies = dict(request.cookies)

            response = await client.post(
                f"{USERS_SERVICE_URL}/users/me/bank_account",
                json=bank_account,
                headers={"Authorization": f"Bearer {current_user.get('token')}"},
                cookies=cookies
            )

            if response.status_code == 400:
                error_detail = response.json().get("detail", "Bad request")
                raise HTTPException(status_code=400, detail=error_detail)
            elif response.status_code == 404:
                raise HTTPException(
                    status_code=404,
                    detail="Счет не найден в банковской системе"
                )

            response.raise_for_status()
            return response.json()

        except httpx.TimeoutException:
            raise HTTPException(
                status_code=504,
                detail="Таймаут при добавлении счета"
            )
        except httpx.HTTPStatusError as e:
            raise HTTPException(
                status_code=e.response.status_code,
                detail=f"Ошибка: {e.response.text}"
            )


@router.get(
    "/bank_accounts",
    summary="Получить все банковские счета",
    description="Возвращает список всех банковских счетов текущего пользователя",
    responses={
        200: {
            "description": "Список банковских счетов",
            "content": {
                "application/json": {
                    "example": [
                        {
                            "bank_account_id": 1,
                            "bank_account_name": "Основная карта",
                            "currency": "RUB",
                            "bank": "Сбербанк",
                            "balance": "125450.75"
                        },
                        {
                            "bank_account_id": 2,
                            "bank_account_name": "Накопительный счет",
                            "currency": "RUB",
                            "bank": "Тинькофф",
                            "balance": "50000.00"
                        }
                    ]
                }
            }
        },
        401: {"description": "Не авторизован"},
        504: {"description": "Таймаут при получении счетов"}
    }
)
async def get_bank_accounts(
    request: Request,
    current_user: dict = Depends(get_current_user)
):
    """
    Получить все банковские счета текущего пользователя.

    **Требует авторизации:** JWT токен в заголовке Authorization.

    ## Описание

    Возвращает список всех банковских счетов, привязанных к вашему профилю.
    Каждый счет содержит информацию о балансе, валюте и банке.

    ## Возвращаемые поля

    | Поле | Тип | Описание |
    |------|-----|----------|
    | `bank_account_id` | integer | Уникальный ID счета в системе |
    | `bank_account_name` | string | Название счета (заданное при добавлении) |
    | `currency` | string | Код валюты (RUB, USD, EUR) |
    | `bank` | string | Название банка |
    | `balance` | string | Текущий баланс счета |

    ## Пример успешного ответа

    ```json
    [
        {
            "bank_account_id": 1,
            "bank_account_name": "Основная карта",
            "currency": "RUB",
            "bank": "Сбербанк",
            "balance": "125450.75"
        },
        {
            "bank_account_id": 2,
            "bank_account_name": "Накопительный счет",
            "currency": "RUB",
            "bank": "Тинькофф",
            "balance": "50000.00"
        }
    ]
    ```

    ## Пример пустого ответа

    Если у пользователя нет добавленных счетов:
    ```json
    []
    ```

    ## Возможные ошибки

    - **401 Unauthorized:** Невалидный или отсутствующий токен
    - **504 Gateway Timeout:** Сервис пользователей не отвечает
    """
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            cookies = dict(request.cookies)

            response = await client.get(
                f"{USERS_SERVICE_URL}/users/me/bank_accounts",
                headers={"Authorization": f"Bearer {current_user.get('token')}"},
                cookies=cookies
            )

            response.raise_for_status()
            return response.json()

        except httpx.TimeoutException:
            raise HTTPException(
                status_code=504,
                detail="Таймаут при получении счетов"
            )
        except httpx.HTTPStatusError as e:
            raise HTTPException(
                status_code=e.response.status_code,
                detail=f"Ошибка: {e.response.text}"
            )


@router.delete(
    "/bank_account/{bank_account_id}",
    status_code=204,
    summary="Удалить банковский счет",
    description="Удаляет банковский счет из профиля пользователя",
    responses={
        204: {
            "description": "Счет успешно удален (без тела ответа)"
        },
        401: {"description": "Не авторизован"},
        404: {
            "description": "Счет не найден",
            "content": {
                "application/json": {
                    "example": {"detail": "Банковский счет не найден"}
                }
            }
        },
        504: {"description": "Таймаут при удалении счета"}
    }
)
async def delete_bank_account(
    bank_account_id: int,
    request: Request,
    current_user: dict = Depends(get_current_user)
):
    """
    Удалить банковский счет из профиля пользователя.

    **Требует авторизации:** JWT токен в заголовке Authorization.

    ## Описание

    Удаляет привязку банковского счета к вашему профилю.

    **ВАЖНО:**
    - Удаляется только связь между вашим профилем и счетом
    - Все транзакции по этому счету остаются в базе данных
    - Вы можете снова добавить этот счет позже

    ## Параметры запроса

    | Параметр | Тип | Расположение | Описание |
    |----------|-----|--------------|----------|
    | `bank_account_id` | integer | Path | ID счета для удаления (из GET /bank_accounts) |

    ## Пример запроса

    ```
    DELETE /users/me/bank_account/1
    ```

    ## Успешный ответ

    - **Код:** 204 No Content
    - **Тело:** Пустое

    ## Возможные ошибки

    - **401 Unauthorized:** Невалидный или отсутствующий токен
    - **404 Not Found:**
        - Счет с указанным ID не существует
        - Счет существует, но не привязан к вашему профилю
    - **504 Gateway Timeout:** Сервис пользователей не отвечает

    ## Пример использования

    1. Получите список своих счетов: `GET /users/me/bank_accounts`
    2. Выберите `bank_account_id` счета для удаления
    3. Вызовите `DELETE /users/me/bank_account/{bank_account_id}`
    """
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            cookies = dict(request.cookies)

            response = await client.delete(
                f"{USERS_SERVICE_URL}/users/me/bank_account/{bank_account_id}",
                headers={"Authorization": f"Bearer {current_user.get('token')}"},
                cookies=cookies
            )

            if response.status_code == 404:
                raise HTTPException(
                    status_code=404,
                    detail="Банковский счет не найден"
                )

            response.raise_for_status()
            return None

        except httpx.TimeoutException:
            raise HTTPException(
                status_code=504,
                detail="Таймаут при удалении счета"
            )
        except httpx.HTTPStatusError as e:
            raise HTTPException(
                status_code=e.response.status_code,
                detail=f"Ошибка: {e.response.text}"
            )
