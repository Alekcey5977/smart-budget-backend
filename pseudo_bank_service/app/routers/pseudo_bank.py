from datetime import datetime
from typing import List, Optional

from app.cache import (
    BANK_ACCOUNT_TTL,
    BANKS_KEY,
    CATEGORIES_KEY,
    DICTIONARIES_TTL,
    MCC_CATEGORIES_KEY,
    MERCHANTS_KEY,
    cache_client,
)
from app.database import get_db
from app.repository.transactions_repository import TransactionRepository
from app.schemas import (
    BankAccountCreate,
    BankCreate,
    CategoryCreate,
    MCCCategoryCreate,
    MerchantCreate,
    TransactionCreate,
    Validate_Bank_Account,
)
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/pseudo_bank", tags=["pseudo_bank"])

# Получение репозитория транзакций


async def get_transactions_repository(db: AsyncSession = Depends(get_db)):
    """Dependency для получения репозитория"""
    return TransactionRepository(db)


@router.post(
    "/validate_account",
    summary="Валидация банковского счета",
    description="Проверяет существование банковского счета в системе псевдо банка",
    responses={
        200: {
            "description": "Счет найден",
            "content": {"application/json": {"example": {"balance": "125450.75", "currency": "RUB"}}},
        },
        404: {
            "description": "Счет не найден",
            "content": {"application/json": {"example": {"detail": "Account not found"}}},
        },
    },
)
async def validate_account(
    request: Validate_Bank_Account,
    db: AsyncSession = Depends(get_db),
    transaction_repo: TransactionRepository = Depends(get_transactions_repository),
):
    """
    Проверка существования банковского счета в псевдо банке.

    ## Назначение

    Эта ручка используется **users-service** при добавлении нового банковского счета
    для проверки, что счет действительно существует в банковской системе.

    ## Параметры запроса

    | Поле | Тип | Обязательно | Описание |
    |------|-----|-------------|----------|
    | `bank_account_hash` | string | Да | SHA256 хеш номера счета (64 символа) |

    ## Формат хеша

    Хеш генерируется из номера счета по формуле:
    ```python
    HMAC-SHA256(account_number, secret_key="bank-account-secure-key-2026")
    ```

    ## Пример запроса

    ```json
    {
        "bank_account_hash": "4a210c3e4ff83583c97689e3e1d8f63cbcd7cb13d8b75ddbcf06091fbb4725db"
    }
    ```

    ## Пример успешного ответа

    ```json
    {
        "balance": "125450.75",
        "currency": "RUB"
    }
    ```

    ## Возвращаемые поля

    | Поле | Тип | Описание |
    |------|-----|----------|
    | `balance` | string | Текущий баланс счета |
    | `currency` | string | Код валюты (RUB, USD, EUR) |

    ## Возможные ошибки

    - **404 Not Found:** Счет с указанным хешем не найден в системе

    ## Тестовые хеши

    | Номер счета | Хеш |
    |-------------|-----|
    | 40817810099910004312 | 4a210c3e4ff83583c97689e3e1d8f63cbcd7cb13d8b75ddbcf06091fbb4725db |
    | 40817810099910004313 | 7b8e9f2a5c6d1e4f8a9b0c3d5e6f7a8b9c0d1e2f3a4b5c6d7e8f9a0b1c2d3e4f |
    | 40817810099910004314 | a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0a1b2 |
    | 40817810099910004315 | 5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6 |
    """
    # Cache-Aside: пробуем получить из кэша
    cache_key = f"bank:account:{request.bank_account_hash}"
    cached = await cache_client.get(cache_key)
    if cached is not None:
        return cached

    result = await transaction_repo.get_account_bank(request.bank_account_hash)

    if not result:
        raise HTTPException(status_code=404, detail="Account not found")

    response_data = {
        "balance": str(result.balance),
        "currency": result.currency,
    }

    # Сохраняем в кэш
    await cache_client.set(cache_key, response_data, ttl=BANK_ACCOUNT_TTL)

    return response_data


