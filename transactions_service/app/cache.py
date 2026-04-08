"""
Инициализация кэширования для transactions-service.
"""

import os

from shared.cache import CacheClient

cache_client = CacheClient(redis_url=os.getenv("REDIS_URL", "redis://redis:6379"))

# TTL (в секундах)
CATEGORIES_TTL = 3600  # 1 час для категорий
TRANSACTION_TTL = 300  # 5 минут для отдельных транзакций
TRANSACTIONS_LIST_TTL = 120  # 2 минуты для списка транзакций

# Ключи кэша для категорий
CATEGORIES_ALL_KEY = "categories:all"
CATEGORIES_INCOME_KEY = "categories:income"
CATEGORIES_EXPENSE_KEY = "categories:expense"
CATEGORIES_BY_ID_PREFIX = "categories:id:"

# Ключи кэша для транзакций
TRANSACTION_BY_ID_PREFIX = "transaction:id:"
TRANSACTIONS_LIST_PREFIX = "transactions:list:"


def category_by_id_key(category_id: int) -> str:
    """Ключ для конкретной категории по ID."""
    return f"{CATEGORIES_BY_ID_PREFIX}{category_id}"


def categories_pattern() -> str:
    """Шаблон для инвалидации всех ключей категорий."""
    return f"{CATEGORIES_BY_ID_PREFIX}*"


def transaction_by_id_key(transaction_id: str) -> str:
    """Ключ для конкретной транзакции по ID."""
    return f"{TRANSACTION_BY_ID_PREFIX}{transaction_id}"


def transactions_list_key(user_id: int, filters: dict) -> str:
    """Составной ключ для списка транзакций с учётом фильтров."""
    # Сериализуем фильтры в строку для уникальности ключа
    filter_parts = []
    for key in sorted(filters.keys()):
        value = filters[key]
        if value is not None:
            if isinstance(value, list):
                filter_parts.append(f"{key}={','.join(str(v) for v in value)}")
            else:
                filter_parts.append(f"{key}={value}")

    filter_str = "&".join(filter_parts) if filter_parts else "all"
    return f"{TRANSACTIONS_LIST_PREFIX}user{user_id}:{filter_str}"


def transaction_pattern(user_id: int = None) -> str:
    """Шаблон для инвалидации ключей транзакций."""
    if user_id is not None:
        return f"{TRANSACTION_BY_ID_PREFIX}*user{user_id}*"
    return f"{TRANSACTION_BY_ID_PREFIX}*"
