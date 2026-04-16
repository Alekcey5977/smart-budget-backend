"""
Инициализация кэширования для transactions-service.
"""
import os

from shared.cache import CacheClient

# Инициализация клиента Redis
REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379")
cache_client = CacheClient(redis_url=REDIS_URL)


# TTL (в секундах)
CATEGORIES_TTL = 43200  # 12 часов

# Ключи кэша для категорий
CATEGORIES_ALL_KEY = "categories:all"
CATEGORIES_INCOME_KEY = "categories:income"
CATEGORIES_EXPENSE_KEY = "categories:expense"
CATEGORIES_BY_ID_PREFIX = "categories:id:"


def category_by_id_key(category_id: int) -> str:
    """Ключ для конкретной категории по ID."""
    return f"{CATEGORIES_BY_ID_PREFIX}{category_id}"


def categories_pattern() -> str:
    """Шаблон для инвалидации всех ключей категорий."""
    return f"{CATEGORIES_BY_ID_PREFIX}*"
