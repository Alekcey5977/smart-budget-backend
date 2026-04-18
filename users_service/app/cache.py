"""
Инициализация кэширования для users-service.
"""

import os

from shared.cache import CacheClient

# Инициализация клиента Redis
REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379")
cache_client = CacheClient(redis_url=REDIS_URL)


# TTL (в секундах)
USER_PROFILE_TTL = 300  # 5 минут для профиля пользователя
BANK_ACCOUNTS_TTL = 300  # 5 минут для списка банковских счетов

# Ключи кэша
USER_PROFILE_PREFIX = "user:profile:"
BANK_ACCOUNTS_PREFIX = "user:bank_accounts:"


def user_profile_key(user_id: int) -> str:
    """Ключ для профиля пользователя по ID."""
    return f"{USER_PROFILE_PREFIX}{user_id}"


def bank_accounts_key(user_id: int) -> str:
    """Ключ для списка банковских счетов пользователя."""
    return f"{BANK_ACCOUNTS_PREFIX}{user_id}"