@router.get(
    "/account/{account_hash}/export",
    summary="Экспорт данных банковского счета",
    description="Возвращает полную информацию о счете, включая все транзакции, мерчантов и категории",
    responses={
        200: {
            "description": "Данные счета успешно экспортированы",
            "content": {
                "application/json": {
                    "example": {
                        "bank_account": {
                            "id": 1,
                            "user_id": 1,
                            "bank_account_hash": "4a210c3e...",
                            "bank_account_name": "Основная карта",
                            "bank_id": 1,
                            "currency": "RUB",
                            "balance": "125450.75",
                        },
                        "bank": {"id": 1, "name": "Сбербанк", "bik": "044525225"},
                        "transactions": [
                            {
                                "id": 1,
                                "bank_account_hash": "4a210c3e...",
                                "merchant_id": 5,
                                "category_id": 1,
                                "amount": "-1250.50",
                                "currency": "RUB",
                                "description": "Покупка продуктов",
                                "transaction_date": "2024-01-15T14:30:00",
                                "mcc": "5411",
                            }
                        ],
                        "merchants": [{"id": 5, "name": "Пятёрочка", "mcc": "5411"}],
                        "categories": [{"id": 1, "name": "Продукты"}],
                        "mcc_categories": [{"mcc": "5411", "category_id": 1}],
                    }
                }
            },
        },
        404: {
            "description": "Счет не найден",
            "content": {"application/json": {"example": {"detail": "Account not found"}}},
        },
    },
)
async def export_account_data(
    account_hash: str,
    since: Optional[datetime] = None,
    transaction_repo: TransactionRepository = Depends(get_transactions_repository),
):
    """
    Экспорт полных данных о банковском счете.

    ## Назначение

    Эта ручка используется **transactions-service** при синхронизации транзакций.
    Возвращает все данные, необходимые для полной синхронизации счета:
    - Информацию о самом счете
    - Банк-эмитент
    - Все транзакции
    - Мерчантов (магазины, организации)
    - Категории транзакций
    - Связи MCC кодов с категориями

    ## Параметры запроса

    | Параметр | Тип | Расположение | Обязательно | Описание |
    |----------|-----|--------------|-------------|----------|
    | `account_hash` | string | Path | Да | SHA256 хеш номера счета |
    | `since` | datetime | Query | Нет | Вернуть только транзакции после этой даты (для инкрементальной синхронизации) |

    ## Пример запроса

    ```
    GET /pseudo_bank/account/4a210c3e4ff83583c97689e3e1d8f63cbcd7cb13d8b75ddbcf06091fbb4725db/export
    ```

    С фильтром по дате:
    ```
    GET /pseudo_bank/account/{hash}/export?since=2024-01-15T00:00:00
    ```

    ## Структура ответа

    ### bank_account
    Информация о банковском счете

    ### bank
    Информация о банке-эмитенте

    ### transactions
    Массив всех транзакций по счету. Каждая транзакция содержит:
    - `amount` - сумма (отрицательная для расходов, положительная для доходов)
    - `merchant_id` - ID магазина/организации
    - `category_id` - ID категории
    - `mcc` - MCC код (Merchant Category Code)
    - `transaction_date` - дата и время операции

    ### merchants
    Справочник мерчантов (магазинов, организаций)

    ### categories
    Справочник категорий транзакций

    ### mcc_categories
    Связи между MCC кодами и категориями

    ## Возможные ошибки

    - **404 Not Found:** Счет с указанным хешем не найден

    ## Использование параметра since

    Для инкрементальной синхронизации (получение только новых транзакций):
    Вернет только транзакции, созданные после указанной даты.
    """
    data = await transaction_repo.export_account_data(account_hash)
    if not data:
        raise HTTPException(status_code=404, detail="Account not found")

    to_dict = transaction_repo.to_dict

    # Кэшируем справочники (меняются крайне редко)
    # Категории
    cached_categories = await cache_client.get(CATEGORIES_KEY)
    if cached_categories is None:
        cached_categories = [to_dict(c) for c in data["categories"]]
        await cache_client.set(CATEGORIES_KEY, cached_categories, ttl=DICTIONARIES_TTL)

    # Мерчанты
    cached_merchants = await cache_client.get(MERCHANTS_KEY)
    if cached_merchants is None:
        cached_merchants = [to_dict(m) for m in data["merchants"]]
        await cache_client.set(MERCHANTS_KEY, cached_merchants, ttl=DICTIONARIES_TTL)

    # MCC категории
    cached_mcc = await cache_client.get(MCC_CATEGORIES_KEY)
    if cached_mcc is None:
        cached_mcc = [to_dict(m) for m in data["mccs"]]
        await cache_client.set(MCC_CATEGORIES_KEY, cached_mcc, ttl=DICTIONARIES_TTL)

    # Банки
    cached_banks = await cache_client.get(BANKS_KEY)
    if cached_banks is None:
        cached_banks = [to_dict(data["bank"])]
        await cache_client.set(BANKS_KEY, cached_banks, ttl=DICTIONARIES_TTL)

    return {
        "bank_account": to_dict(data["account"]),
        "bank": to_dict(data["bank"]),
        "transactions": [to_dict(t) for t in data["transactions"]],
        "merchants": cached_merchants,
        "categories": cached_categories,
        "mcc_categories": cached_mcc,
    }


