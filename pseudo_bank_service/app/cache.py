"""
Инициализация кэширования для pseudo_bank_service.
"""

import os

from shared.cache import CacheClient

cache_client = CacheClient(redis_url=os.getenv("REDIS_URL", "redis://redis:6379"))

# TTL (в секундах)
BANK_ACCOUNT_TTL = 300  # 5 минут для данных банковского счёта
DICTIONARIES_TTL = 3600  # 1 час для категорий, мерчантов, MCC, банков

# Ключи кэша
BANK_ACCOUNT_PREFIX = "bank:account:"
CATEGORIES_KEY = "pseudo_bank:categories"
MERCHANTS_KEY = "pseudo_bank:merchants"
MCC_CATEGORIES_KEY = "pseudo_bank:mcc_categories"
BANKS_KEY = "pseudo_bank:banks"
