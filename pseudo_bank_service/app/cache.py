"""
Инициализация кэширования для pseudo_bank_service.
"""

import os

from shared.cache import CacheClient

cache_client = CacheClient(redis_url=os.getenv(
    "REDIS_URL", "redis://redis:6379"))

# TTL (в секундах)
BANK_ACCOUNT_TTL = 900  # 15 минут
DICTIONARIES_TTL = 10800  # 3 часа

# Ключи кэша
BANK_ACCOUNT_PREFIX = "bank:account:"
CATEGORIES_KEY = "pseudo_bank:categories"
MERCHANTS_KEY = "pseudo_bank:merchants"
MCC_CATEGORIES_KEY = "pseudo_bank:mcc_categories"
BANKS_KEY = "pseudo_bank:banks"