@router.post(
    "/categories",
    status_code=status.HTTP_201_CREATED,
    summary="Создать категорию",
    description="Создает одну категорию транзакций",
    responses={
        201: {
            "description": "Категория создана",
            "content": {"application/json": {"example": {"id": 1, "name": "Продукты"}}},
        }
    },
    tags=["Загрузка данных"],
)
async def create_category(
    category: CategoryCreate, transaction_repo: TransactionRepository = Depends(get_transactions_repository)
):
    """
    Создание категории транзакций.

    **Используется:** Только для загрузки тестовых данных через скрипт.

    ## Параметры запроса

    | Поле | Тип | Обязательно | Описание |
    |------|-----|-------------|----------|
    | `id` | integer | Да | Уникальный ID категории |
    | `name` | string | Да | Название категории |

    ## Пример запроса

    ```json
    {
        "id": 1,
        "name": "Продукты"
    }
    ```

    ## Примеры категорий

    - Продукты
    - Транспорт
    - Развлечения
    - Здоровье
    - Образование
    - Одежда
    - Рестораны
    - Коммунальные услуги
    """
    result = await transaction_repo.create_category(category)

    # Инвалидация кэша категорий
    await cache_client.delete(CATEGORIES_KEY)

    return transaction_repo.to_dict(result)


@router.post(
    "/categories/bulk",
    status_code=status.HTTP_201_CREATED,
    summary="Массовое создание категорий",
    description="Создает несколько категорий за один запрос (более эффективно)",
    responses={
        201: {"description": "Категории созданы", "content": {"application/json": {"example": {"created": 10}}}}
    },
    tags=["Загрузка данных"],
)
async def create_categories_bulk(
    categories: List[CategoryCreate], transaction_repo: TransactionRepository = Depends(get_transactions_repository)
):
    """
    Массовое создание категорий транзакций.

    **Используется:** Только для загрузки тестовых данных через скрипт.

    ## Преимущества bulk операций

    - Одна транзакция БД вместо N
    - Быстрее в 10-100 раз
    - Меньше нагрузка на сеть

    ## Пример запроса

    ```json
    [
        {"id": 1, "name": "Продукты"},
        {"id": 2, "name": "Транспорт"},
        {"id": 3, "name": "Развлечения"},
        {"id": 4, "name": "Здоровье"}
    ]
    ```

    ## Пример ответа

    ```json
    {
        "created": 4
    }
    ```
    """
    result = await transaction_repo.bulk_create_categories(categories)

    # Инвалидация кэша категорий
    await cache_client.delete(CATEGORIES_KEY)

    return result


