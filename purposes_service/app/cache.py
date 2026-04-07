"""
Инициализация кэширования для purposes-service.
"""

import os

from shared.cache import CacheClient

cache_client = CacheClient(redis_url=os.getenv("REDIS_URL", "redis://redis:6379"))

# TTL (в секундах)
PURPOSES_LIST_TTL = 300  # 5 минут для списка целей пользователя

# Ключи кэша
PURPOSES_BY_USER_PREFIX = "purposes:user:"


def purposes_by_user_key(user_id: int) -> str:
    """Ключ для списка целей пользователя по ID."""
    return f"{PURPOSES_BY_USER_PREFIX}{user_id}"