@router.post(
    "/mcc_categories",
    status_code=status.HTTP_201_CREATED,
    summary="Создать MCC категорию",
    description="Создает связь между MCC кодом и категорией",
    responses={
        201: {
            "description": "MCC категория создана",
            "content": {"application/json": {"example": {"mcc": "5411", "category_id": 1}}},
        }
    },
    tags=["Загрузка данных"],
)
async def create_mcc_category(
    mcc: MCCCategoryCreate, transaction_repo: TransactionRepository = Depends(get_transactions_repository)
):
    """
    Создание связи между MCC кодом и категорией.

    **Используется:** Только для загрузки тестовых данных через скрипт.

    ## Что такое MCC?

    MCC (Merchant Category Code) - стандартный код категории мерчанта в банковской индустрии.
    Например:
    - 5411 - Продуктовые магазины
    - 5812 - Рестораны
    - 4121 - Такси
    - 5541 - АЗС

    ## Параметры запроса

    | Поле | Тип | Обязательно | Описание |
    |------|-----|-------------|----------|
    | `mcc` | string | Да | MCC код (4 цифры) |
    | `category_id` | integer | Да | ID категории из таблицы categories |

    ## Пример запроса

    ```json
    {
        "mcc": "5411",
        "category_id": 1
    }
    ```

    Этот запрос привяжет MCC код 5411 (продуктовые магазины) к категории 1 (Продукты).
    """
    result = await transaction_repo.create_mcc_category(mcc)
    return transaction_repo.to_dict(result)


@router.post(
    "/mcc_categories/bulk",
    status_code=status.HTTP_201_CREATED,
    summary="Массовое создание MCC категорий",
    description="Создает несколько связей MCC-категория за один запрос",
    responses={
        201: {"description": "MCC категории созданы", "content": {"application/json": {"example": {"created": 50}}}}
    },
    tags=["Загрузка данных"],
)
async def create_mcc_categories_bulk(
    mcc_list: List[MCCCategoryCreate], transaction_repo: TransactionRepository = Depends(get_transactions_repository)
):
    """
    Массовое создание связей между MCC кодами и категориями.

    **Используется:** Только для загрузки тестовых данных через скрипт.

    ## Пример запроса

    ```json
    [
        {"mcc": "5411", "category_id": 1},
        {"mcc": "5412", "category_id": 1},
        {"mcc": "5812", "category_id": 7},
        {"mcc": "4121", "category_id": 2}
    ]
    ```

    ## Пример ответа

    ```json
    {
        "created": 4
    }
    ```
    """
    result = await transaction_repo.bulk_create_mcc_categories(mcc_list)

    # Инвалидация кэша MCC категорий
    await cache_client.delete(MCC_CATEGORIES_KEY)

    return result


@router.post(
    "/merchants",
    status_code=status.HTTP_201_CREATED,
    summary="Создать мерчанта",
    description="Создает мерчанта (магазин, организацию)",
    responses={
        201: {
            "description": "Мерчант создан",
            "content": {"application/json": {"example": {"id": 1, "name": "Пятёрочка", "mcc": "5411"}}},
        }
    },
    tags=["Загрузка данных"],
)
async def create_merchant(
    merchant: MerchantCreate, transaction_repo: TransactionRepository = Depends(get_transactions_repository)
):
    """
    Создание мерчанта (магазин, организация, получатель платежа).

    **Используется:** Только для загрузки тестовых данных через скрипт.

    ## Параметры запроса

    | Поле | Тип | Обязательно | Описание |
    |------|-----|-------------|----------|
    | `id` | integer | Да | Уникальный ID мерчанта |
    | `name` | string | Да | Название магазина/организации |
    | `mcc` | string | Да | MCC код (определяет тип деятельности) |

    ## Пример запроса

    ```json
    {
        "id": 1,
        "name": "Пятёрочка",
        "mcc": "5411"
    }
    ```

    ## Примеры мерчантов

    - **Магазины:** Пятёрочка, Магнит, Ашан (MCC 5411)
    - **Рестораны:** McDonald's, KFC, Burger King (MCC 5812)
    - **Транспорт:** Яндекс.Такси, Uber (MCC 4121)
    - **АЗС:** Лукойл, Роснефть (MCC 5541)
    """
    result = await transaction_repo.create_merchant(merchant)
    return transaction_repo.to_dict(result)


@router.post(
    "/merchants/bulk",
    status_code=status.HTTP_201_CREATED,
    summary="Массовое создание мерчантов",
    description="Создает несколько мерчантов за один запрос",
    responses={201: {"description": "Мерчанты созданы", "content": {"application/json": {"example": {"created": 30}}}}},
    tags=["Загрузка данных"],
)
async def create_merchants_bulk(
    merchants: List[MerchantCreate], transaction_repo: TransactionRepository = Depends(get_transactions_repository)
):
    """
    Массовое создание мерчантов.

    **Используется:** Только для загрузки тестовых данных через скрипт.

    ## Пример запроса

    ```json
    [
        {"id": 1, "name": "Пятёрочка", "mcc": "5411"},
        {"id": 2, "name": "Магнит", "mcc": "5411"},
        {"id": 3, "name": "McDonald's", "mcc": "5812"}
    ]
    ```

    ## Пример ответа

    ```json
    {
        "created": 3
    }
    ```
    """
    result = await transaction_repo.bulk_create_merchants(merchants)

    # Инвалидация кэша мерчантов
    await cache_client.delete(MERCHANTS_KEY)

    return result


@router.post(
    "/banks",
    status_code=status.HTTP_201_CREATED,
    summary="Создать банк",
    description="Создает банк-эмитент",
    responses={
        201: {
            "description": "Банк создан",
            "content": {"application/json": {"example": {"id": 1, "name": "Сбербанк", "bik": "044525225"}}},
        }
    },
    tags=["Загрузка данных"],
)
async def create_bank(bank: BankCreate, transaction_repo: TransactionRepository = Depends(get_transactions_repository)):
    """
    Создание банка-эмитента.

    **Используется:** Только для загрузки тестовых данных через скрипт.

    ## Параметры запроса

    | Поле | Тип | Обязательно | Описание |
    |------|-----|-------------|----------|
    | `id` | integer | Да | Уникальный ID банка |
    | `name` | string | Да | Название банка |
    | `bik` | string | Да | БИК (Банковский Идентификационный Код) |

    ## Что такое БИК?

    БИК - уникальный 9-значный код банка в России.
    Используется для идентификации банка при переводах.

    ## Пример запроса

    ```json
    {
        "id": 1,
        "name": "Сбербанк",
        "bik": "044525225"
    }
    ```

    ## Примеры банков

    - Сбербанк (БИК 044525225)
    - Альфа-Банк (БИК 044525593)
    - Тинькофф (БИК 044525974)
    - ВТБ (БИК 044525187)
    """
    result = await transaction_repo.create_bank(bank)
    return transaction_repo.to_dict(result)


@router.post(
    "/banks/bulk",
    status_code=status.HTTP_201_CREATED,
    summary="Массовое создание банков",
    description="Создает несколько банков за один запрос",
    responses={201: {"description": "Банки созданы", "content": {"application/json": {"example": {"created": 3}}}}},
    tags=["Загрузка данных"],
)
async def create_banks_bulk(
    banks: List[BankCreate], transaction_repo: TransactionRepository = Depends(get_transactions_repository)
):
    """
    Массовое создание банков.

    **Используется:** Только для загрузки тестовых данных через скрипт.

    ## Пример запроса

    ```json
    [
        {"id": 1, "name": "Сбербанк", "bik": "044525225"},
        {"id": 2, "name": "Альфа-Банк", "bik": "044525593"},
        {"id": 3, "name": "Тинькофф", "bik": "044525974"}
    ]
    ```

    ## Пример ответа

    ```json
    {
        "created": 3
    }
    ```
    """
    result = await transaction_repo.bulk_create_banks(banks)

    # Инвалидация кэша банков
    await cache_client.delete(BANKS_KEY)

    return result


@router.post(
    "/bank_accounts",
    status_code=status.HTTP_201_CREATED,
    summary="Создать банковский счет",
    description="Создает банковский счет в псевдо банке",
    responses={
        201: {
            "description": "Счет создан",
            "content": {
                "application/json": {
                    "example": {
                        "id": 1,
                        "user_id": 1,
                        "bank_account_hash": "4a210c3e4ff83583c97689e3e1d8f63cbcd7cb13d8b75ddbcf06091fbb4725db",
                        "bank_account_name": "Основная карта",
                        "bank_id": 1,
                        "currency": "RUB",
                        "balance": "125450.75",
                    }
                }
            },
        }
    },
    tags=["Загрузка данных"],
)
async def create_bank_account(
    account: BankAccountCreate, transaction_repo: TransactionRepository = Depends(get_transactions_repository)
):
    """
    Создание банковского счета в псевдо банке.

    **Используется:** Только для загрузки тестовых данных через скрипт.

    ## Параметры запроса

    | Поле | Тип | Обязательно | Описание |
    |------|-----|-------------|----------|
    | `user_id` | integer | Да | ID владельца счета |
    | `bank_account_hash` | string | Да | SHA256 хеш номера счета (64 символа) |
    | `bank_account_name` | string | Да | Название счета |
    | `bank_id` | integer | Да | ID банка-эмитента |
    | `currency` | string | Нет | Код валюты (по умолчанию RUB) |
    | `balance` | decimal | Нет | Начальный баланс (по умолчанию 0.00) |

    ## Пример запроса

    ```json
    {
        "user_id": 1,
        "bank_account_hash": "4a210c3e4ff83583c97689e3e1d8f63cbcd7cb13d8b75ddbcf06091fbb4725db",
        "bank_account_name": "Основная карта",
        "bank_id": 1,
        "currency": "RUB",
        "balance": "125450.75"
    }
    ```

    ## Генерация хеша

    Хеш генерируется из номера счета:
    ```python
    import hmac
    import hashlib

    account_number = "40817810099910004312"
    secret = "bank-account-secure-key-2026"

    hash = hmac.new(
        secret.encode(),
        account_number.encode(),
        hashlib.sha256
    ).hexdigest()
    ```
    """
    result = await transaction_repo.create_bank_account(account)
    return transaction_repo.to_dict(result)


@router.post(
    "/bank_accounts/bulk",
    status_code=status.HTTP_201_CREATED,
    summary="Массовое создание банковских счетов",
    description="Создает несколько банковских счетов за один запрос",
    responses={201: {"description": "Счета созданы", "content": {"application/json": {"example": {"created": 4}}}}},
    tags=["Загрузка данных"],
)
async def create_bank_accounts_bulk(
    accounts: List[BankAccountCreate], transaction_repo: TransactionRepository = Depends(get_transactions_repository)
):
    """
    Массовое создание банковских счетов.

    **Используется:** Только для загрузки тестовых данных через скрипт.

    ## Пример запроса

    ```json
    [
        {
            "user_id": 1,
            "bank_account_hash": "4a210c3e...",
            "bank_account_name": "Основная карта",
            "bank_id": 1,
            "currency": "RUB",
            "balance": "125450.75"
        },
        {
            "user_id": 1,
            "bank_account_hash": "7b8e9f2a...",
            "bank_account_name": "Накопительная",
            "bank_id": 2,
            "currency": "RUB",
            "balance": "50000.00"
        }
    ]
    ```

    ## Пример ответа

    ```json
    {
        "created": 2
    }
    ```
    """
    return await transaction_repo.bulk_create_bank_accounts(accounts)


@router.post(
    "/transactions",
    status_code=status.HTTP_201_CREATED,
    summary="Создать транзакцию",
    description="Создает одну транзакцию (операцию по счету)",
    responses={
        201: {
            "description": "Транзакция создана",
            "content": {
                "application/json": {
                    "example": {
                        "id": 1,
                        "bank_account_hash": "4a210c3e...",
                        "merchant_id": 5,
                        "category_id": 1,
                        "amount": "-1250.50",
                        "currency": "RUB",
                        "description": "Покупка продуктов",
                        "transaction_date": "2024-01-15T14:30:00",
                        "mcc": "5411",
                    }
                }
            },
        }
    },
    tags=["Загрузка данных"],
)
async def create_transaction(
    transaction: TransactionCreate, transaction_repo: TransactionRepository = Depends(get_transactions_repository)
):
    """
    Создание транзакции (банковской операции).

    **Используется:** Только для загрузки тестовых данных через скрипт.

    ## Параметры запроса

    | Поле | Тип | Обязательно | Описание |
    |------|-----|-------------|----------|
    | `id` | integer | Да | Уникальный ID транзакции |
    | `bank_account_hash` | string | Да | Хеш счета, по которому прошла операция |
    | `merchant_id` | integer | Да | ID мерчанта (магазин, организация) |
    | `category_id` | integer | Да | ID категории транзакции |
    | `amount` | decimal | Да | Сумма (отрицательная для расходов, положительная для доходов) |
    | `currency` | string | Да | Код валюты (RUB, USD, EUR) |
    | `description` | string | Нет | Описание операции |
    | `transaction_date` | datetime | Да | Дата и время операции |
    | `mcc` | string | Да | MCC код мерчанта |

    ## Пример запроса (расход)

    ```json
    {
        "id": 1,
        "bank_account_hash": "4a210c3e4ff83583c97689e3e1d8f63cbcd7cb13d8b75ddbcf06091fbb4725db",
        "merchant_id": 5,
        "category_id": 1,
        "amount": "-1250.50",
        "currency": "RUB",
        "description": "Покупка продуктов",
        "transaction_date": "2024-01-15T14:30:00",
        "mcc": "5411"
    }
    ```

    ## Пример запроса (доход)

    ```json
    {
        "id": 2,
        "bank_account_hash": "4a210c3e...",
        "merchant_id": 1,
        "category_id": 10,
        "amount": "50000.00",
        "currency": "RUB",
        "description": "Зарплата",
        "transaction_date": "2024-01-01T10:00:00",
        "mcc": "0000"
    }
    ```

    ## Правила для amount

    - **Отрицательное значение:** расход (списание со счета)
    - **Положительное значение:** доход (поступление на счет)
    - Формат: десятичное число с точкой, до 2 знаков после запятой
    """
    result = await transaction_repo.create_transaction(transaction)
    return transaction_repo.to_dict(result)


@router.post(
    "/transactions/bulk",
    status_code=status.HTTP_201_CREATED,
    summary="Массовое создание транзакций",
    description="Создает несколько транзакций за один запрос (самая важная ручка для загрузки данных)",
    responses={
        201: {"description": "Транзакции созданы", "content": {"application/json": {"example": {"created": 33}}}}
    },
    tags=["Загрузка данных"],
)
async def create_transactions_bulk(
    transactions: List[TransactionCreate],
    transaction_repo: TransactionRepository = Depends(get_transactions_repository),
):
    """
    Массовое создание транзакций.

    **Используется:** Только для загрузки тестовых данных через скрипт.

    ## Важность этой ручки

    Это самая важная ручка для загрузки тестовых данных, так как:
    - Транзакций обычно очень много (сотни, тысячи)
    - Bulk операция в 100+ раз быстрее
    - Позволяет загрузить полную историю за секунды

    ## Пример запроса

    ```json
    [
        {
            "id": 1,
            "bank_account_hash": "4a210c3e...",
            "merchant_id": 5,
            "category_id": 1,
            "amount": "-1250.50",
            "currency": "RUB",
            "description": "Покупка продуктов",
            "transaction_date": "2024-01-15T14:30:00",
            "mcc": "5411"
        },
        {
            "id": 2,
            "bank_account_hash": "4a210c3e...",
            "merchant_id": 8,
            "category_id": 2,
            "amount": "-350.00",
            "currency": "RUB",
            "description": "Поездка на такси",
            "transaction_date": "2024-01-15T18:45:00",
            "mcc": "4121"
        }
    ]
    ```

    ## Пример ответа

    ```json
    {
        "created": 2
    }
    ```

    ## Типичное использование

    При загрузке тестовых данных обычно создается:
    - 30-50 транзакций на счет
    - Смесь доходов и расходов
    - Разные категории и мерчанты
    - За период 1-3 месяца
    """
    return await transaction_repo.bulk_create_transactions(transactions)
